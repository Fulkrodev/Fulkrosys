"""Servicio del Motor 16 Adaptive Onboarding.

Sub-pase M16-A: foundation. Creacion de sessions desde Marcos + listing +
state transitions. El flujo cliente (consume magic link + responder preguntas)
viene en M16-B.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.onboarding import OnboardingSession
from backend.app.motors.m12_magic_link.service import MagicLinkService, MagicLinkNotFoundError
from backend.app.motors.m12_magic_link.purposes import MagicLinkPurpose
from backend.app.motors.m12_magic_link.schemas import MagicLinkGenerateRequest

from .catalog_loader import find_template_for
from .enums import Role, Sector, SessionState


class OnboardingServiceError(ValueError):
    pass


async def create_session(
    db: AsyncSession,
    project_id: uuid.UUID,
    sector: Sector,
    role: Role,
    interlocutor_email: str,
    interlocutor_name: Optional[str],
    ttl_hours: int,
    language: str,
    metadata_extra: Optional[dict],
    purpose: Optional[MagicLinkPurpose] = None,
    lead_id: Optional[uuid.UUID] = None,
) -> dict:
    """Create a new onboarding session.

    Post-MB-4.bis3 (ADR-020 v3 IMPLEMENTED FULLY): NO genera magic_link
    cliente. Cliente accede el wizard vía /client-portal/onboarding con
    su sesión ClientUser (post-firma C-001 cuenta portal activada).
    El admin panel (MB-4.3) lista y gestiona sessions sin necesidad de
    magic_link issuance.

    Batch A diagnóstico previo (additive · acotado): si
    ``purpose == DIAGNOSTICO_PRECLIENTE`` se emite un magic-link account-less
    (scope={session_id}) para que el LEAD responda SIN cuenta vía el flujo
    consume + /me/* existente. Default (``purpose=None``) preserva el
    comportamiento in-portal ADR-020 v3 (magic_link_id=None · NO regresión).
    """
    template = find_template_for(sector, role)
    if template is None:
        raise OnboardingServiceError(
            f'No hay plantilla de onboarding para sector={sector.value} role={role.value}. '
            f'Disponibles: revisar catalogo en GET /api/v1/onboarding/catalog'
        )

    session_id = uuid.uuid4()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)

    onb = OnboardingSession(
        id=session_id,
        project_id=project_id,
        lead_id=lead_id,  # #7.3 · formaliza la traza lead↔onboarding
        sector=sector.value,
        rol_receptor=role.value,
        interlocutor_email=interlocutor_email,
        interlocutor_nombre=interlocutor_name,
        magic_link_id=None,  # ADR-020 v3 hard-rejection · cliente in-portal
        estado=SessionState.CREATED.value,
        template_id_str=template.id,
        total_questions=len(template.questions),
        answered_questions=0,
        language=language,
        metadata_extra=metadata_extra,
        expires_at=expires_at,
    )
    db.add(onb)
    await db.flush()

    # Batch A diagnóstico previo: emisión magic-link account-less SOLO para el
    # purpose precliente (gated). El lead recibe el link y entra sin cuenta via
    # POST /onboarding/consume → session_secret → /me/*. scope.session_id es lo
    # que consume_magic_link_and_start usa para localizar la sesión.
    magic_link_id = None
    magic_link_url = None
    if purpose == MagicLinkPurpose.DIAGNOSTICO_PRECLIENTE:
        from backend.app.config import get_settings
        ml_resp = await MagicLinkService(db).generate_magic_link(
            MagicLinkGenerateRequest(
                project_id=project_id,
                purpose=MagicLinkPurpose.DIAGNOSTICO_PRECLIENTE,
                recipient_email=interlocutor_email,
                scope={"session_id": str(session_id)},
            ),
            base_url=get_settings().app_base_url,
        )
        onb.magic_link_id = ml_resp.magic_link_id
        await db.flush()
        magic_link_id = ml_resp.magic_link_id
        magic_link_url = ml_resp.url

    return {
        'session_id': session_id,
        'template_id': template.id,
        'template_nombre': template.nombre,
        'tiempo_estimado_minutos': template.tiempo_estimado_minutos,
        'total_questions': len(template.questions),
        'magic_link_id': magic_link_id,
        'magic_link_url': magic_link_url,
        'otp': None,
        'expires_at': expires_at,
        'state': SessionState.CREATED,
        'portal_url': f'/client-portal/onboarding',
    }


def _check_expiration(onb: OnboardingSession) -> None:
    """Auto-expire sessions past their expires_at on read."""
    if onb.estado in (SessionState.CREATED.value, SessionState.SENT.value):
        if onb.expires_at and onb.expires_at.replace(tzinfo=timezone.utc if onb.expires_at.tzinfo is None else onb.expires_at.tzinfo) < datetime.now(timezone.utc):
            onb.estado = SessionState.EXPIRED.value


async def list_sessions_by_project(
    db: AsyncSession,
    project_id: uuid.UUID,
    state_filter: Optional[SessionState] = None,
    role_filter: Optional[Role] = None,
) -> list[dict]:
    stmt = (
        select(OnboardingSession)
        .where(OnboardingSession.project_id == project_id)
        .where(OnboardingSession.deleted_at.is_(None))
    )
    if state_filter:
        stmt = stmt.where(OnboardingSession.estado == state_filter.value)
    if role_filter:
        stmt = stmt.where(OnboardingSession.rol_receptor == role_filter.value)
    stmt = stmt.order_by(OnboardingSession.created_at.desc())

    r = await db.execute(stmt)
    sessions = r.scalars().all()
    for s in sessions:
        _check_expiration(s)
    await db.flush()
    return [_to_summary(s) for s in sessions]


async def get_session_detail(db: AsyncSession, session_id: uuid.UUID) -> dict:
    r = await db.execute(
        select(OnboardingSession)
        .where(OnboardingSession.id == session_id)
        .where(OnboardingSession.deleted_at.is_(None))
    )
    s = r.scalar_one_or_none()
    if s is None:
        raise OnboardingServiceError(f'Session {session_id} no existe')
    return _to_summary(s, detail=True)


async def mark_session_sent(db: AsyncSession, session_id: uuid.UUID) -> dict:
    r = await db.execute(
        select(OnboardingSession)
        .where(OnboardingSession.id == session_id)
        .where(OnboardingSession.deleted_at.is_(None))
    )
    s = r.scalar_one_or_none()
    if s is None:
        raise OnboardingServiceError(f'Session {session_id} no existe')
    if s.estado != SessionState.CREATED.value:
        raise OnboardingServiceError(
            f'Session {session_id} no esta en estado created (actual: {s.estado})'
        )

    now = datetime.now(timezone.utc)
    s.estado = SessionState.SENT.value
    s.sent_at = now
    await db.flush()

    return {
        'session_id': session_id,
        'state': SessionState.SENT,
        'sent_at': now,
    }


async def cancel_session(
    db: AsyncSession, session_id: uuid.UUID, reason: Optional[str],
) -> dict:
    r = await db.execute(
        select(OnboardingSession)
        .where(OnboardingSession.id == session_id)
        .where(OnboardingSession.deleted_at.is_(None))
    )
    s = r.scalar_one_or_none()
    if s is None:
        raise OnboardingServiceError(f'Session {session_id} no existe')
    if s.estado == SessionState.COMPLETED.value:
        raise OnboardingServiceError(f'Session {session_id} ya esta completada')
    if s.estado == SessionState.CANCELLED.value:
        raise OnboardingServiceError(f'Session {session_id} ya estaba cancelada')

    magic_link_revoked = False
    if s.magic_link_id is not None:
        try:
            ml_service = MagicLinkService(db)
            await ml_service.revoke_magic_link(
                magic_link_id=s.magic_link_id,
                reason=f'onboarding_cancelled: {reason or "manual"}',
            )
            magic_link_revoked = True
        except MagicLinkNotFoundError:
            pass

    s.estado = SessionState.CANCELLED.value
    meta = s.metadata_extra or {}
    meta['cancellation_reason'] = reason
    meta['cancelled_at'] = datetime.now(timezone.utc).isoformat()
    s.metadata_extra = meta
    await db.flush()

    return {
        'session_id': session_id,
        'state': SessionState.CANCELLED,
        'magic_link_revoked': magic_link_revoked,
    }


def _to_summary(s: OnboardingSession, detail: bool = False) -> dict:
    total = s.total_questions or 0
    answered = s.answered_questions or 0
    progress = round(100.0 * answered / total, 1) if total > 0 else 0.0

    base = {
        'id': s.id,
        'project_id': s.project_id,
        'template_id': s.template_id_str,
        'sector': s.sector,
        'role': s.rol_receptor,
        'interlocutor_email': s.interlocutor_email,
        'interlocutor_name': s.interlocutor_nombre,
        'state': s.estado,
        'total_questions': total,
        'answered_questions': answered,
        'progress_percentage': progress,
        'created_at': s.created_at,
        'sent_at': s.sent_at,
        'started_at': s.iniciado_at,
        'completed_at': s.completado_at,
        'expires_at': s.expires_at,
    }
    if detail:
        base['magic_link_id'] = s.magic_link_id
        base['language'] = s.language
        base['metadata_extra'] = s.metadata_extra
    return base
