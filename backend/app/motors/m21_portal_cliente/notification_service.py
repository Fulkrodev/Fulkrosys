"""ClientNotification service (SAN-E v3.MB-4.bis3 · ADR-020 v3 IMPLEMENTED FULLY).

Reemplaza emisión magic_link cliente · motors backend llaman
emit_client_notification() · cliente recibe en /client-portal/inbox.

Caller pattern (motors backend):
    from backend.app.motors.m21_portal_cliente.notification_service import (
        emit_client_notification,
    )
    await emit_client_notification(
        db=db,
        project_id=project.id,
        client_user_id=client_user.id,
        type='evidence_request',
        title='Aportar evidencia OBL-042',
        body='Necesitamos evidencia documental para la obligación X',
        target_url=f'/client-portal/evidencias?obligation={obligation.id}',
        priority='high',
        emitted_by_motor='m05',
    )

Bridge a cliente: cliente lee /api/v1/portal/notifications/inbox · click
target_url naviga a portal · marks actioned.

Sesión 3B-2B.8 CLUSTER 2 Phase 2D · DRY central SSE wire-completeness ·
emit_client_notification ahora dispatch SSE event `client_notification.created`
+ audit_log `cliente.notif.dispatched` (Sub-atom 5.A 3-way OR project_id +
client_id propagated) post-persist · best-effort try/except · primary persist
nunca bloqueado por side-effect failure. Forward-compat ALL VALID_TYPES
(report_available · acta_review · etc) realtime cliente inbox auto-refetch
sin modificar emitter motors específicos (DRY centralizado).
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.client_notification import ClientNotification

logger = logging.getLogger(__name__)


VALID_TYPES = {
    "evidence_request",
    "acta_review",
    "retainer_offer",
    "retainer_reconsideration",
    "onboarding_ready",
    "generic_alert",
    "invoice_review",
    "risk_validation",
    "compliance_confirmation",
    "meeting_invite",
    "scope_change_validation",
    "incident_report",
    "nps_survey",
    "vote_request",
    "report_available",
    "renewal_campaign",
    "info_request",
}

VALID_PRIORITIES = {"low", "normal", "high", "urgent"}


async def emit_client_notification(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    client_user_id: uuid.UUID,
    type: str,
    title: str,
    body: str | None,
    target_url: str,
    emitted_by_motor: str,
    priority: str = "normal",
    payload: dict[str, Any] | None = None,
    expires_at: datetime | None = None,
) -> ClientNotification:
    """Crea ClientNotification record. Llamado desde motors backend.

    Reemplaza emit magic_link cliente · cliente recibe en portal inbox.

    Raises:
        ValueError: type or priority no válido.
    """
    if type not in VALID_TYPES:
        raise ValueError(
            f"ClientNotification type inválido: {type!r} · "
            f"válidos: {sorted(VALID_TYPES)}"
        )
    if priority not in VALID_PRIORITIES:
        raise ValueError(
            f"ClientNotification priority inválido: {priority!r} · "
            f"válidos: {sorted(VALID_PRIORITIES)}"
        )

    notif = ClientNotification(
        project_id=project_id,
        client_user_id=client_user_id,
        type=type,
        title=title,
        body=body,
        target_url=target_url,
        priority=priority,
        payload_json=payload,
        emitted_by_motor=emitted_by_motor,
        expires_at=expires_at,
    )
    db.add(notif)
    await db.flush()

    # Sesión 3B-2B.8 CLUSTER 2 Phase 2D · SSE dispatch + audit_log emit
    # post-persist (best-effort independent · NO bloquea primary persist).
    # DRY centralizado: TODO emitter motor que llama emit_client_notification
    # obtiene SSE realtime + audit_log Sub-atom 5.A automatic sin modificar
    # callers existing (m_cloud_connectors digest + m05 obligations + m25
    # lifecycle + m09 dda_evidence_gap + m01/m02/m17 CLUSTER 1 Phase 2B).
    await _emit_notification_side_effects(
        db,
        notif=notif,
        project_id=project_id,
        client_user_id=client_user_id,
    )

    return notif


async def _emit_notification_side_effects(
    db: AsyncSession,
    *,
    notif: ClientNotification,
    project_id: uuid.UUID,
    client_user_id: uuid.UUID,
) -> None:
    """SSE dispatch + audit_log emit best-effort post emit_client_notification.

    Pattern notify_best_effort (Bloque 3+5 established): primary persist
    NUNCA bloqueado por side-effect failure. logger.exception en cada
    branch · graceful degradation forward-compat.

    Sub-atom 5.A 3-way OR audit_log entry:
    - project_id + client_id derived from project lookup
    - accion 'cliente.notif.dispatched' (≤20 chars VARCHAR limit ·
      audit_log.accion column post Sub-atom 5.A widen NO necesario aquí)
    - payload_new contiene notification metadata + emitter motor
    """
    # 1. SSE dispatch · client_notification.created event
    try:
        from backend.app.core.sse_dispatcher import sse_dispatcher

        sse_data = {
            "notification_id": str(notif.id),
            "type": notif.type,
            "title": notif.title,
            "target_url": notif.target_url,
            "priority": notif.priority,
            "client_user_id": str(client_user_id),
            "emitted_by_motor": notif.emitted_by_motor,
        }
        await sse_dispatcher.dispatch(
            f"project:{project_id}",
            "client_notification.created",
            sse_data,
        )
    except Exception:  # pragma: no cover · best-effort
        logger.exception(
            "SSE client_notification.created dispatch failed · notif_id=%s",
            notif.id,
        )

    # 2. audit_log emit · cliente.notif.dispatched (Sub-atom 5.A 3-way OR)
    try:
        # Resolve client_id from project (RLS coherence)
        client_id_row = (
            await db.execute(
                text(
                    "SELECT client_id FROM projects "
                    "WHERE id = :pid AND deleted_at IS NULL"
                ),
                {"pid": str(project_id)},
            )
        ).first()
        client_id_val = str(client_id_row[0]) if client_id_row else None

        audit_payload = {
            "notification_id": str(notif.id),
            "type": notif.type,
            "priority": notif.priority,
            "emitted_by_motor": notif.emitted_by_motor,
            "target_url": notif.target_url,
        }

        await db.execute(
            text(
                "INSERT INTO audit_log "
                "(id, tabla, registro_id, accion, usuario, "
                "project_id, client_id, payload_new, timestamp) "
                "VALUES (gen_random_uuid(), 'client_notification', "
                ":rid, :accion, :usuario, :pid, :cid, :payload, now())"
            ),
            {
                "rid": str(notif.id),
                "accion": "cliente.notif.dispatched",
                "usuario": notif.emitted_by_motor[:255]
                if notif.emitted_by_motor
                else "system",
                "pid": str(project_id),
                "cid": client_id_val,
                "payload": json.dumps(audit_payload),
            },
        )
        await db.flush()
    except Exception:  # pragma: no cover · best-effort
        logger.exception(
            "audit_log cliente.notif.dispatched emit failed · notif_id=%s",
            notif.id,
        )


async def list_inbox(
    db: AsyncSession,
    client_user_id: uuid.UUID,
    *,
    include_read: bool = False,
    include_dismissed: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> list[ClientNotification]:
    """Lista notifications del cliente · ordered DESC created_at."""
    stmt = select(ClientNotification).where(
        ClientNotification.client_user_id == client_user_id,
    )
    if not include_read:
        stmt = stmt.where(ClientNotification.read_at.is_(None))
    if not include_dismissed:
        stmt = stmt.where(ClientNotification.dismissed_at.is_(None))
    # Filter expired
    now = datetime.now(timezone.utc)
    stmt = stmt.where(
        or_(
            ClientNotification.expires_at.is_(None),
            ClientNotification.expires_at > now,
        )
    )
    stmt = stmt.order_by(ClientNotification.created_at.desc())
    stmt = stmt.limit(limit).offset(offset)
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def count_unread(
    db: AsyncSession, client_user_id: uuid.UUID,
) -> int:
    """Count notifications no leídas · no descartadas · no expiradas (badge UI)."""
    now = datetime.now(timezone.utc)
    stmt = select(func.count(ClientNotification.id)).where(
        ClientNotification.client_user_id == client_user_id,
        ClientNotification.read_at.is_(None),
        ClientNotification.dismissed_at.is_(None),
        or_(
            ClientNotification.expires_at.is_(None),
            ClientNotification.expires_at > now,
        ),
    )
    res = await db.execute(stmt)
    return int(res.scalar_one() or 0)


async def _verify_ownership(
    db: AsyncSession,
    notification_id: uuid.UUID,
    client_user_id: uuid.UUID,
) -> Optional[ClientNotification]:
    """Devuelve notification si ownership OK · None si no encontrada o ajena."""
    stmt = select(ClientNotification).where(
        ClientNotification.id == notification_id,
        ClientNotification.client_user_id == client_user_id,
    )
    res = await db.execute(stmt)
    return res.scalar_one_or_none()


async def mark_read(
    db: AsyncSession,
    notification_id: uuid.UUID,
    client_user_id: uuid.UUID,
) -> bool:
    """Verify ownership · update read_at. Returns False si no found."""
    notif = await _verify_ownership(db, notification_id, client_user_id)
    if notif is None:
        return False
    if notif.read_at is None:
        notif.read_at = datetime.now(timezone.utc)
        await db.flush()
    return True


async def mark_all_read(
    db: AsyncSession,
    client_user_id: uuid.UUID,
) -> int:
    """Mark every unread notification for the user as read · returns count."""
    from sqlalchemy import update

    now = datetime.now(timezone.utc)
    result = await db.execute(
        update(ClientNotification)
        .where(
            ClientNotification.client_user_id == client_user_id,
            ClientNotification.read_at.is_(None),
            ClientNotification.dismissed_at.is_(None),
        )
        .values(read_at=now)
    )
    await db.flush()
    return int(result.rowcount or 0)


async def dismiss(
    db: AsyncSession,
    notification_id: uuid.UUID,
    client_user_id: uuid.UUID,
) -> bool:
    """Verify ownership · update dismissed_at."""
    notif = await _verify_ownership(db, notification_id, client_user_id)
    if notif is None:
        return False
    if notif.dismissed_at is None:
        notif.dismissed_at = datetime.now(timezone.utc)
        await db.flush()
    return True


async def mark_actioned(
    db: AsyncSession,
    notification_id: uuid.UUID,
    client_user_id: uuid.UUID,
) -> bool:
    """Cliente clicked target_url · update actioned_at + read_at."""
    notif = await _verify_ownership(db, notification_id, client_user_id)
    if notif is None:
        return False
    now = datetime.now(timezone.utc)
    if notif.actioned_at is None:
        notif.actioned_at = now
    if notif.read_at is None:
        notif.read_at = now
    await db.flush()
    return True
