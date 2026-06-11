"""Portal API wrappers for M16 onboarding (SAN-E v3.MB-4.2.bis · Q1-B).

Wrappers separados /api/v1/portal/onboarding/* con auth ClientUser.
Internamente reusa servicios admin existentes (client_service · service ·
lms_service) con scope cliente · audit log con client_user_id.

11 endpoints (10 portal-facing + 1 AWS especial):
- GET    /projects/{project_id}/status
- GET    /projects/{project_id}/next-question
- POST   /projects/{project_id}/answer
- GET    /projects/{project_id}/connectors
- POST   /projects/{project_id}/connectors/{connector_type}/oauth-init
- POST   /projects/{project_id}/connectors/{connector_type}/oauth-callback
- POST   /projects/{project_id}/connectors/aws/credentials
- POST   /projects/{project_id}/connectors/{connector_type}/sync
- GET    /projects/{project_id}/lms
- POST   /projects/{project_id}/lms/{assignment_id}/complete
- POST   /projects/{project_id}/finish

Decisión arquitectónica Q1-B (audit MB-4.0):
- Wrappers separados (NO reuse admin endpoints)
- Auth ClientUser context · audit log distinto admin vs portal
- Alinea ADR-019 portal isolation + cleanup M21 single-user-RW
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.models.client_portal import ClientUser
from backend.app.models.core import Project
from backend.app.models.lms import LmsAssignment
from backend.app.models.onboarding import (
    ConnectorConfig,
    OnboardingSession,
)
from backend.app.motors.m16_onboarding import client_service, lms_service
from backend.app.motors.m16_onboarding import oauth_service, oauth_state_service
from backend.app.motors.m21_portal_cliente.api import get_current_client_user


router = APIRouter(
    prefix="/api/v1/portal/onboarding",
    tags=["m16-portal-onboarding"],
)


# =====================================================================
# Pydantic schemas
# =====================================================================

class AnswerPayload(BaseModel):
    question_id: str = Field(..., min_length=1, max_length=80)
    answer: Any


class OAuthInitPayload(BaseModel):
    redirect_uri: str = Field(..., min_length=1, max_length=512)


class OAuthCallbackPayload(BaseModel):
    code: str = Field(..., min_length=1)
    state: str = Field(..., min_length=1)


class AWSCredentialsPayload(BaseModel):
    access_key_id: str = Field(..., min_length=16, max_length=128)
    secret_access_key: str = Field(..., min_length=16, max_length=256)
    region: str = Field(..., min_length=2, max_length=32)


class StatusResponse(BaseModel):
    session_id: str | None = None
    estado: str | None = None
    answered_questions: int = 0
    total_questions: int = 0
    progress_pct: int = 0
    template_id: str | None = None


class ConnectorStatus(BaseModel):
    connector_type: str
    available: bool
    connected: bool
    status: str
    last_discovery_at: str | None = None
    auth_method: str = "oauth"


class FinishResponse(BaseModel):
    completed: bool
    completed_at: str | None = None
    next_step_url: str | None = None


# =====================================================================
# Helpers
# =====================================================================

async def _verify_project_belongs_to_client_user(
    db: AsyncSession, project_id: uuid.UUID, client_user: ClientUser,
) -> Project:
    """Scope check: project debe pertenecer al client_id del ClientUser."""
    res = await db.execute(select(Project).where(Project.id == project_id))
    project = res.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.client_id != client_user.client_id:
        raise HTTPException(
            status_code=403,
            detail="Project no pertenece a tu cliente · scope denied",
        )
    return project


async def _get_active_session(
    db: AsyncSession, project_id: uuid.UUID,
) -> OnboardingSession:
    """Recupera onboarding session activa para project · 404 si no existe."""
    res = await db.execute(
        select(OnboardingSession)
        .where(OnboardingSession.project_id == project_id)
        .order_by(OnboardingSession.created_at.desc())
        .limit(1)
    )
    onb = res.scalar_one_or_none()
    if onb is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Onboarding session no encontrada · Marcos debe crear una sesión "
                "desde el panel admin antes de continuar."
            ),
        )
    return onb


# =====================================================================
# Onboarding wizard
# =====================================================================

@router.get("/projects/{project_id}/status", response_model=StatusResponse)
async def portal_get_status(
    project_id: uuid.UUID,
    client_user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> StatusResponse:
    """Estado del onboarding del cliente para un project."""
    await _verify_project_belongs_to_client_user(db, project_id, client_user)
    onb = await _get_active_session(db, project_id)
    answered = onb.answered_questions or 0
    total = onb.total_questions or 0
    pct = int(round(answered * 100 / total)) if total > 0 else 0
    return StatusResponse(
        session_id=str(onb.id),
        estado=onb.estado,
        answered_questions=answered,
        total_questions=total,
        progress_pct=pct,
        template_id=onb.template_id_str,
    )


@router.get("/projects/{project_id}/next-question")
async def portal_get_next_question(
    project_id: uuid.UUID,
    client_user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Próxima pregunta a contestar (branching evaluado · client_service)."""
    await _verify_project_belongs_to_client_user(db, project_id, client_user)
    onb = await _get_active_session(db, project_id)
    return await client_service.get_next_question(db, onb)


