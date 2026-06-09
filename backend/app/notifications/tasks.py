"""Celery tasks NotificationOrchestrator MB-16.4 (ADR-039).

Tasks expuestas:

1. ``notifications.dispatch_event`` · re-dispatch event marcado failed
   (manual replay vía API admin o re-trigger automático future enhancement).
   Usa retry framework Celery (``bind=True``, ``autoretry_for``,
   ``max_retries=3``, ``countdown=60``) sobre el retry exponencial built-in
   de EmailSender (2s · 8s · 32s) → defensa profundidad fallos transient
   infraestructura.

2. ``notifications.scan_client_inactivity`` · scan diario que detecta
   ClientUsers sin actividad portal últimos N días
   (``Settings.client_inactivity_threshold_days``, default 14d) y dispara:
   - AlertService.trigger_alert categoría ``client_inactivity`` por cada
     ClientUser inactivo (UI admin /admin/alerts SSE refresh).
   - NotificationOrchestrator.enqueue_with_template
     ``client_inactivity_admin`` → email admin configurado (digest unificado por
     cliente).

   Cosecha CELERY-CLIENT-INACTIVITY deferred MB-14 (DECISIONS.md ADR-038
   sección Deferrables · re-asignado MB-16). Beat schedule daily 09:00
   Europe/Madrid (post-WhatsApp hours start si Marcos respeta DND propio).

Stub-friendly: si Celery no instalado (dev/tests), el decorador
``@celery_app.task`` actúa como identity decorator (ver
``backend/app/core/celery_app.py``). Tasks pueden invocarse direct
síncronamente desde tests vía ``await scan_client_inactivity_async()``.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from loguru import logger
from sqlalchemy import select, text

from backend.app.config import get_settings
from backend.app.core.celery_app import celery_app
from backend.app.database import async_session
from backend.app.models.client_portal import ClientUser
from backend.app.models.notifications import NotificationEvent
from backend.app.motors.m18_communication.alert_service import AlertService
from backend.app.notifications.deep_links import DeepLinkGenerator
from backend.app.notifications.orchestrator import NotificationOrchestrator


def _ensure_loop() -> asyncio.AbstractEventLoop:
    """Reutiliza event loop o crea uno nuevo · safe en Celery sync worker."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("loop closed")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop


@celery_app.task(
    name="notifications.dispatch_event",
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 60},
    acks_late=True,
)
def dispatch_event(self, event_id: str) -> dict:
    """Re-dispatch a NotificationEvent que falló previamente.

    Args:
        event_id: UUID del NotificationEvent a re-dispatchar.

    Returns:
        dict con status final + channels detail.

    Reintenta automaticamente hasta 3 veces con countdown 60s vía
    Celery autoretry_for. EmailSender retry built-in (2s · 8s · 32s)
    aplica dentro de cada attempt → 4 attempts × 3 sub-attempts = 12
    intentos posibles antes de mark final failed.
    """
    logger.info(
        "notifications.dispatch_event task triggered event_id=%s task_id=%s",
        event_id, getattr(self.request, "id", "sync"),
    )
    loop = _ensure_loop()
    return loop.run_until_complete(_redispatch_event_async(event_id))


@celery_app.task(name="notifications.scan_client_inactivity")
def scan_client_inactivity() -> dict:
    """Scan diario · detecta ClientUsers inactivos + dispara alerts.

    Scheduled: daily 09:00 Europe/Madrid (Celery beat).

    Returns:
        dict con stats: total_scanned, inactive_count, alerts_created,
        notifications_enqueued.
    """
    logger.info("notifications.scan_client_inactivity task triggered")
    loop = _ensure_loop()
    return loop.run_until_complete(scan_client_inactivity_async())


# ──────────────────────── Async helpers ────────────────────────


async def _redispatch_event_async(event_id: str) -> dict:
    async with async_session() as db:
        try:
            result = await redispatch_event_with_session(db, event_id)
            await db.commit()
            return result
        except Exception:
            await db.rollback()
            raise


