"""Motor 29 — Email forward out-of-band.

Reenvía mensaje cliente al email configurado en admin_settings.notifications
(o email del contact M30 si presente), usando EmailSender consolidado.

Flujo (plan v4.2 6.12):
  1. Si ``message.from_role == 'client'``: forward al admin (Marcos).
     - Si ``message.to_contact_id`` presente: forward a ``contact.email``
       (override del default admin_settings).
     - Si ausente: forward a ``admin_settings.notifications.client_messages_forward_to``.
  2. Si ``message.from_role == 'admin'``: forward al cliente (notification
     de respuesta admin).
     - Si ``message.to_contact_id`` presente: forward a ``contact.email``.
     - Si ausente: NO forward (cliente lo verá vía portal polling).

Estado persistido en columnas:
  - ``forwarded_to_email`` — destinatario real
  - ``forwarded_at`` — timestamp del envío exitoso
  - ``email_forward_status`` — pending/sent/failed/skipped

Coherente con email_log via EmailSender (cada envío genera entry).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.admin_settings import service as admin_settings_service
from backend.app.core.email.sender import get_email_sender
from backend.app.motors.m29_client_messaging.models import ClientMessage
from backend.app.motors.m30_client_contacts.models import ClientContact


logger = logging.getLogger(__name__)


_SUBJECT_TEMPLATES = {
    "client": "[FULKRO] Nuevo mensaje cliente",
    "admin": "[FULKRO] Respuesta de Marcos",
}


async def forward_message(
    db: AsyncSession,
    message: ClientMessage,
) -> str:
    """Reenvía el mensaje al destinatario apropiado.

    Returns: estado final ``email_forward_status`` (sent/failed/skipped).

    Side effects: actualiza columnas ``forwarded_*`` en ``message`` row.
    """
    target_email = await _resolve_target_email(db, message)
    if target_email is None:
        message.email_forward_status = "skipped"
        await db.flush()
        return "skipped"

    subject = _SUBJECT_TEMPLATES.get(
        message.from_role, "[FULKRO] Nuevo mensaje",
    )

    html_body = _render_email_html(message)
    text_body = message.body_markdown

    sender = get_email_sender()
    message.email_forward_status = "pending"
    message.forwarded_to_email = target_email

    try:
        result = await sender.send(
            db,
            to=target_email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            template_used="m29_message_forward",
            client_id=message.client_id,
            metadata={
                "motor": "m29",
                "message_id": str(message.id),
                "thread_id": str(message.thread_id),
                "from_role": message.from_role,
            },
        )
    except Exception:
        # Defensa: cualquier excepción no esperada → marcar failed sin
        # abortar el flow del send (mensaje persiste en BD).
        logger.exception("EmailSender raise inesperado en m29 forward")
        message.email_forward_status = "failed"
        await db.flush()
        return "failed"

    if result.ok:
        message.email_forward_status = "sent"
        message.forwarded_at = datetime.now(timezone.utc)
    else:
        message.email_forward_status = "failed"
        logger.warning(
            "m29 forward failed message_id=%s error=%s",
            message.id, result.error,
        )

    await db.flush()
    return message.email_forward_status


async def _resolve_target_email(
    db: AsyncSession,
    message: ClientMessage,
) -> str | None:
    """Resuelve email destinatario según from_role + to_contact_id + settings."""
    # 1. Si to_contact_id presente, prefer contact.email
    if message.to_contact_id is not None:
        contact = await db.get(ClientContact, message.to_contact_id)
        if contact is not None and contact.email and not contact.deleted_at:
            return str(contact.email)

    # 2. Fallback admin_settings.notifications
    if message.from_role == "client":
        return await _read_admin_forward_email(db)

    # 3. Admin → cliente sin to_contact_id: NO forward (skipped)
    return None


async def _read_admin_forward_email(db: AsyncSession) -> str | None:
    """Lee admin_settings.notifications.client_messages_forward_to."""
    try:
        settings = await admin_settings_service.get_settings(db)
    except Exception:  # noqa: BLE001
        # singleton missing — defensa profunda, no rompe send.
        return None
    notifications = settings.notifications or {}
    if not notifications.get("client_messages_forward_enabled", True):
        return None
    forward_to = notifications.get("client_messages_forward_to")
    if not forward_to:
        return None
    return str(forward_to)


def _render_email_html(message: ClientMessage) -> str:
    """Render minimal HTML (defensa profunda; render real client-side).

    Plan v4.2 6.13 menciona template HTML branding FULKRO. Por ahora
    minimal coherente con _render_safe_html del service. Plantilla
    completa con branding queda diferida a sub-fase frontend (6.B) o
    template Jinja2 separado.
    """
    body_html = message.body_html or ""
    if not body_html:
        # Fallback en caso de race: render directo del markdown
        import html as html_lib
        body_html = html_lib.escape(message.body_markdown).replace(
            "\n", "<br>",
        )
    sender_label = (
        "Cliente" if message.from_role == "client" else "Marcos (FULKRO)"
    )
    return f"""<!DOCTYPE html>
<html lang="es"><body style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; line-height: 1.6; color: #1a1a1a;">
  <h2 style="color: #2563eb;">Nuevo mensaje en FULKRO</h2>
  <p><strong>De:</strong> {sender_label}</p>
  <p><strong>Hora:</strong> {message.created_at.isoformat() if message.created_at else ""}</p>
  <hr style="border: 1px solid #e5e7eb;">
  <div style="background: #f9fafb; padding: 16px; border-radius: 8px;">
    {body_html}
  </div>
  <hr style="border: 1px solid #e5e7eb;">
  <p style="color: #6b7280; font-size: 12px;">
    Mensaje automático FULKRO — Motor 29 Client Messaging.
  </p>
</body></html>"""