@router.post("/projects/{project_id}/answer")
async def portal_post_answer(
    project_id: uuid.UUID,
    payload: AnswerPayload,
    client_user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Guarda respuesta del cliente · avanza wizard · evalúa branching."""
    await _verify_project_belongs_to_client_user(db, project_id, client_user)
    onb = await _get_active_session(db, project_id)
    try:
        result = await client_service.save_answer(
            db, onb=onb,
            question_id=payload.question_id,
            answer_value=payload.answer,
        )
    except (ValueError, client_service.OnboardingClientError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    await db.commit()
    return result


# =====================================================================
# Connectors
# =====================================================================

@router.get("/projects/{project_id}/connectors")
async def portal_list_connectors(
    project_id: uuid.UUID,
    client_user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, list[ConnectorStatus]]:
    """Lista 6 connectors disponibles + estado configurado per project."""
    await _verify_project_belongs_to_client_user(db, project_id, client_user)
    res = await db.execute(
        select(ConnectorConfig).where(ConnectorConfig.project_id == project_id)
    )
    configured = {c.provider: c for c in res.scalars().all()}

    result: list[ConnectorStatus] = []
    for connector_type in ("github", "microsoft", "azure", "google", "base", "aws"):
        existing = configured.get(connector_type)
        result.append(
            ConnectorStatus(
                connector_type=connector_type,
                available=True,
                connected=existing is not None,
                status=existing.status if existing else "not_connected",
                last_discovery_at=(
                    existing.last_discovery_at.isoformat()
                    if existing and existing.last_discovery_at
                    else None
                ),
                auth_method=("iam_access_key" if connector_type == "aws" else "oauth"),
            ),
        )
    return {"connectors": result}


@router.post("/projects/{project_id}/connectors/{connector_type}/oauth-init")
async def portal_oauth_init(
    project_id: uuid.UUID,
    connector_type: str,
    payload: OAuthInitPayload,
    client_user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Inicia OAuth flow para 5 providers · genera state + authorize URL.

    AWS NO soporta OAuth · responde 405 con instrucción a /aws/credentials.
    """
    if connector_type == "aws":
        raise HTTPException(
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
            detail=(
                "AWS no usa OAuth · usa POST "
                "/portal/onboarding/projects/{project_id}/connectors/aws/credentials "
                "con access_key_id + secret_access_key + region."
            ),
        )
    if connector_type not in oauth_service.SUPPORTED_OAUTH_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Provider no soportado: {connector_type}",
        )
    await _verify_project_belongs_to_client_user(db, project_id, client_user)

    # oauth_state_tokens es fail-CLOSED (RLS project-scoped). El state token es un
    # bearer secreto single-use generado ANTES de fijar contexto de proyecto; se
    # emite vía rol BYPASSRLS (autorización ya verificada arriba por cliente+proyecto).
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))

    provider_cfg = oauth_service._provider_configs()[connector_type]
    state, code_challenge = await oauth_state_service.create_state(
        db,
        client_user_id=client_user.id,
        project_id=project_id,
        connector_type=connector_type,
        redirect_uri=payload.redirect_uri,
        use_pkce=provider_cfg.requires_pkce,
    )

    try:
        authorize_url = oauth_service.build_authorize_url(
            connector_type=connector_type,
            state=state,
            redirect_uri=payload.redirect_uri,
            code_challenge=code_challenge,
        )
    except oauth_service.OAuthError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    await db.commit()
    return {"authorize_url": authorize_url, "state": state}