async def redispatch_event_with_session(db, event_id: str) -> dict:
    """Núcleo del re-dispatch · acepta session existente (test override).

    NO commit/rollback aquí · el caller decide.
    """
    eid = uuid.UUID(event_id)
    result = await db.execute(
        select(NotificationEvent).where(NotificationEvent.id == eid)
    )
    event = result.scalar_one_or_none()
    if event is None:
        logger.warning(
            "notifications.dispatch_event · event %s not found",
            event_id,
        )
        return {"status": "not_found", "event_id": event_id}

    if event.status == "delivered":
        logger.info(
            "notifications.dispatch_event · event %s already delivered · skip",
            event_id,
        )
        return {"status": "already_delivered", "event_id": event_id}

    payload = event.payload_jsonb or {}
    template_name = event.template_used
    render_context = payload.get("_render_context") or {}

    if template_name and render_context:
        orch = NotificationOrchestrator(db)
        outcome = await orch.enqueue_with_template(
            event_type=event.event_type,
            template_name=template_name,
            template_context=render_context,
            recipient_email=event.recipient_email,
            recipient_user_id=event.recipient_user_id,
            project_id=event.project_id,
            payload={**payload, "_redispatch_of": str(event.id)},
        )
        return {
            "status": outcome.status,
            "event_id": str(outcome.event_id),
            "channels_succeeded": outcome.channels_succeeded,
            "channels_failed": outcome.channels_failed,
            "redispatch_of": event_id,
        }

    logger.warning(
        "notifications.dispatch_event · event %s missing template/context · "
        "marking failed without retry",
        event_id,
    )
    event.status = "failed"
    event.error = (
        event.error or
        "Cannot redispatch · payload._render_context missing"
    )
    event.retry_count += 1
    return {
        "status": "failed_no_context",
        "event_id": event_id,
        "retry_count": event.retry_count,
    }


async def scan_client_inactivity_async() -> dict:
    """Async wrapper Celery · usa session propia de ``async_session``.

    Para tests usar ``scan_client_inactivity_with_session(db)`` que
    permite inyección del session transaccional del fixture.
    """
    async with async_session() as db:
        await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
        try:
            stats = await scan_client_inactivity_with_session(db)
            await db.commit()
            return stats
        except Exception:
            await db.rollback()
            raise


