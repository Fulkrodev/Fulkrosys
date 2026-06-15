"""Workflow step notifications · auto-trigger on unblock/completion (1.D.G.F v3.11).

Cuando step transitions:
- step actor=cliente becomes available (unblock) → notify cliente
  - ClientNotification in-app inbox row
  - Email via NotificationOrchestrator
  - WhatsApp opt-in si WHATSAPP_NOTIFICATIONS_ENABLED feature flag enabled

- step actor=admin becomes available (unblock) → notify admin
  - In-app dropdown header (TBD admin notifications · pre-existing TODO)
  - Email opcional per preference admin

Feature flag WHATSAPP_NOTIFICATIONS_ENABLED:
- Default: enabled true (piloto)
- Env var: WHATSAPP_NOTIFICATIONS_ENABLED=false para off rápido
"""
from __future__ import annotations

import logging
import os
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.client_notification import ClientNotification
from backend.app.models.client_portal import ClientUser
from backend.app.models.core import Project
from backend.app.motors.m21_portal_cliente.task_templates_loader import (
    TaskTemplate,
)


logger = logging.getLogger(__name__)


def whatsapp_notifications_enabled() -> bool:
    """Feature flag · default true · env var WHATSAPP_NOTIFICATIONS_ENABLED."""
    raw = os.environ.get("WHATSAPP_NOTIFICATIONS_ENABLED", "true")
    return raw.strip().lower() not in {"0", "false", "no", "off"}


@dataclass(frozen=True)
class NotificationDispatchResult:
    channels: list[str]
    message: str
    skipped_reasons: list[str]


def _format_cliente_message(
    template: TaskTemplate,
    consultor_name: str = "Tu consultor",
) -> str:
    """Build R29 friendly text · per template.notification_template_cliente o default."""
    if template.notification_template_cliente:
        return template.notification_template_cliente.format(
            step_title=template.title,
            consultor_name=consultor_name,
        )
    return f"{consultor_name} preparó {template.title} · es tu turno"


def _format_admin_message(
    template: TaskTemplate,
    cliente_name: str = "El cliente",
) -> str:
    if template.notification_template_admin:
        return template.notification_template_admin.format(
            step_title=template.title,
            cliente_name=cliente_name,
        )
    return f"{cliente_name} completó {template.title} · puedes proceder"


async def _resolve_client_users_for_project(
    db: AsyncSession, project_id: uuid.UUID,
) -> list[ClientUser]:
    """Lista ClientUsers del proyecto · usados para notificar cliente."""
    project = await db.get(Project, project_id)
    if project is None:
        return []
    result = await db.execute(
        select(ClientUser).where(
            ClientUser.client_id == project.client_id,
        )
    )
    return list(result.scalars().all())


async def send_client_unblock_notification(
    db: AsyncSession,
    project_id: uuid.UUID,
    template: TaskTemplate,
) -> NotificationDispatchResult:
    """Fire notifications cuando step actor=cliente becomes available.

    - In-app ClientNotification row per ClientUser project
    - Email via NotificationOrchestrator si email_sender disponible
    - WhatsApp opcional si flag enabled
    """
    channels: list[str] = []
    skipped: list[str] = []

    client_users = await _resolve_client_users_for_project(db, project_id)
    if not client_users:
        skipped.append("no_client_users_for_project")
        return NotificationDispatchResult(
            channels=channels,
            message="No hay client users registrados para el proyecto",
            skipped_reasons=skipped,
        )

    title = "Tu consultor terminó · es tu turno"
    body = _format_cliente_message(template)
    target_url = template.cta_url or "/client-portal/workflow"

    # In-app notification per user
    for user in client_users:
        notif = ClientNotification(
            project_id=project_id,
            client_user_id=user.id,
            type="workflow_step_unblocked",
            title=title,
            body=body,
            target_url=target_url,
            priority="normal",
            emitted_by_motor="m_workflow_engine",
            payload_json={"template_id": template.id},
        )
        db.add(notif)
    channels.append("in_app")

    await db.flush()

    # Email via NotificationOrchestrator
    try:
        from backend.app.notifications.orchestrator import NotificationOrchestrator
        orchestrator = NotificationOrchestrator(db)
        html_body = (
            f"<p>{body}</p>"
            f"<p><a href='{target_url}'>Acceder</a></p>"
        )
        for user in client_users:
            try:
                await orchestrator.enqueue(
                    event_type="workflow_step_unblocked",
                    recipient_email=user.email,
                    recipient_user_id=user.id,
                    subject=title,
                    html_body=html_body,
                    text_body=body,
                    project_id=project_id,
                    template_used="workflow_step_unblocked",
                    payload={"template_id": template.id},
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "workflow_unblock · email enqueue failed user=%s err=%s",
                    user.id, exc,
                )
                skipped.append(f"email_failed:{user.id}")
        if "email_failed" not in " ".join(skipped):
            channels.append("email")
    except ImportError:
        skipped.append("email_orchestrator_unavailable")

    # WhatsApp opcional (feature flag)
    if whatsapp_notifications_enabled():
        try:
            from backend.app.notifications.whatsapp_dispatcher import (  # type: ignore
                dispatch_critical_event,
            )
            for user in client_users:
                try:
                    await dispatch_critical_event(
                        db=db,
                        client_user_id=user.id,
                        project_id=project_id,
                        event_type="workflow_step_unblocked",
                        payload={"body": body, "target_url": target_url},
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "workflow_unblock · whatsapp failed user=%s err=%s",
                        user.id, exc,
                    )
                    skipped.append(f"whatsapp_failed:{user.id}")
            if not any(s.startswith("whatsapp_failed") for s in skipped):
                channels.append("whatsapp")
        except (ImportError, TypeError):
            skipped.append("whatsapp_dispatcher_unavailable")
    else:
        skipped.append("whatsapp_flag_disabled")

    return NotificationDispatchResult(
        channels=channels,
        message=f"Notification dispatched via {', '.join(channels)}",
        skipped_reasons=skipped,
    )


async def send_admin_step_completed_notification(
    db: AsyncSession,
    project_id: uuid.UUID,
    template: TaskTemplate,
) -> NotificationDispatchResult:
    """Fire notifications cuando step actor=admin becomes available (cliente completó).

    NO admin_notifications table existing yet (audit-first 1.D.G.F).
    Solo emite payload logging para futura admin inbox · graceful no-op.
    """
    channels: list[str] = []
    skipped: list[str] = []

    message = _format_admin_message(template)
    logger.info(
        "workflow_step_unblocked admin · project=%s template=%s message=%s",
        project_id, template.id, message,
    )
    channels.append("log_only_admin_inbox_not_yet_implemented")
    skipped.append("admin_notifications_pending_T1_polish")

    return NotificationDispatchResult(
        channels=channels,
        message=message,
        skipped_reasons=skipped,
    )


async def send_client_remind_notification(
    db: AsyncSession,
    project_id: uuid.UUID,
    template: TaskTemplate,
) -> NotificationDispatchResult:
    """Marcos manual remind · idempotente · reusa send_client_unblock_notification.

    Endpoint /admin/.../steps/{id}/remind invoca este handler.
    NO duplica si already sent < 24h (TBD enforcement T1 dedup).
    """
    return await send_client_unblock_notification(
        db=db, project_id=project_id, template=template,
    )
