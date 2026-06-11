"""Portal Cliente copiloto endpoints · MB-7 atom 7.2 plan v6.

Reuses agent_14_copiloto.service pipeline (NO new RAG pipeline).
Auth: get_current_client_user instead of require_owner.

Q5.2 cement: all client users access the same copiloto (NO role).
"""
from __future__ import annotations

import json as _json
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agents.agent_14_copiloto.service import (
    answer_question,
    stream_answer_question,
)
from backend.app.agents.agent_14_copiloto.types import (
    CopilotQuery,
    PageContext,
)
from backend.app.agents.copilot_memory import (
    load_conversation_history,
    persist_exchange,
)
from backend.app.agents.copilot_project_state import build_project_state_block
from backend.app.agents.copilot_rate_limit import (
    CopilotRateLimitExceeded,
    enforce_rate_limit_or_raise,
)
from backend.app.database import get_db, set_tenant_context
from backend.app.models.client_portal import ClientUser
from backend.app.motors.m21_portal_cliente.api import get_current_client_user


router = APIRouter(
    prefix="/client-portal/copiloto",
    tags=["Portal Cliente - Copiloto"],
)


async def _enforce_cliente_rate_limit(
    db: AsyncSession, user: ClientUser,
) -> Optional[str]:
    """F-13-01 · cap copiloto cliente antes de cualquier llamada LLM.

    El router ``portal_api`` (consumido por ``frontend/lib/api/copiloto.ts``)
    carecía de rate-limit, dejando los caps token/coste/mes evadibles por esta
    vía. Espeja ``client_copilot_stub.py``: hard-block → 429 R29 friendly;
    soft-warn → devuelve ``warning_message`` para adjuntar a la respuesta.
    Caps derivados on-query de ``LLMInteractionLog`` (ADR-025, sin tablas
    nuevas) en ``agents/copilot_rate_limit.py``.
    """
    # FIX P1-1: el cap del cliente DEBE ser POR PROYECTO. Sin pasar project_id,
    # get_rate_limit_status agregaba el uso LLM de TODOS los clientes → quota
    # poisoning cross-tenant + fuga de coste. Resolvemos el proyecto del cliente
    # server-side (RLS-gated · _resolve_project_meta_scoped fija además el
    # contexto que reusa el call-site inmediatamente después · idempotente).
    project_id_str, _ = await _resolve_project_meta_scoped(db, user.client_id)
    project_id = uuid.UUID(project_id_str) if project_id_str else None
    if project_id is None:
        # R09 fail-closed: ``get_rate_limit_status`` exige project_id para el tier
        # cliente. Sin proyecto activo no hay agregado por-tenant que aplicar → se
        # omite el cap (evita 500 · no degrada cross-tenant: no hay nada que sumar).
        return None
    try:
        status = await enforce_rate_limit_or_raise(
            db=db, user_id=user.id, tier="cliente", project_id=project_id,
        )
    except CopilotRateLimitExceeded as exc:
        raise HTTPException(
            status_code=429,
            detail=exc.status.blocked_reason or "Has alcanzado el límite de uso",
        )
    return status.warning_message


class PortalPageContext(BaseModel):
    url: Optional[str] = None
    project_phase: Optional[str] = None
    active_motor: Optional[str] = None


class PortalCopilotChatBody(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)
    page_context: Optional[PortalPageContext] = None


class PortalCopilotChatResponse(BaseModel):
    answer: str
    citations_found: list[str]
    not_in_corpus: bool
    low_grounding_confidence: bool
    model_used: str
    latency_ms: int
    rate_limit_warning: Optional[str] = None


async def _resolve_project_meta(
    db: AsyncSession, client_id: uuid.UUID,
) -> tuple[Optional[str], Optional[str]]:
    """Find active project + categoria_objetivo for cliente.

    Returns (project_id, ens_category) · (None, None) si missing.

    Phase 2E · ens_category resuelto para inject PageContext y permitir
    al copiloto tailorear respuestas per categoría (BÁSICA/MEDIA/ALTA).
    """
    row = (await db.execute(
        text(
            "SELECT id, categoria_objetivo FROM projects "
            "WHERE client_id = :cid AND deleted_at IS NULL "
            "ORDER BY created_at DESC LIMIT 1"
        ),
        {"cid": str(client_id)},
    )).first()
    if row is None:
        return None, None
    return str(row[0]), (row[1] if row[1] else None)


