"""NotificationOrchestrator core service (ADR-039 MB-16.2).

API principal:

    orchestrator = NotificationOrchestrator(db)
    event = await orchestrator.enqueue(
        event_type="task_assigned",
        recipient_user_id=client_user.id,
        recipient_email=client_user.email,
        subject="Nueva tarea asignada",
        html_body="<p>...</p>",
        text_body="...",
        project_id=project.id,
        template_used="task_assigned",
        payload={"task_id": str(task.id)},
    )

Flujo enqueue:
1. Resolve preferences (factory default si no existe row).
2. Check DND timezone-aware → si activo, status=suppressed_dnd
   sin dispatch (cliente decidió ventana silencio).
3. Persist NotificationEvent row (status=queued).
4. Dispatch sync (mode=sync MVP atom 16.2 · async Celery atom 16.4):
   - Email canal si ``email_enabled`` y ``email`` válido
   - Portal SSE canal si ``portal_sse_enabled`` y ``recipient_user_id``
     conocido
5. Update event row con channels_succeeded/failed + timestamps +
   status final (delivered | failed).

Error handling:
- EmailSender retry built-in (2s · 8s · 32s exponencial existing).
- SSE dispatch best-effort (queue full → drop · cliente reconecta
  via polling baseline).
- Orchestrator-level retry vive en Celery worker (atom 16.4)
  para failures transient infraestructura.

Política conservadora: si DND tz inválida O preferences corruptas
→ envío permitido (mejor mensaje extra que mensaje perdido).
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.email import EmailSender, get_email_sender
from backend.app.core.sse_dispatcher import sse_dispatcher
from backend.app.models.notifications import (
    NotificationEvent,
    NotificationPreference,
)
from backend.app.notifications.dnd import is_dnd_active
from backend.app.notifications.templates_resolver import (
    RenderedTemplate,
    TemplateResolver,
)

logger = logging.getLogger(__name__)


CHANNEL_EMAIL = "email"
CHANNEL_PORTAL_SSE = "portal_sse"
# SAN-E MB-8 atom 8.2 · WhatsApp channel · dispatch via whatsapp_dispatcher
# (decoupled from orchestrator core · motors call directly for critical events).
CHANNEL_WHATSAPP = "whatsapp"

DEFAULT_TIMEZONE = "Europe/Madrid"


class OrchestratorError(Exception):
    """Error genérico orchestrator."""


@dataclass
class DispatchOutcome:
    """Resumen del intento de despacho · expuesto a callers + tests."""

    event_id: uuid.UUID
    status: str
    channels_succeeded: list[str] = field(default_factory=list)
    channels_failed: list[str] = field(default_factory=list)
    suppressed_by_dnd: bool = False
    error: str | None = None


class NotificationOrchestrator:
    """Despacha notificaciones cross-canal con preferences + DND + audit."""

    def __init__(
        self,
        db: AsyncSession,
        *,
        email_sender: EmailSender | None = None,
        template_resolver: TemplateResolver | None = None,
    ):
        self.db = db
        self._email_sender = email_sender
        self._template_resolver = template_resolver

    @property
    def email_sender(self) -> EmailSender:
        if self._email_sender is None:
            self._email_sender = get_email_sender()
        return self._email_sender

    @property
    def template_resolver(self) -> TemplateResolver:
        if self._template_resolver is None:
            self._template_resolver = TemplateResolver()
        return self._template_resolver

    async def enqueue_with_template(
        self,
        *,
        event_type: str,
        template_name: str,
        template_context: dict,
        recipient_email: str,
        recipient_user_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
        payload: dict | None = None,
        sse_channel: str | None = None,
        sse_data: dict | None = None,
        now_utc: datetime | None = None,
    ) -> DispatchOutcome:
        """Resolve template YAML + render Jinja2 → enqueue + dispatch.

        Wrapper alrededor de ``enqueue()`` que delega rendering al
        ``TemplateResolver``. WhatsApp footer auto-append en pies HTML
        + text via ``WhatsAppInfoFormatter`` integrado en resolver.

        Args:
            template_name: basename YAML en
                ``backend/app/notifications/templates/`` (sin ext).
            template_context: dict variables Jinja2 (recipient_name,
                project_name, cta_url, etc).
            otros: ver ``enqueue()``.
        """
        rendered: RenderedTemplate = self.template_resolver.render(
            template_name, template_context,
        )
        return await self.enqueue(
            event_type=event_type,
            recipient_email=recipient_email,
            subject=rendered.subject,
            html_body=rendered.html_body,
            text_body=rendered.text_body,
            recipient_user_id=recipient_user_id,
            project_id=project_id,
            template_used=template_name,
            payload=payload,
            sse_channel=sse_channel,
            sse_data=sse_data,
            now_utc=now_utc,
        )

    async def enqueue(
        self,
        *,
        event_type: str,
        recipient_email: str,
        subject: str,
        html_body: str,
        text_body: str | None = None,
        recipient_user_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
        template_used: str | None = None,
        payload: dict | None = None,
        sse_channel: str | None = None,
        sse_data: dict | None = None,
        now_utc: datetime | None = None,
    ) -> DispatchOutcome:
        """Encola + dispatch sync evento notificación.

        Args:
            event_type: ej. ``task_assigned``, ``chat_admin_reply``.
            recipient_email: email destino · snapshot persistido.
            subject: asunto email.
            html_body: cuerpo HTML email.
            text_body: cuerpo texto plano. Si ``None``, EmailSender lo
                deriva de html_body.
            recipient_user_id: ClientUser.id si aplica · None para
                admin events (ej. client_inactivity_admin → marcos).
            project_id: scope proyecto · None para events admin
                cross-project.
            template_used: basename template YAML usado.
            payload: dict snapshot del contexto (task_id · thread_id ·
                etc) para diagnostic admin.
            sse_channel: canal SSE custom · default
                ``client_user:{recipient_user_id}`` si user conocido.
            sse_data: data SSE custom · default ``{event_type, payload}``.
            now_utc: para tests · default datetime.now(UTC).

        Returns:
            DispatchOutcome con status final + channels detail.
        """
        preferences = await self._resolve_preferences(recipient_user_id)

        outcome_payload = payload or {}
        suppressed = self._should_suppress_dnd(preferences, now_utc)

        event = NotificationEvent(
            event_type=event_type,
            recipient_user_id=recipient_user_id,
            recipient_email=recipient_email,
            project_id=project_id,
            template_used=template_used,
            payload_jsonb=outcome_payload,
            status="suppressed_dnd" if suppressed else "queued",
        )
        self.db.add(event)
        await self.db.flush()
        await self.db.refresh(event)

        if suppressed:
            logger.info(
                "Notification %s event_type=%s recipient=%s SUPPRESSED by DND",
                event.id, event_type, recipient_email,
            )
            return DispatchOutcome(
                event_id=event.id,
                status="suppressed_dnd",
                suppressed_by_dnd=True,
            )

        outcome = await self._dispatch_sync(
            event=event,
            preferences=preferences,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            sse_channel=sse_channel,
            sse_data=sse_data or {"event_type": event_type, "payload": outcome_payload},
        )
        return outcome

    async def _resolve_preferences(
        self, recipient_user_id: uuid.UUID | None,
    ) -> NotificationPreference | None:
        """Lookup preferences por user_id · None si admin event."""
        if recipient_user_id is None:
            return None
        result = await self.db.execute(
            select(NotificationPreference).where(
                NotificationPreference.client_user_id == recipient_user_id
            )
        )
        return result.scalar_one_or_none()

    def _should_suppress_dnd(
        self,
        preferences: NotificationPreference | None,
        now_utc: datetime | None,
    ) -> bool:
        if preferences is None:
            return False
        return is_dnd_active(
            dnd_start_local=preferences.dnd_start_local,
            dnd_end_local=preferences.dnd_end_local,
            tz_name=preferences.timezone or DEFAULT_TIMEZONE,
            now_utc=now_utc,
        )

    async def _dispatch_sync(
        self,
        *,
        event: NotificationEvent,
        preferences: NotificationPreference | None,
        subject: str,
        html_body: str,
        text_body: str | None,
        sse_channel: str | None,
        sse_data: dict,
    ) -> DispatchOutcome:
        """Dispatch immediate · single transaction commit."""
        attempted: list[str] = []
        succeeded: list[str] = []
        failed: list[str] = []
        first_error: str | None = None
        email_log_id: uuid.UUID | None = None

        event.status = "dispatching"
        event.dispatched_at = datetime.now(timezone.utc)
        await self.db.flush()

        if self._email_enabled(preferences):
            attempted.append(CHANNEL_EMAIL)
            ok, err, log_id = await self._dispatch_email(
                event=event,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
            )
            if ok:
                succeeded.append(CHANNEL_EMAIL)
                email_log_id = log_id
            else:
                failed.append(CHANNEL_EMAIL)
                first_error = first_error or err

        if self._sse_enabled(preferences, event.recipient_user_id):
            attempted.append(CHANNEL_PORTAL_SSE)
            ok, err = await self._dispatch_portal_sse(
                event=event,
                channel=sse_channel,
                data=sse_data,
            )
            if ok:
                succeeded.append(CHANNEL_PORTAL_SSE)
            else:
                failed.append(CHANNEL_PORTAL_SSE)
                first_error = first_error or err

        event.channels_attempted = attempted
        event.channels_succeeded = succeeded
        event.channels_failed = failed
        if email_log_id is not None:
            event.email_log_id = email_log_id
        event.error = first_error
        if succeeded and not failed:
            event.status = "delivered"
            event.delivered_at = datetime.now(timezone.utc)
        elif succeeded and failed:
            event.status = "delivered"
            event.delivered_at = datetime.now(timezone.utc)
        else:
            event.status = "failed"
        await self.db.flush()

        return DispatchOutcome(
            event_id=event.id,
            status=event.status,
            channels_succeeded=succeeded,
            channels_failed=failed,
            error=first_error,
        )

    @staticmethod
    def _email_enabled(preferences: NotificationPreference | None) -> bool:
        if preferences is None:
            return True
        return bool(preferences.email_enabled)

    @staticmethod
    def _sse_enabled(
        preferences: NotificationPreference | None,
        recipient_user_id: uuid.UUID | None,
    ) -> bool:
        if recipient_user_id is None:
            return False
        if preferences is None:
            return True
        return bool(preferences.portal_sse_enabled)

    async def _dispatch_email(
        self,
        *,
        event: NotificationEvent,
        subject: str,
        html_body: str,
        text_body: str | None,
    ) -> tuple[bool, str | None, uuid.UUID | None]:
        try:
            result = await self.email_sender.send(
                self.db,
                to=event.recipient_email,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
                template_used=event.template_used,
                metadata={
                    "notification_event_id": str(event.id),
                    "event_type": event.event_type,
                },
            )
        except Exception as exc:  # pragma: no cover · safety net
            logger.exception(
                "Email dispatch raised event=%s recipient=%s",
                event.id, event.recipient_email,
            )
            return False, f"email_exception: {exc}", None

        if not result.ok:
            return False, result.error or "email_failed", result.email_log_id
        return True, None, result.email_log_id

    async def _dispatch_portal_sse(
        self,
        *,
        event: NotificationEvent,
        channel: str | None,
        data: dict,
    ) -> tuple[bool, str | None]:
        target_channel = channel or f"client_user:{event.recipient_user_id}"
        payload: dict[str, Any] = {
            "notification_event_id": str(event.id),
            "event_type": event.event_type,
            **data,
        }
        try:
            await sse_dispatcher.dispatch(
                target_channel,
                "notification",
                payload,
            )
        except Exception as exc:
            logger.exception(
                "SSE dispatch raised event=%s channel=%s",
                event.id, target_channel,
            )
            return False, f"sse_exception: {exc}"
        return True, None


__all__ = [
    "NotificationOrchestrator",
    "OrchestratorError",
    "DispatchOutcome",
    "CHANNEL_EMAIL",
    "CHANNEL_PORTAL_SSE",
    "DEFAULT_TIMEZONE",
]