async def scan_client_inactivity_with_session(db) -> dict:
    """Núcleo scan · acepta session existente (test override).

    Sentencia SQL aware de RLS: el caller debe haber escalado a rol
    superuser ``fulkro`` si necesita scan cross-tenant (Marcos owner).
    NO commit aquí · caller decide.
    """
    settings = get_settings()
    threshold_days = settings.client_inactivity_threshold_days
    cutoff = datetime.now(timezone.utc) - timedelta(days=threshold_days)
    deep_links = DeepLinkGenerator()

    stats: dict = {
        "threshold_days": threshold_days,
        "cutoff_utc": cutoff.isoformat(),
        "total_scanned": 0,
        "inactive_count": 0,
        "alerts_created": 0,
        "notifications_enqueued": 0,
        "errors": [],
    }

    count_result = await db.execute(
        text("SELECT COUNT(*) FROM client_users WHERE deleted_at IS NULL")
    )
    stats["total_scanned"] = int(count_result.scalar_one() or 0)

    inactive_users = (await db.execute(
        select(ClientUser).where(
            ClientUser.deleted_at.is_(None),
            (
                (ClientUser.last_login.is_(None))
                | (ClientUser.last_login < cutoff)
            ),
        )
    )).scalars().all()

    stats["inactive_count"] = len(inactive_users)

    project_lookup = await _resolve_first_project_per_client(
        db, [u.client_id for u in inactive_users]
    )
    client_name_lookup = await _resolve_client_names(
        db, [u.client_id for u in inactive_users]
    )

    for user in inactive_users:
        project_id = project_lookup.get(user.client_id)
        client_name = client_name_lookup.get(
            user.client_id, "Cliente desconocido"
        )

        if user.last_login is None:
            days_inactive = threshold_days
            last_login_str = "Nunca accedió"
        else:
            delta = datetime.now(timezone.utc) - user.last_login
            days_inactive = delta.days
            last_login_str = user.last_login.strftime("%Y-%m-%d")

        if project_id is not None:
            try:
                await db.execute(
                    text(
                        "SELECT set_config('app.current_project_id', "
                        ":pid, true)"
                    ),
                    {"pid": str(project_id)},
                )
                alerts = AlertService(db)
                await alerts.trigger_alert(
                    project_id=project_id,
                    severity="warning",
                    category="client_inactivity",
                    title=(
                        f"Cliente inactivo {days_inactive} días · "
                        f"{client_name}"
                    ),
                    description=(
                        f"{user.email} sin acceso al portal. "
                        f"Último login: {last_login_str}"
                    ),
                    action_url=deep_links.client_user_admin(
                        user.client_id, user.id,
                    ),
                    triggered_by="notifications.scan_client_inactivity",
                    metadata={
                        "client_user_id": str(user.id),
                        "days_inactive": days_inactive,
                        "last_login": last_login_str,
                    },
                )
                stats["alerts_created"] += 1
            except Exception as exc:  # pragma: no cover
                logger.exception(
                    "scan_client_inactivity · alert_create failed user=%s",
                    user.id,
                )
                stats["errors"].append(f"alert:{user.id}:{exc}")

        try:
            orch = NotificationOrchestrator(db)
            cta_url = deep_links.client_user_admin(
                user.client_id, user.id,
            )
            await orch.enqueue_with_template(
                event_type="client_inactivity_admin",
                template_name="client_inactivity_admin",
                template_context={
                    "client_name": client_name,
                    "days_inactive": days_inactive,
                    "last_login_date": last_login_str,
                    "last_task_completed": "",
                    "cta_url": cta_url,
                },
                recipient_email=settings.marcos_admin_email,
                recipient_user_id=None,
                project_id=project_id,
                payload={
                    "client_user_id": str(user.id),
                    "client_id": str(user.client_id),
                    "days_inactive": days_inactive,
                    "_render_context": {
                        "client_name": client_name,
                        "days_inactive": days_inactive,
                        "last_login_date": last_login_str,
                        "last_task_completed": "",
                        "cta_url": cta_url,
                    },
                },
            )
            stats["notifications_enqueued"] += 1
        except Exception as exc:  # pragma: no cover
            logger.exception(
                "scan_client_inactivity · enqueue failed user=%s",
                user.id,
            )
            stats["errors"].append(f"notify:{user.id}:{exc}")

    logger.info(
        "scan_client_inactivity completed · inactive=%d alerts=%d notifs=%d",
        stats["inactive_count"],
        stats["alerts_created"],
        stats["notifications_enqueued"],
    )
    return stats


async def _resolve_first_project_per_client(
    db, client_ids: list[uuid.UUID],
) -> dict[uuid.UUID, uuid.UUID]:
    """Resuelve un project_id representativo por client_id (1er proyecto).

    Necesario para AlertService que requiere project_id para RLS scope.
    Si cliente no tiene proyectos → cliente excluido del alert (notification
    admin sigue · email a Marcos no requiere project context).
    """
    if not client_ids:
        return {}
    rows = (await db.execute(
        text(
            "SELECT DISTINCT ON (client_id) client_id, id "
            "FROM projects WHERE client_id = ANY(:cids) "
            "AND (deleted_at IS NULL OR deleted_at > NOW()) "
            "ORDER BY client_id, created_at ASC"
        ),
        {"cids": [str(c) for c in client_ids]},
    )).all()
    return {row[0]: row[1] for row in rows}


async def _resolve_client_names(
    db, client_ids: list[uuid.UUID],
) -> dict[uuid.UUID, str]:
    if not client_ids:
        return {}
    rows = (await db.execute(
        text(
            "SELECT id, nombre FROM clients WHERE id = ANY(:cids)"
        ),
        {"cids": [str(c) for c in client_ids]},
    )).all()
    return {row[0]: row[1] for row in rows}


__all__ = [
    "dispatch_event",
    "scan_client_inactivity",
    "scan_client_inactivity_async",
    "scan_client_inactivity_with_session",
    "redispatch_event_with_session",
]