@router.post("/projects/{project_id}/connectors/{connector_type}/oauth-callback")
async def portal_oauth_callback(
    project_id: uuid.UUID,
    connector_type: str,
    payload: OAuthCallbackPayload,
    client_user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Recibe authorization code + state · valida · intercambia tokens · persiste."""
    if connector_type == "aws":
        raise HTTPException(
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
            detail="AWS no usa OAuth callback",
        )
    await _verify_project_belongs_to_client_user(db, project_id, client_user)

    # oauth_state_tokens es fail-CLOSED (RLS project-scoped) y el callback corre SIN
    # contexto de proyecto fijado (el state token ES quien lo resuelve). Se eleva a
    # BYPASSRLS para el lookup/consume del token bearer (replay-guard via consumed_at +
    # validación de scope client_user/project explícita más abajo).
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))

    try:
        ctx = await oauth_state_service.validate_and_consume(db, payload.state)
    except oauth_state_service.OAuthStateError as exc:
        raise HTTPException(status_code=401, detail=str(exc))

    if ctx.connector_type != connector_type:
        raise HTTPException(
            status_code=400,
            detail="State token connector_type mismatch (cross-flow attempt)",
        )
    if ctx.client_user_id != client_user.id or ctx.project_id != project_id:
        raise HTTPException(
            status_code=403,
            detail="State token scope mismatch (client_user/project)",
        )

    try:
        tokens = await oauth_service.exchange_code(
            connector_type=connector_type,
            code=payload.code,
            redirect_uri=ctx.redirect_uri,
            code_verifier=ctx.code_verifier,
        )
    except oauth_service.OAuthError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    cfg_record = await oauth_service.persist_oauth_connector(
        db,
        project_id=project_id,
        connector_type=connector_type,
        tokens=tokens,
    )
    await db.commit()
    return {
        "connected": True,
        "connector_id": str(cfg_record.id),
        "status": cfg_record.status,
    }


@router.post("/projects/{project_id}/connectors/aws/credentials")
async def portal_aws_credentials(
    project_id: uuid.UUID,
    payload: AWSCredentialsPayload,
    client_user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """AWS especial · paste IAM access key · validate via STS · persist."""
    await _verify_project_belongs_to_client_user(db, project_id, client_user)
    try:
        identity = await oauth_service.aws_validate_credentials(
            access_key_id=payload.access_key_id,
            secret_access_key=payload.secret_access_key,
            region=payload.region,
        )
    except oauth_service.OAuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    record = await oauth_service.persist_aws_connector(
        db,
        project_id=project_id,
        access_key_id=payload.access_key_id,
        secret_access_key=payload.secret_access_key,
        region=payload.region,
        identity_summary=identity,
    )
    await db.commit()
    return {
        "connected": True,
        "connector_id": str(record.id),
        "account_id": identity.get("account_id"),
        "arn": identity.get("arn"),
    }


@router.post("/projects/{project_id}/connectors/{connector_type}/sync")
async def portal_connector_sync(
    project_id: uuid.UUID,
    connector_type: str,
    client_user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Trigger sync M22 discovery · placeholder hasta wiring orchestrator."""
    await _verify_project_belongs_to_client_user(db, project_id, client_user)
    res = await db.execute(
        select(ConnectorConfig).where(
            ConnectorConfig.project_id == project_id,
            ConnectorConfig.provider == connector_type,
        )
    )
    record = res.scalar_one_or_none()
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=f"Connector {connector_type} no configurado · usa oauth-init primero",
        )
    record.last_discovery_at = datetime.now(timezone.utc)
    record.status = "sync_triggered"
    await db.commit()
    return {
        "triggered": True,
        "connector_type": connector_type,
        "status": "sync_triggered",
        "note": (
            "Sync M22 discovery wiring pendiente extension · ahora solo marca "
            "last_discovery_at + status."
        ),
    }


