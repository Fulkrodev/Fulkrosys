"""Client-side service for M16 Adaptive Onboarding.

Handles: consume magic link, question navigation with branching,
answer persistence, validation, submit. Separated from admin
service (service.py) for clarity.
"""
from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.onboarding import OnboardingResponse, OnboardingSession
from backend.app.motors.m12_magic_link.schemas import MagicLinkConsumeRequest
from backend.app.motors.m12_magic_link.service import MagicLinkService

from .catalog_loader import get_template_by_id
from .enums import QuestionType, SessionState
from .types import BranchingCondition, OnboardingTemplate, Question


class OnboardingClientError(ValueError):
    pass


class OnboardingAuthError(ValueError):
    pass


class OnboardingGoneError(ValueError):
    pass


# ==== AUTH ====

def _generate_session_secret() -> str:
    return secrets.token_urlsafe(32)


def _hash_secret(secret: str) -> str:
    return bcrypt.hashpw(secret.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def _verify_secret(secret_plain: str, secret_hash: str) -> bool:
    try:
        return bcrypt.checkpw(secret_plain.encode("utf-8"), secret_hash.encode("ascii"))
    except Exception:
        return False


async def consume_magic_link_and_start(
    db: AsyncSession,
    token: str,
    otp: Optional[str],
) -> dict:
    """First client call: validate magic link via M12, issue session_secret."""
    ml_service = MagicLinkService(db)

    try:
        consume_req = MagicLinkConsumeRequest(token=token, otp=otp)
        consume_result = await ml_service.consume_magic_link(consume_req)
    except Exception as exc:
        raise OnboardingAuthError(f"Credenciales invalidas: {exc}")

    scope = consume_result.scope or {}
    session_id_str = scope.get("session_id")
    if not session_id_str:
        raise OnboardingClientError("Magic link no tiene session_id en scope")

    session_id = uuid.UUID(session_id_str)
    r = await db.execute(
        select(OnboardingSession).where(OnboardingSession.id == session_id)
    )
    onb = r.scalar_one_or_none()
    if onb is None:
        raise OnboardingClientError("Session asociada al magic link no existe")

    if onb.estado in (SessionState.EXPIRED.value, SessionState.CANCELLED.value):
        raise OnboardingGoneError(f"Session no disponible ({onb.estado})")

    # Generate + persist session_secret
    secret_plain = _generate_session_secret()
    onb.client_auth_secret_hash = _hash_secret(secret_plain)
    onb.client_auth_issued_at = datetime.now(timezone.utc)
    await db.flush()

    template = get_template_by_id(onb.template_id_str)
    if template is None:
        raise OnboardingClientError(f"Plantilla {onb.template_id_str} no existe")

    sections = list(dict.fromkeys(q.section for q in template.questions))
    total = onb.total_questions or 0
    answered = onb.answered_questions or 0
    progress = round(100.0 * answered / total, 1) if total > 0 else 0.0

    return {
        "session_id": onb.id,
        "session_secret": secret_plain,
        "template_id": template.id,
        "template_nombre": template.nombre,
        "tiempo_estimado_minutos": template.tiempo_estimado_minutos,
        "total_questions": total,
        "answered_questions": answered,
        "progress_percentage": progress,
        "sections": sections,
        "state": SessionState(onb.estado),
    }


async def authenticate_client_session(
    db: AsyncSession,
    session_id: uuid.UUID,
    session_secret: str,
) -> OnboardingSession:
    """Validate session_secret. Used by require_onboarding_auth dependency."""
    r = await db.execute(
        select(OnboardingSession).where(OnboardingSession.id == session_id)
    )
    onb = r.scalar_one_or_none()
    if onb is None:
        raise OnboardingAuthError("Session no existe")
    if onb.client_auth_secret_hash is None:
        raise OnboardingAuthError("Session no tiene auth (usa /consume primero)")
    if not _verify_secret(session_secret, onb.client_auth_secret_hash):
        raise OnboardingAuthError("Secret invalido")
    if onb.estado in (SessionState.EXPIRED.value, SessionState.CANCELLED.value):
        raise OnboardingGoneError(f"Session no disponible ({onb.estado})")
    return onb


# ==== BRANCHING ENGINE ====

def _eval_condition(condition: BranchingCondition, answers: dict[str, Any]) -> bool:
    """Evaluate skip_if. Returns True if condition is met (question should be skipped)."""
    if condition.question_id not in answers:
        return False
    ref = answers[condition.question_id]
    target = condition.value
    op = condition.operator

    if op == "equals":
        return ref == target
    if op == "not_equals":
        return ref != target
    if op == "in":
        return isinstance(target, list) and ref in target
    if op == "contains":
        if isinstance(ref, str) and isinstance(target, str):
            return target in ref
        if isinstance(ref, list):
            return target in ref
        return False
    return False


async def _load_answers_map(db: AsyncSession, session_id: uuid.UUID) -> dict[str, Any]:
    """Load all current answers as dict question_id -> answer_value."""
    r = await db.execute(
        select(OnboardingResponse).where(OnboardingResponse.session_id == session_id)
    )
    answers = {}
    for row in r.scalars().all():
        v = row.answer_value
        if isinstance(v, dict) and "value" in v:
            answers[row.question_id] = v["value"]
        else:
            answers[row.question_id] = v
    return answers


def _effective_question_sequence(
    template: OnboardingTemplate,
    answers: dict[str, Any],
) -> list[Question]:
    """Return effective question sequence after applying skip_if."""
    sequence = []
    for q in template.questions:
        if q.skip_if is not None and _eval_condition(q.skip_if, answers):
            continue
        sequence.append(q)
    return sequence


# ==== NAVIGATION ====

async def get_next_question(db: AsyncSession, onb: OnboardingSession) -> dict:
    """Return next unanswered question according to branching."""
    template = get_template_by_id(onb.template_id_str)
    if template is None:
        raise OnboardingClientError(f"Plantilla {onb.template_id_str} no existe")

    answers = await _load_answers_map(db, onb.id)
    effective = _effective_question_sequence(template, answers)

    next_q = None
    for q in effective:
        if q.id not in answers:
            next_q = q
            break

    total_eff = len(effective)
    answered_count = sum(1 for q in effective if q.id in answers)
    progress = round(100.0 * answered_count / total_eff, 1) if total_eff > 0 else 0.0
    remaining_req = sum(1 for q in effective if q.id not in answers and q.validation.required)

    return {
        "done": next_q is None,
        "question": next_q,
        "progress_percentage": progress,
        "current_section": next_q.section if next_q else None,
        "remaining_required": remaining_req,
    }


# ==== VALIDATION ====

def _validate_answer(question: Question, answer: Any) -> None:
    """Validate an answer against question type and validation rules."""
    qv = question.validation
    qt = question.type

    if qv.required and (answer is None or (isinstance(answer, str) and not answer.strip())):
        raise OnboardingClientError(f"Respuesta requerida para {question.id}")

    if answer is None:
        return

    if qt == QuestionType.BOOLEAN:
        if not isinstance(answer, bool):
            raise OnboardingClientError(f"{question.id}: debe ser boolean")

    elif qt == QuestionType.NUMBER:
        if not isinstance(answer, (int, float)) or isinstance(answer, bool):
            raise OnboardingClientError(f"{question.id}: debe ser numero")
        if qv.min_value is not None and answer < qv.min_value:
            raise OnboardingClientError(f"{question.id}: minimo {qv.min_value}")
        if qv.max_value is not None and answer > qv.max_value:
            raise OnboardingClientError(f"{question.id}: maximo {qv.max_value}")

    elif qt in (QuestionType.TEXT, QuestionType.LONG_TEXT):
        if not isinstance(answer, str):
            raise OnboardingClientError(f"{question.id}: debe ser texto")
        if qv.min_length is not None and len(answer) < qv.min_length:
            raise OnboardingClientError(f"{question.id}: minimo {qv.min_length} caracteres")
        if qv.max_length is not None and len(answer) > qv.max_length:
            raise OnboardingClientError(f"{question.id}: maximo {qv.max_length} caracteres")

    elif qt == QuestionType.EMAIL:
        if not isinstance(answer, str) or "@" not in answer or "." not in answer.split("@")[-1]:
            raise OnboardingClientError(f"{question.id}: email invalido")

    elif qt == QuestionType.URL:
        if not isinstance(answer, str) or not (answer.startswith("http://") or answer.startswith("https://")):
            raise OnboardingClientError(f"{question.id}: URL debe empezar con http(s)://")

    elif qt == QuestionType.DATE:
        if not isinstance(answer, str):
            raise OnboardingClientError(f"{question.id}: fecha debe ser string ISO")
        try:
            datetime.fromisoformat(answer.replace("Z", "+00:00"))
        except ValueError:
            raise OnboardingClientError(f"{question.id}: fecha no es ISO valida")

    elif qt == QuestionType.SINGLE_SELECT:
        if not isinstance(answer, str):
            raise OnboardingClientError(f"{question.id}: single_select requiere string")
        if question.options:
            valid = {o.value for o in question.options}
            if answer not in valid:
                raise OnboardingClientError(f'{question.id}: valor "{answer}" no esta entre las opciones')

    elif qt == QuestionType.MULTI_SELECT:
        if not isinstance(answer, list) or not all(isinstance(v, str) for v in answer):
            raise OnboardingClientError(f"{question.id}: multi_select requiere lista de strings")
        if question.options:
            valid = {o.value for o in question.options}
            invalid = [v for v in answer if v not in valid]
            if invalid:
                raise OnboardingClientError(f"{question.id}: valores invalidos: {invalid}")


# ==== SAVE ANSWER ====

async def save_answer(
    db: AsyncSession,
    onb: OnboardingSession,
    question_id: str,
    answer_value: Any,
) -> dict:
    """Save an answer (upsert). Handle automatic state transitions."""
    template = get_template_by_id(onb.template_id_str)
    if template is None:
        raise OnboardingClientError(f"Plantilla {onb.template_id_str} no existe")

    question = next((q for q in template.questions if q.id == question_id), None)
    if question is None:
        raise OnboardingClientError(f"Pregunta {question_id} no existe en plantilla")

    _validate_answer(question, answer_value)

    # Upsert
    r = await db.execute(
        select(OnboardingResponse).where(
            OnboardingResponse.session_id == onb.id,
            OnboardingResponse.question_id == question_id,
        )
    )
    existing = r.scalar_one_or_none()

    if existing:
        existing.answer_value = {"value": answer_value}
        existing.section = question.section
        existing.updated_at = datetime.now(timezone.utc)
    else:
        db.add(OnboardingResponse(
            session_id=onb.id,
            question_id=question_id,
            section=question.section,
            answer_value={"value": answer_value},
        ))
        onb.answered_questions = (onb.answered_questions or 0) + 1

    # SENT -> IN_PROGRESS on first answer
    if onb.estado in (SessionState.CREATED.value, SessionState.SENT.value):
        onb.estado = SessionState.IN_PROGRESS.value
        if onb.iniciado_at is None:
            onb.iniciado_at = datetime.now(timezone.utc)

    await db.flush()

    total = onb.total_questions or 0
    answered = onb.answered_questions or 0
    progress = round(100.0 * answered / total, 1) if total > 0 else 0.0

    return {
        "question_id": question_id,
        "saved": True,
        "progress_percentage": progress,
        "state": SessionState(onb.estado),
    }


# ==== SUBMIT ====

async def submit_onboarding(
    db: AsyncSession,
    onb: OnboardingSession,
    allow_partial: bool,
    updated_by: uuid.UUID | None = None,
) -> dict:
    """Finalize the session. Validates completeness unless allow_partial."""
    if onb.estado == SessionState.COMPLETED.value:
        return {
            "session_id": onb.id,
            "state": SessionState.COMPLETED,
            "completed_at": onb.completado_at,
            "missing_required": [],
        }

    template = get_template_by_id(onb.template_id_str)
    if template is None:
        raise OnboardingClientError(f"Plantilla {onb.template_id_str} no existe")

    answers = await _load_answers_map(db, onb.id)
    effective = _effective_question_sequence(template, answers)

    missing = [q.id for q in effective if q.validation.required and q.id not in answers]

    if missing and not allow_partial:
        raise OnboardingClientError(
            f"Faltan {len(missing)} respuestas obligatorias. "
            "Usa allow_partial=true para forzar cierre."
        )

    now = datetime.now(timezone.utc)
    onb.estado = SessionState.COMPLETED.value
    onb.completado_at = now
    await db.flush()

    # Ejecutable 8 OLA 0 (FR-1): aplicar las dimensiones canónicas del proyecto
    # desde las respuestas del onboarding. Era dead-code (0 callers): sin esto las
    # 10 dims (madurez_ens_actual, aplica_nis2, aplica_dora, dpo_designado…)
    # quedan NULL y las tareas/medidas enriquecidas por perfil nunca disparan
    # → el cliente llega a auditoría sin evidencias del perfil (rompe Premisa#1).
    # Non-invasive (OPS-040: no levanta excepción). Actor de auditoría: el
    # ClientUser real si el caller lo pasa, si no la propia sesión (UUID válido,
    # Project.updated_by no tiene FK).
    from backend.app.motors.m16_onboarding.dimensions_capture import (
        apply_dimensions_from_responses,
    )
    await apply_dimensions_from_responses(
        db, onb.project_id, answers, updated_by or onb.id,
    )

    return {
        "session_id": onb.id,
        "state": SessionState.COMPLETED,
        "completed_at": now,
        "missing_required": missing if allow_partial else [],
    }