# Backward-compat wrapper (other call sites)
async def _resolve_project_id(
    db: AsyncSession, client_id: uuid.UUID,
) -> Optional[str]:
    project_id, _ = await _resolve_project_meta(db, client_id)
    return project_id


async def _resolve_project_meta_scoped(
    db: AsyncSession, client_id: uuid.UUID,
) -> tuple[Optional[str], Optional[str]]:
    """F-18-01 · ÚNICA puerta correcta de resolución project-scoped cliente.

    El runtime conecta como ``fulkro_app`` (RLS activa, ``rolbypassrls=false``)
    y NO hay middleware que setee ``app.current_client_id``
    (``authenticate_request`` solo pone ``app.current_user``). Sin ese GUC, la
    política ``client_isolation`` de ``projects`` ciega la fila del cliente →
    ``_resolve_project_meta`` devolvería ``None`` (fail-closed, NO fuga) y el
    copiloto respondería 404 / contexto vacío a su dueño legítimo (F-18-01).

    Esta puerta hace, en orden:
      1. setea ``app.current_client_id`` **ANTES** de la query de resolución
         (la RLS de ``projects`` es por ``client_id``; sin esto la query es
         ciega — NO basta con espejar el orden de ``m17`` que resuelve antes de
         setear),
      2. resuelve el proyecto del cliente (server-side, RLS-gated),
      3. setea ``app.current_project_id`` para las lecturas project-scoped
         posteriores (``compute_workflow_state``, pipeline RAG, etc).

    ``set_tenant_context`` usa SIEMPRE ``is_local=true`` (auto-reset al fin de
    transacción). ``is_local=false`` está PROHIBIDO: filtraría el GUC a la
    siguiente petición de OTRO cliente que reúse la conexión del pool = fuga
    cross-tenant. CUIDADO: un ``db.commit()`` intermedio tira el GUC
    ``is_local`` → re-setear contexto tras cada commit (ver ``/chat/stream``).

    El ``project_id`` se resuelve aquí server-side desde ``client_id`` (NUNCA
    se confía un ``project_id`` de input cliente para setear ``app.current_project_id``).
    """
    # 1 · contexto client_id ANTES de resolver · la RLS de `projects` es por
    #     client_id; sin este GUC la query de resolución es ciega (→ None).
    #     NO basta espejar m17 (resuelve antes de setear · orden mal · F-18-01b).
    await set_tenant_context(db, client_id=client_id)
    # 2 · resolución server-side RLS-gated (ahora ve la fila del cliente).
    project_id, ens_category = await _resolve_project_meta(db, client_id)
    # 3 · project_id para las lecturas project-scoped posteriores (resuelto
    #     server-side desde client_id · NUNCA project_id de input cliente).
    if project_id:
        await set_tenant_context(db, project_id=uuid.UUID(project_id))
    return project_id, ens_category


def _to_page_context(
    schema: Optional[PortalPageContext],
    ens_category: Optional[str] = None,
) -> Optional[PageContext]:
    """Convert API page_context to internal PageContext.

    Phase 2E · ens_category resolved server-side desde project.categoria_objetivo
    inyectado aquí · permits LLM tailoring per categoría sin trust del cliente.
    """
    if schema is None and ens_category is None:
        return None
    return PageContext(
        url=schema.url if schema else None,
        client_id=None,  # set after project resolution to keep RLS clean
        project_phase=schema.project_phase if schema else None,
        active_motor=schema.active_motor if schema else None,
        ens_category=ens_category,
        # current_screen = pathname (para el screen_references_catalog cliente).
        current_screen=schema.url if schema else None,
    )


async def _cliente_project_state(
    db: AsyncSession, project_id: Optional[str],
) -> Optional[str]:
    """Bloque "Estado actual del proyecto" role=cliente (R29 · sin jerga ENS).

    Best-effort · requiere contexto RLS ya fijado por el caller
    (_resolve_project_meta_scoped). Devuelve None si falla o no hay proyecto.
    """
    if not project_id:
        return None
    try:
        return (await build_project_state_block(db, project_id, "cliente")) or None
    except Exception:  # noqa: BLE001 · best-effort
        logger.exception("cliente project_state failed · pid={}", project_id)
        return None