# =====================================================================
# LMS
# =====================================================================

@router.get("/projects/{project_id}/lms")
async def portal_list_lms(
    project_id: uuid.UUID,
    client_user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Lista assignments LMS del project · catálogo cursos disponibles."""
    await _verify_project_belongs_to_client_user(db, project_id, client_user)
    res = await db.execute(
        select(LmsAssignment).where(LmsAssignment.project_id == project_id)
    )
    assignments = res.scalars().all()
    return {
        "assignments": [
            {
                "id": str(a.id),
                "course_codigo": a.course_codigo,
                "course_titulo": a.course_titulo,
                "asistente_nombre": a.asistente_nombre,
                "asistente_email": a.asistente_email,
                "estado": a.estado,
                "asignado_at": (
                    a.asignado_at.isoformat() if a.asignado_at else None
                ),
                "completado_at": (
                    a.completado_at.isoformat() if a.completado_at else None
                ),
                "quiz_score": a.quiz_score,
                "quiz_pass": a.quiz_pass,
            }
            for a in assignments
        ],
        "courses_available": lms_service.list_courses(),
    }


@router.post("/projects/{project_id}/lms/{assignment_id}/complete")
async def portal_complete_lms(
    project_id: uuid.UUID,
    assignment_id: uuid.UUID,
    client_user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Marca assignment LMS como completado · genera registro asistencia."""
    await _verify_project_belongs_to_client_user(db, project_id, client_user)
    res = await db.execute(
        select(LmsAssignment).where(
            LmsAssignment.id == assignment_id,
            LmsAssignment.project_id == project_id,
        )
    )
    assignment = res.scalar_one_or_none()
    if assignment is None:
        raise HTTPException(status_code=404, detail="LMS assignment not found")
    assignment.estado = "completado"
    assignment.completado_at = datetime.now(timezone.utc)
    await db.commit()
    return {
        "completed": True,
        "assignment_id": str(assignment.id),
        "completado_at": assignment.completado_at.isoformat(),
    }


# =====================================================================
# Finish
# =====================================================================

@router.post("/projects/{project_id}/finish", response_model=FinishResponse)
async def portal_finish_onboarding(
    project_id: uuid.UUID,
    client_user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> FinishResponse:
    """Finaliza onboarding · valida required questions answered · advance phase.

    Reusa client_service.submit_onboarding (admin existing) con scope cliente.
    """
    await _verify_project_belongs_to_client_user(db, project_id, client_user)
    onb = await _get_active_session(db, project_id)
    try:
        result = await client_service.submit_onboarding(
            db, onb=onb, allow_partial=False, updated_by=client_user.id,
        )
    except (ValueError, client_service.OnboardingClientError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    await db.commit()
    completed_at_raw = result.get("completed_at") if isinstance(result, dict) else None
    completed_at_str: str | None
    if isinstance(completed_at_raw, datetime):
        completed_at_str = completed_at_raw.isoformat()
    elif isinstance(completed_at_raw, str):
        completed_at_str = completed_at_raw
    else:
        completed_at_str = None
    return FinishResponse(
        completed=True,
        completed_at=completed_at_str,
        next_step_url=f"/client-portal/projects/{project_id}/dashboard",
    )
