"""Motor 29 — Celery tasks programadas.

Plan v4.2 6.15 + 6.16:

  - ``cleanup_expired_attachments`` — semanal (Sunday 04:00 ES). Scan
    attachments con ``uploaded_at + signed_url_ttl_seconds < now()`` y
    elimina object MinIO + soft-delete row (idempotente).

  - ``digest_unread_admin`` — diario (08:00 ES). Si Marcos tiene
    ``unread_for_admin > 0``, envía email digest con resumen mensajes
    nuevos vía EmailSender consolidado.

Nota: tasks usan SQLAlchemy sync session (no AsyncSession) porque Celery
worker corre fuera del event loop FastAPI. Pattern coherente con m26
(backup) y m23 (retainer) tasks.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from loguru import logger as loguru_logger

from backend.app.core.celery_app import celery_app


# Evitar logger naming clash entre logging stdlib y loguru
logger = logging.getLogger(__name__)


@celery_app.task(name="m29.cleanup_expired_attachments")
def cleanup_expired_attachments() -> dict[str, Any]:
    """Cleanup attachments con ``uploaded_at + signed_url_ttl_seconds < now()``.

    Scheduled: weekly Sunday 04:00 ES (plan 6.15).

    Lógica:
      1. Query attachments WHERE uploaded_at + signed_url_ttl_seconds * INTERVAL '1 second' < now()
         AND deleted_at IS NULL
      2. Para cada attachment: remove_object MinIO + setea deleted_at
      3. Retorna counts {checked, deleted, errors}.
    """
    return asyncio.run(_cleanup_expired_attachments_async())


async def _cleanup_expired_attachments_async() -> dict[str, Any]:
    from sqlalchemy import select, text
    from backend.app.core.storage.minio_client import remove_object
    from backend.app.database import async_session
    from backend.app.motors.m29_client_messaging.models import (
        ClientMessageAttachment,
    )

    checked = 0
    deleted = 0
    errors = 0

    async with async_session() as db:
        # Bypass RLS — admin task
        await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))

        # Query expired attachments
        stmt = select(ClientMessageAttachment).where(
            ClientMessageAttachment.uploaded_at.isnot(None),
            ClientMessageAttachment.deleted_at.is_(None),
            text(
                "uploaded_at + (signed_url_ttl_seconds * INTERVAL '1 second')"
                " < now()"
            ),
        )
        result = await db.execute(stmt)
        expired = list(result.scalars())

        for att in expired:
            checked += 1
            try:
                # Remove object MinIO (idempotente — no falla si ya borrado)
                remove_object(att.minio_bucket, att.minio_object_key)
                att.deleted_at = datetime.now(timezone.utc)
                deleted += 1
            except Exception as exc:  # noqa: BLE001
                errors += 1
                logger.warning(
                    "m29 cleanup attachment %s falló: %s",
                    att.id, exc,
                )

        await db.commit()

    loguru_logger.info(
        "m29 cleanup_expired_attachments: checked=%d deleted=%d errors=%d",
        checked, deleted, errors,
    )
    return {
        "task": "m29.cleanup_expired_attachments",
        "checked": checked,
        "deleted": deleted,
        "errors": errors,
    }


@celery_app.task(name="m29.digest_unread_admin")
def digest_unread_admin() -> dict[str, Any]:
    """Envía digest diario a Marcos si tiene mensajes no leídos.

    Scheduled: daily 08:00 ES (plan 6.16).

    Lógica:
      1. Count messages WHERE from_role='client' AND is_read_by_admin=FALSE
         AND deleted_at IS NULL
      2. Si > 0: leer admin_settings.notifications.digest_enabled
         (default True) + admin_settings.notifications.client_messages_forward_to
         como destinatario digest
      3. Send EmailSender con resumen (count + threads únicos +
         último mensaje excerpt)
      4. Retorna counts {unread, threads, sent}.
    """
    return asyncio.run(_digest_unread_admin_async())


async def _digest_unread_admin_async() -> dict[str, Any]:
    from sqlalchemy import func, select, text
    from backend.app.admin_settings import service as admin_settings_service
    from backend.app.core.email.sender import get_email_sender
    from backend.app.database import async_session
    from backend.app.motors.m29_client_messaging.models import ClientMessage

    async with async_session() as db:
        await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))

        # Count unread for admin
        unread_stmt = select(func.count(ClientMessage.id)).where(
            ClientMessage.from_role == "client",
            ClientMessage.is_read_by_admin.is_(False),
            ClientMessage.deleted_at.is_(None),
        )
        unread = (await db.execute(unread_stmt)).scalar_one() or 0

        if unread == 0:
            loguru_logger.info("m29 digest_unread_admin: 0 unread, skipped")
            return {
                "task": "m29.digest_unread_admin",
                "unread": 0, "threads": 0, "sent": False,
            }

        # Threads únicos
        threads_stmt = select(
            func.count(func.distinct(ClientMessage.thread_id))
        ).where(
            ClientMessage.from_role == "client",
            ClientMessage.is_read_by_admin.is_(False),
            ClientMessage.deleted_at.is_(None),
        )
        threads = (await db.execute(threads_stmt)).scalar_one() or 0

        # Read settings + decidir destinatario
        try:
            settings = await admin_settings_service.get_settings(db)
        except Exception:  # noqa: BLE001
            loguru_logger.warning(
                "m29 digest: admin_settings missing, skipped",
            )
            return {
                "task": "m29.digest_unread_admin",
                "unread": unread, "threads": threads, "sent": False,
            }

        notifications = settings.notifications or {}
        if not notifications.get("digest_enabled", True):
            loguru_logger.info("m29 digest_enabled=False, skipped")
            return {
                "task": "m29.digest_unread_admin",
                "unread": unread, "threads": threads, "sent": False,
            }

        target = notifications.get("client_messages_forward_to")
        if not target:
            loguru_logger.warning(
                "m29 digest: client_messages_forward_to no configurado",
            )
            return {
                "task": "m29.digest_unread_admin",
                "unread": unread, "threads": threads, "sent": False,
            }

        # Build email body
        html_body = _render_digest_html(unread, threads)
        text_body = (
            f"Tienes {unread} mensaje{'s' if unread != 1 else ''} nuevo"
            f"{'s' if unread != 1 else ''} sin leer en FULKRO "
            f"(en {threads} hilo{'s' if threads != 1 else ''}).\n\n"
            f"Accede al panel admin para responder."
        )

        sender = get_email_sender()
        result = await sender.send(
            db,
            to=str(target),
            subject=f"[FULKRO] Resumen diario — {unread} mensajes pendientes",
            html_body=html_body,
            text_body=text_body,
            template_used="m29_digest_admin",
            metadata={
                "motor": "m29",
                "task": "digest_unread_admin",
                "unread": unread,
                "threads": threads,
            },
        )
        await db.commit()

        loguru_logger.info(
            "m29 digest sent ok=%s message_id=%s unread=%d threads=%d",
            result.ok, result.message_id, unread, threads,
        )

        return {
            "task": "m29.digest_unread_admin",
            "unread": unread,
            "threads": threads,
            "sent": result.ok,
            "message_id": result.message_id,
        }


def _render_digest_html(unread: int, threads: int) -> str:
    """Render digest HTML (minimal coherente con email_forward)."""
    plural_msg = "mensajes" if unread != 1 else "mensaje"
    plural_thread = "hilos" if threads != 1 else "hilo"
    return f"""<!DOCTYPE html>
<html lang="es"><body style="font-family: -apple-system, sans-serif; line-height: 1.6; color: #1a1a1a;">
  <h2 style="color: #2563eb;">Resumen diario FULKRO</h2>
  <p>Tienes <strong>{unread} {plural_msg} sin leer</strong> en
     <strong>{threads} {plural_thread}</strong>.</p>
  <p>Accede al <a href="https://fulkro.es/admin/messages"
     style="color: #2563eb;">panel admin</a> para responder.</p>
  <hr style="border: 1px solid #e5e7eb;">
  <p style="color: #6b7280; font-size: 12px;">
    Digest automático FULKRO — Motor 29 Client Messaging.
    Configurable en Admin → Settings → Notifications.
  </p>
</body></html>"""