async def _emit_copilot_audit_log(
    db: AsyncSession,
    *,
    project_id: str,
    client_id: uuid.UUID,
    accion: str,
    payload: dict,
) -> None:
    """Sub-atom 5.A · audit_log Sub-atom 5.A 3-way OR (project_id + client_id).

    Best-effort try/except · primary Q&A NUNCA bloqueado por audit_log fail.
    """
    try:
        await db.execute(
            text(
                "INSERT INTO audit_log "
                "(id, tabla, registro_id, accion, usuario, "
                "project_id, client_id, payload_new, timestamp) "
                "VALUES (gen_random_uuid(), 'copilot_interaction', "
                ":rid, :accion, :usuario, :pid, :cid, :payload, now())"
            ),
            {
                "rid": str(uuid.uuid4()),
                "accion": accion,
                "usuario": "cliente_copilot",
                "pid": project_id,
                "cid": str(client_id),
                "payload": _json.dumps(payload),
            },
        )
        await db.flush()
    except Exception:  # pragma: no cover · best-effort
        logger.exception(
            "audit_log {} emit failed · project_id={}",
            accion, project_id,
        )


@router.post("/chat", response_model=PortalCopilotChatResponse)
async def portal_copiloto_chat(
    body: PortalCopilotChatBody,
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> PortalCopilotChatResponse:
    """Single-shot Q&A (no SSE).

    Phase 2E · resolve project.categoria_objetivo + inject PageContext
    ens_category · LLM tailorea respuesta per categoría (BÁSICA/MEDIA/ALTA).
    audit_log Sub-atom 5.A emit cliente.copilot.asked + cliente.copilot.answered.
    """
    rate_warning = await _enforce_cliente_rate_limit(db, user)  # F-13-01
    # F-18-01 · setea contexto RLS (client_id) antes de resolver + project_id
    # tras resolver · sin esto el copiloto es ciego a su propio proyecto en prod.
    project_id, ens_category = await _resolve_project_meta_scoped(db, user.client_id)
    if not project_id:
        raise HTTPException(
            status_code=404, detail="No active project for this client",
        )
    page_context = _to_page_context(body.page_context, ens_category) or (
        PageContext(ens_category=ens_category)
    )
    if page_context.current_screen is None:
        page_context.current_screen = page_context.url
    # 2026-06-09 · estado EN VIVO del proyecto (role=cliente · R29) · RLS ya
    # fijado por _resolve_project_meta_scoped arriba.
    page_context.project_state = await _cliente_project_state(db, project_id)
    # 2026-06-09 · memoria N6 (sesión separada · best-effort) · el chat RAG
    # cliente era stateless · ahora recuerda el hilo (aislado client_id+project_id).
    conv_id, history = await load_conversation_history(
        project_id=uuid.UUID(project_id),
        client_user_id=user.id,
        client_id=user.client_id,
    )
    query = CopilotQuery(
        question=body.question,
        project_id=project_id,
        page_context=page_context,
        role="cliente",
        history=history,
    )

    # Phase 2E · audit_log cliente.copilot.asked (Sub-atom 5.A pre-LLM)
    await _emit_copilot_audit_log(
        db,
        project_id=project_id,
        client_id=user.client_id,
        accion="cliente.copilot.asked",
        payload={
            "question_preview": body.question[:200],
            "ens_category": ens_category,
            "active_motor": (body.page_context.active_motor
                             if body.page_context else None),
        },
    )

    try:
        result = await answer_question(db, query)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Portal copilot chat error: {}", exc)
        raise HTTPException(status_code=500, detail="Error en copiloto")

    # Phase 2E · audit_log cliente.copilot.answered (Sub-atom 5.A post-LLM)
    await _emit_copilot_audit_log(
        db,
        project_id=project_id,
        client_id=user.client_id,
        accion="cliente.copilot.answered",
        payload={
            "model_used": result.model_used,
            "latency_ms": result.latency_ms,
            "citations_count": len(result.citations_found),
            "not_in_corpus": result.not_in_corpus,
            "low_grounding_confidence": result.low_grounding_confidence,
        },
    )

    await db.commit()
    # 2026-06-09 · persiste el turno en memoria N6 (sesión separada · best-effort).
    await persist_exchange(
        conversation_id=conv_id,
        project_id=uuid.UUID(project_id),
        user_text=body.question,
        assistant_text=result.answer,
        client_id=user.client_id,
    )
    return PortalCopilotChatResponse(
        answer=result.answer,
        citations_found=result.citations_found,
        not_in_corpus=result.not_in_corpus,
        low_grounding_confidence=result.low_grounding_confidence,
        model_used=result.model_used,
        latency_ms=result.latency_ms,
        rate_limit_warning=rate_warning,
    )


@router.post("/chat/stream")
async def portal_copiloto_chat_stream(
    body: PortalCopilotChatBody,
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
):
    """SSE streaming · reuses stream_answer_question from agent_14_copiloto.

    Phase 2E · category-aware via PageContext.ens_category resolved server-side.
    audit_log emit cliente.copilot.asked pre-stream (answer trace via generator
    NO bloqueante).
    """
    await _enforce_cliente_rate_limit(db, user)  # F-13-01 · hard-block pre-stream
    # F-18-01 · contexto RLS antes de resolver (ver _resolve_project_meta_scoped).
    project_id, ens_category = await _resolve_project_meta_scoped(db, user.client_id)
    if not project_id:
        raise HTTPException(
            status_code=404, detail="No active project for this client",
        )

    # 2026-06-09 · computa el estado del proyecto (role=cliente) ANTES del
    # commit: el db.commit() de abajo tira el GUC is_local → tras él las
    # lecturas project-scoped (compute_workflow_state) serían ciegas.
    _cliente_state_block = await _cliente_project_state(db, project_id)
    # 2026-06-09 · memoria N6 (sesión separada · best-effort) · carga ANTES del
    # commit (aunque usa su propia sesión · idempotente).
    _conv_id, _history = await load_conversation_history(
        project_id=uuid.UUID(project_id),
        client_user_id=user.id,
        client_id=user.client_id,
    )

    # Phase 2E · audit_log pre-stream
    await _emit_copilot_audit_log(
        db,
        project_id=project_id,
        client_id=user.client_id,
        accion="cliente.copilot.asked",
        payload={
            "question_preview": body.question[:200],
            "ens_category": ens_category,
            "mode": "stream",
            "active_motor": (body.page_context.active_motor
                             if body.page_context else None),
        },
    )
    await db.commit()

    _stream_pc = _to_page_context(body.page_context, ens_category) or (
        PageContext(ens_category=ens_category)
    )
    if _stream_pc.current_screen is None:
        _stream_pc.current_screen = _stream_pc.url
    _stream_pc.project_state = _cliente_state_block
    query = CopilotQuery(
        question=body.question,
        project_id=project_id,
        page_context=_stream_pc,
        role="cliente",
        history=_history,
    )

    async def _generator():
        _answer_acc: Optional[str] = None
        try:
            # F-18-01 · el db.commit() pre-stream (arriba) tiró el GUC is_local
            # → re-setear el contexto RLS AQUÍ o las lecturas project-scoped de
            # stream_answer_question serían ciegas (contexto vacío tras commit).
            # client_id + project_id ya resueltos server-side arriba (NUNCA un
            # project_id de input cliente). is_local=true se mantiene PROHIBIDO
            # cambiarlo (bleed cross-tenant en la conexión del pool).
            await set_tenant_context(
                db, client_id=user.client_id, project_id=uuid.UUID(project_id),
            )
            async for frame in stream_answer_question(db, query):
                yield frame
                # 2026-06-09 · captura la respuesta final del frame "done" para
                # persistir el turno en memoria N6 tras el stream.
                if '"done"' in frame:
                    try:
                        _payload = frame.split("data:", 1)[1].strip()
                        _data = _json.loads(_payload)
                        if _data.get("type") == "done":
                            _answer_acc = (_data.get("data") or {}).get("answer")
                    except Exception:  # noqa: BLE001 · best-effort parse
                        pass
            await db.commit()
            # memoria N6 (sesión separada · best-effort · post-stream).
            if _answer_acc:
                await persist_exchange(
                    conversation_id=_conv_id,
                    project_id=uuid.UUID(project_id),
                    user_text=body.question,
                    assistant_text=_answer_acc,
                    client_id=user.client_id,
                )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Portal copilot stream error: {}", exc)
            payload = _json.dumps(
                {"type": "error", "error": "Error en copiloto"},
                ensure_ascii=False,
            )
            yield f"data: {payload}\n\n"

    return StreamingResponse(
        _generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ════════════════════════════════════════════════════════════════════
# Sesión 3B-2B.8 CLUSTER 4 Phase 4A · LLM coach mode upgrade
# ════════════════════════════════════════════════════════════════════


class PortalCoachChatResponse(BaseModel):
    answer: str
    current_phase: Optional[str] = None
    top_pending_action: Optional[str] = None
    citations_found: list[str]
    not_in_corpus: bool
    low_grounding_confidence: bool
    model_used: str
    latency_ms: int
    rate_limit_warning: Optional[str] = None


class PortalCoachNextStepResponse(BaseModel):
    has_action: bool
    current_phase: Optional[str] = None
    message: str
    pending_action_motor: Optional[str] = None
    pending_action_template_id: Optional[str] = None


async def _resolve_coach_context(
    db: AsyncSession, project_id_str: str,
) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """Compute workflow state + top action for cliente · returns 4-tuple:

      (current_phase · pending_action_text · motor · template_id)

    Best-effort try/except: si scanner falla · returns (None, None, None, None)
    · primary copilot answer NUNCA bloqueado por coach scanner fail.
    """
    try:
        from uuid import UUID as _UUID

        from backend.app.motors.m11_copiloto.workflow_state_scanner import (
            compute_workflow_state,
            top_action_for_role,
        )

        state = await compute_workflow_state(db, _UUID(project_id_str))
        top = top_action_for_role(state, "cliente")
        if top is None:
            return state.current_phase, None, None, None
        return (
            state.current_phase,
            top.description_cliente,
            top.motor,
            top.target_url,
        )
    except Exception:  # pragma: no cover · best-effort
        logger.exception(
            "coach scanner failed · project_id={}", project_id_str,
        )
        return None, None, None, None


@router.post("/coach", response_model=PortalCoachChatResponse)
async def portal_copiloto_coach(
    body: PortalCopilotChatBody,
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> PortalCoachChatResponse:
    """Coach mode Q&A · LLM context-aware con workflow state + categoría.

    Phase 4A · extends portal_copiloto_chat con coach guidance injection:
      1. Resolve workflow state next_cliente_actions (Phase 1D scanner)
      2. Inject coach_mode=True + current_phase + pending_action en PageContext
      3. _build_system_prompt adds coach guidance section R29 firmísimo
      4. Reuse answer_question (agent_14 RAG pipeline) categoría-aware Phase 2E
      5. audit_log Sub-atom 5.A 3-way OR

    Filosofía cliente-mínimo:
    - Coach guides cliente "qué hacer y por qué" · NO autoría contenido ENS
    - "Sin prisa por tu parte" R29 firmísimo
    - Cliente recibe / aprueba / firma · NUNCA opera ENS técnico
    """
    rate_warning = await _enforce_cliente_rate_limit(db, user)  # F-13-01
    # F-18-01 · contexto RLS (client_id + project_id) para resolución + coach scan.
    project_id, ens_category = await _resolve_project_meta_scoped(db, user.client_id)
    if not project_id:
        raise HTTPException(
            status_code=404, detail="No active project for this client",
        )

    current_phase, pending_action, _motor, _tpl_id = await _resolve_coach_context(
        db, project_id,
    )

    # Build PageContext with coach injection
    page_context = _to_page_context(body.page_context, ens_category)
    if page_context is None:
        page_context = PageContext(ens_category=ens_category)
    page_context.coach_mode = True
    page_context.coach_current_phase = current_phase
    page_context.coach_pending_action = pending_action
    if page_context.current_screen is None:
        page_context.current_screen = page_context.url
    # 2026-06-09 · estado EN VIVO completo (role=cliente) además del coach hint.
    page_context.project_state = await _cliente_project_state(db, project_id)
    # 2026-06-09 · memoria N6 (sesión separada · best-effort).
    conv_id, history = await load_conversation_history(
        project_id=uuid.UUID(project_id),
        client_user_id=user.id,
        client_id=user.client_id,
    )

    query = CopilotQuery(
        question=body.question,
        project_id=project_id,
        page_context=page_context,
        role="cliente",
        history=history,
    )

    await _emit_copilot_audit_log(
        db,
        project_id=project_id,
        client_id=user.client_id,
        accion="cliente.coach.message.sent",
        payload={
            "question_preview": body.question[:200],
            "ens_category": ens_category,
            "current_phase": current_phase,
            "has_pending_action": pending_action is not None,
        },
    )

    try:
        result = await answer_question(db, query)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Portal coach chat error: {}", exc)
        raise HTTPException(status_code=500, detail="Error en copiloto coach")

    await _emit_copilot_audit_log(
        db,
        project_id=project_id,
        client_id=user.client_id,
        accion="cliente.coach.message.answered",
        payload={
            "model_used": result.model_used,
            "latency_ms": result.latency_ms,
            "citations_count": len(result.citations_found),
            "current_phase": current_phase,
        },
    )
    await db.commit()
    # 2026-06-09 · persiste el turno en memoria N6 (sesión separada · best-effort).
    await persist_exchange(
        conversation_id=conv_id,
        project_id=uuid.UUID(project_id),
        user_text=body.question,
        assistant_text=result.answer,
        client_id=user.client_id,
    )

    return PortalCoachChatResponse(
        answer=result.answer,
        current_phase=current_phase,
        top_pending_action=pending_action,
        citations_found=result.citations_found,
        not_in_corpus=result.not_in_corpus,
        low_grounding_confidence=result.low_grounding_confidence,
        model_used=result.model_used,
        latency_ms=result.latency_ms,
        rate_limit_warning=rate_warning,
    )


@router.get("/coach/next-step", response_model=PortalCoachNextStepResponse)
async def portal_coach_next_step(
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> PortalCoachNextStepResponse:
    """Coach next-step recommendation · single-shot · NO LLM (deterministic O(1)).

    Phase 4A · compute_workflow_state + top_action_for_role · R29 friendly
    compose. Returns has_action=False cuando NO pending actions ("Todo al día").
    """
    # F-18-01 · contexto RLS (client_id + project_id) antes de resolver/scan.
    project_id, _ens_category = await _resolve_project_meta_scoped(db, user.client_id)
    if not project_id:
        raise HTTPException(
            status_code=404, detail="No active project for this client",
        )

    current_phase, pending_action, motor, tpl_id = await _resolve_coach_context(
        db, project_id,
    )

    if pending_action is None:
        message = (
            "Todo al día por tu parte. Si quieres, pregúntame por la fase "
            "actual del proyecto. Sin prisa."
        )
        has_action = False
    else:
        message = (
            f"Tu próxima tarea: {pending_action}\n\n"
            "Cuando puedas. Sin prisa por tu parte."
        )
        has_action = True

    await _emit_copilot_audit_log(
        db,
        project_id=project_id,
        client_id=user.client_id,
        accion="cliente.coach.next_step.viewed",
        payload={
            "has_action": has_action,
            "current_phase": current_phase,
            "motor": motor,
        },
    )
    await db.commit()

    return PortalCoachNextStepResponse(
        has_action=has_action,
        current_phase=current_phase,
        message=message,
        pending_action_motor=motor,
        pending_action_template_id=tpl_id,
    )


_PORTAL_QUICK_ACTIONS: dict[str, list[dict]] = {
    "default": [
        {"id": "what_to_do_today", "label": "¿Qué toca hoy?",
         "prefill_query": "¿Qué tareas o hitos tengo pendientes hoy en mi proyecto ENS?"},
        {"id": "explain_phase", "label": "Explícame mi fase actual",
         "prefill_query": "¿En qué fase estoy y qué se espera de mí?"},
        {"id": "next_signing", "label": "¿Qué tengo que firmar?",
         "prefill_query": "Lista los documentos pendientes de firma de mi proyecto."},
    ],
    "magerit": [
        {"id": "magerit_explain", "label": "Explícame MAGERIT",
         "prefill_query": "¿Qué es MAGERIT y qué se me pide en esta fase?"},
        {"id": "magerit_assets", "label": "Mis activos",
         "prefill_query": "Resúmeme los activos identificados y por qué los marcamos críticos."},
    ],
    "dda": [
        {"id": "dda_pending", "label": "Medidas pendientes",
         "prefill_query": "¿Qué medidas DdA tengo pendientes de revisar?"},
        {"id": "dda_explain", "label": "¿Qué es una DdA?",
         "prefill_query": "Explícame qué es la Declaración de Aplicabilidad."},
    ],
    "conformidad": [
        {"id": "conformity_state", "label": "Estado conformidad",
         "prefill_query": "¿En qué estado de conformidad ENS está mi proyecto?"},
        {"id": "conformity_next", "label": "Próximos pasos",
         "prefill_query": "¿Qué pasos faltan para la conformidad final?"},
    ],
    "evidencias": [
        {"id": "evidence_pending", "label": "Evidencias pendientes",
         "prefill_query": "Lista las evidencias que tengo pendientes de aportar."},
        {"id": "evidence_explain", "label": "¿Qué es una evidencia?",
         "prefill_query": "Explícame qué considera una evidencia ENS válida."},
    ],
    "incidents": [
        {"id": "incident_what_to_do", "label": "Tengo un incidente",
         "prefill_query": "Tengo un incidente de seguridad. ¿Qué pasos sigo?"},
    ],
}


@router.get("/quick-actions")
async def portal_quick_actions(
    context: Optional[str] = None,
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Catalog of suggested copilot prompts per active page context.

    F-13-01 · gated por el cap copiloto cliente (defense-in-depth): cuando el
    cliente está hard-blocked se devuelve 429 para todo el copiloto, incluido
    el catálogo de sugerencias (UX coherente · no se ofrecen prompts que no
    podrá enviar). Autenticación añadida en el mismo cambio (el endpoint
    carecía de auth dep).
    """
    await _enforce_cliente_rate_limit(db, user)
    key = (context or "default").lower()
    return _PORTAL_QUICK_ACTIONS.get(key, _PORTAL_QUICK_ACTIONS["default"])


# ══════════════════ Workflow state hint cliente (Sesión 3B-2B.8 Phase 1D) ══════════════════


class PortalWorkflowHintResponse(BaseModel):
    """Top action hint cliente · workflow-aware R29 friendly."""

    has_action: bool
    message: str
    priority: str
    target_url: Optional[str] = None
    motor: Optional[str] = None
    action: Optional[str] = None
    current_phase: str


@router.get("/hint", response_model=PortalWorkflowHintResponse)
async def get_copilot_hint_cliente(
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> PortalWorkflowHintResponse:
    """Workflow-aware next-action hint (cliente role · R29 friendly) · Phase 1D.

    Reuse pure functional compute_workflow_state · backward-compat try/except.
    audit_log emit copilot.hint.generated con project_id + client_id Sub-atom 5.A.
    """
    from backend.app.motors.m11_copiloto.workflow_state_scanner import (
        WorkflowScannerOptions,
        compute_workflow_state,
        top_action_for_role,
    )

    # F-18-01 · contexto RLS (client_id + project_id) · sin esto /hint queda
    # ciego al proyecto del cliente y devuelve siempre "sin proyecto activo".
    project_id_str, _ens_category = await _resolve_project_meta_scoped(
        db, user.client_id,
    )
    if not project_id_str:
        return PortalWorkflowHintResponse(
            has_action=False,
            message="Aún no tienes un proyecto activo. Marcos te avisará.",
            priority="low",
            current_phase="pre_venta",
        )
    project_uuid = uuid.UUID(project_id_str)

    try:
        state = await compute_workflow_state(
            db, project_uuid,
            options=WorkflowScannerOptions(role_filter="cliente"),
        )
    except Exception:
        logger.exception("compute_workflow_state cliente · backward-compat fallback")
        return PortalWorkflowHintResponse(
            has_action=False,
            message="Sin sugerencias en este momento.",
            priority="low",
            current_phase="unknown",
        )

    top = top_action_for_role(state, "cliente")
    if top is None:
        return PortalWorkflowHintResponse(
            has_action=False,
            message="Todo al día · sin acciones pendientes por tu parte.",
            priority="low",
            current_phase=state.current_phase,
        )

    # audit_log emit copilot.hint.generated · Sub-atom 5.A pattern (best-effort)
    try:
        import json as _json
        await db.execute(text(
            "INSERT INTO audit_log (id, tabla, registro_id, accion, usuario, "
            "project_id, client_id, payload_new, timestamp) "
            "VALUES (gen_random_uuid(), 'copilot_hints', :pid, "
            "'copilot.hint.generated', :user, :pid, :cid, :payload, now())"
        ), {
            "pid": project_id_str,
            "cid": str(user.client_id),
            "user": (user.email or "cliente")[:255],
            "payload": _json.dumps({
                "role": "cliente",
                "phase": state.current_phase,
                "priority": top.priority,
                "action": top.action,
                "motor": top.motor,
            }),
        })
        await db.commit()
    except Exception:
        logger.exception("audit_log copilot.hint.generated cliente emit failed")

    return PortalWorkflowHintResponse(
        has_action=True,
        message=top.description_cliente,
        priority=top.priority,
        target_url=top.target_url,
        motor=top.motor,
        action=top.action,
        current_phase=state.current_phase,
    )
