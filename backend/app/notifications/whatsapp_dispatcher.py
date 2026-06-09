"""CHANNEL_WHATSAPP routing dispatcher · MB-8 atom 8.2.

Decouples WhatsApp dispatch from NotificationOrchestrator core to avoid
touching the 300+ LOC ADR-039 orchestrator. Motor adapters call this
module directly for critical events; BASICA digest Celery aggregates
events and calls send_basica_digest.

Q5.A + tier-aware routing:
- BASICA tier → digest weekly (Monday 09:00 Europe/Madrid)
- MEDIA tier → per-event WhatsApp for critical
- ALTA tier → per-event WhatsApp for critical
- Per event_type override stored in whatsapp_critical_events_routing.

Q4.C bidirectional: outbound only here; cliente replies → handle_inbound
via webhook handler in m31_whatsapp/api.py.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Optional

from jinja2 import Template
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.client_portal import ClientUser
from backend.app.motors.m31_whatsapp.models import (
    WhatsAppCriticalEventRouting,
)
from backend.app.motors.m31_whatsapp.service import WhatsAppService


logger = logging.getLogger(__name__)


CHANNEL_WHATSAPP = "whatsapp"


@dataclass
class WhatsAppDispatchResult:
    dispatched: bool = False
    skipped_reason: Optional[str] = None
    route: Optional[str] = None
    message_id: Optional[str] = None
    errors: list[str] = field(default_factory=list)


def _route_for_tier(
    routing: WhatsAppCriticalEventRouting, tier: str | None,
) -> str:
    """Resolve the per-tier route enum value."""
    if tier == "BASICA":
        return routing.tier_basica_route
    if tier == "MEDIA":
        return routing.tier_media_route
    if tier == "ALTA":
        return routing.tier_alta_route
    return "silent"  # unknown tier · silent fallback


async def _resolve_project_tier(
    db: AsyncSession, project_id: uuid.UUID,
) -> Optional[str]:
    row = (await db.execute(
        text(
            "SELECT categoria_objetivo FROM projects "
            "WHERE id = :pid AND deleted_at IS NULL"
        ),
        {"pid": str(project_id)},
    )).first()
    return row[0] if row else None


async def dispatch_critical_event(
    db: AsyncSession,
    *,
    event_type: str,
    project_id: uuid.UUID,
    client_user_id: uuid.UUID,
    payload: dict,
    wa_service: Optional[WhatsAppService] = None,
) -> WhatsAppDispatchResult:
    """Dispatch a single critical event via WhatsApp if routing rules permit.

    Steps:
      1. Lookup routing row for event_type · skip if missing.
      2. Resolve project tier · skip if 'silent' or 'digest' route.
      3. Check cliente opt-in active · skip if not opted in.
      4. Render template_es with payload via Jinja2.
      5. send_outbound via WhatsAppService.
    """
    result = WhatsAppDispatchResult()

    routing = (await db.execute(
        select(WhatsAppCriticalEventRouting).where(
            WhatsAppCriticalEventRouting.event_type == event_type,
        )
    )).scalar_one_or_none()
    if routing is None:
        result.skipped_reason = f"no_routing_for_{event_type}"
        return result

    tier = await _resolve_project_tier(db, project_id)
    route = _route_for_tier(routing, tier)
    result.route = route
    if route in ("silent", "digest"):
        result.skipped_reason = f"route_is_{route}"
        return result
    if route != "whatsapp":
        result.skipped_reason = f"route_is_{route}_handled_elsewhere"
        return result

    user = (await db.execute(
        select(ClientUser).where(ClientUser.id == client_user_id)
    )).scalar_one_or_none()
    if user is None:
        result.skipped_reason = "user_not_found"
        return result
    if user.whatsapp_opt_in_at is None:
        result.skipped_reason = "no_opt_in"
        return result
    if not user.whatsapp_number:
        result.skipped_reason = "no_phone"
        return result

    try:
        rendered = Template(routing.template_es).render(**(payload or {}))
    except Exception as exc:  # noqa: BLE001
        result.errors.append(f"template_render: {exc}")
        return result

    svc = wa_service or WhatsAppService()
    thread = await svc.get_or_create_thread(
        db, project_id=project_id, client_user_id=client_user_id,
    )
    try:
        msg = await svc.send_outbound(
            db, thread=thread, body=rendered, sender_type="system",
        )
        result.dispatched = True
        result.message_id = str(msg.id)
    except Exception as exc:  # noqa: BLE001
        result.errors.append(f"send_outbound: {exc}")

    return result


@dataclass
class DigestSummary:
    project_id: str
    client_user_id: str
    events_in_window: int
    sent: bool = False
    error: Optional[str] = None


async def send_media_daily_digest_for_project(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    client_user_id: uuid.UUID,
    wa_service: Optional[WhatsAppService] = None,
) -> DigestSummary:
    """MEDIA tier daily digest · 24h aggregation · MB-8 closure.

    Same semantics as send_basica_digest_for_project but with lookback=1.
    Caller is m31.media_digest_daily Celery task (09:00 Europe/Madrid).
    """
    return await send_basica_digest_for_project(
        db,
        project_id=project_id,
        client_user_id=client_user_id,
        lookback_days=1,
        wa_service=wa_service,
    )


async def send_basica_digest_for_project(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    client_user_id: uuid.UUID,
    lookback_days: int = 7,
    wa_service: Optional[WhatsAppService] = None,
) -> DigestSummary:
    """Aggregate critical events of last `lookback_days` and send 1 WA digest.

    Only sends if there's at least 1 event in window · skips silent week.
    """
    from datetime import datetime, timedelta, timezone

    summary = DigestSummary(
        project_id=str(project_id),
        client_user_id=str(client_user_id),
        events_in_window=0,
    )

    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    # Aggregate count of critical drift/incident rows · placeholder query.
    row = (await db.execute(text(
        "SELECT COALESCE(SUM(count), 0) AS total FROM ( "
        " SELECT count(*) AS count FROM retainer_drift_events "
        "  WHERE project_id = :pid AND severidad IN ('HIGH', 'CRITICAL') "
        "  AND created_at > :cutoff "
        " UNION ALL "
        " SELECT count(*) FROM incidents "
        "  WHERE project_id = :pid AND workflow_state IN ('resolved', 'closed') "
        "  AND created_at > :cutoff "
        ") s"
    ), {"pid": str(project_id), "cutoff": cutoff})).first()
    count = int(row[0] or 0) if row else 0
    summary.events_in_window = count
    if count == 0:
        summary.skipped_reason = "no_events"  # type: ignore[attr-defined]
        return summary

    user = (await db.execute(
        select(ClientUser).where(ClientUser.id == client_user_id)
    )).scalar_one_or_none()
    if (
        user is None
        or user.whatsapp_opt_in_at is None
        or not user.whatsapp_number
    ):
        summary.error = "no_opt_in_or_phone"
        return summary

    body = (
        f"Resumen semanal FULKRO: {count} eventos críticos detectados "
        f"esta semana. Ver detalle: https://fulkro.es/client-portal/dashboard"
    )
    svc = wa_service or WhatsAppService()
    thread = await svc.get_or_create_thread(
        db, project_id=project_id, client_user_id=client_user_id,
    )
    try:
        await svc.send_outbound(
            db, thread=thread, body=body, sender_type="system",
        )
        summary.sent = True
    except Exception as exc:  # noqa: BLE001
        summary.error = str(exc)[:200]

    return summary
