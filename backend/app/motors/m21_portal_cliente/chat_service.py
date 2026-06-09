"""ChatService · cliente↔admin chat con SSE push + SLA tracking
(ADR-038 SAN-D MB-14.5).

Pivot SSE+REST (DEC-MB14-CHAT-WEBSOCKET-PIVOT): mensajes persisten
via REST POST · clientes/admin reciben updates real-time via SSE
existing dispatcher MB-13.3.

SLA: tracking last_client_message_at + last_admin_response_at en
ChatThread permite Celery beat task verificar SLA <2h breach (task
real implementación deferrable atom 14.9 o MB-19+).
"""
from __future__ import annotations

import json as _json
import logging
import uuid as _uuid
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, text as _sa_text, update as _sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m21_portal_cliente.models_chat import (
    ChatMessage,
    ChatThread,
)

logger = logging.getLogger(__name__)


VALID_SENDER_TYPES = {"client", "admin", "system"}


async def _emit_chat_audit_log(
    db: AsyncSession,
    *,
    project_id: UUID,
    client_id: UUID | None,
    accion: str,
    registro_id: UUID,
    usuario: str,
    payload: dict,
) -> None:
    """Sub-atom 5.A · audit_log 3-way OR (project_id + client_id).

    Best-effort try/except · primary chat persistence NUNCA bloqueado por
    audit_log failure. CLUSTER 5 Phase 5A delta canonical emit helper.
    """
    try:
        await db.execute(
            _sa_text(
                "INSERT INTO audit_log "
                "(id, tabla, registro_id, accion, usuario, "
                "project_id, client_id, payload_new, timestamp) "
                "VALUES (gen_random_uuid(), 'chat_messages', "
                ":rid, :accion, :usuario, :pid, :cid, :payload, now())"
            ),
            {
                "rid": str(registro_id),
                "accion": accion,
                "usuario": usuario,
                "pid": str(project_id),
                "cid": str(client_id) if client_id else None,
                "payload": _json.dumps(payload),
            },
        )
        await db.flush()
    except Exception:  # pragma: no cover · best-effort
        logger.exception(
            "audit_log %s emit failed · project_id=%s",
            accion, project_id,
        )


class ChatError(Exception):
    pass


class ChatService:
    """Cliente↔admin chat persistido + SSE dispatch + SLA tracking."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_thread(
        self,
        project_id: UUID,
        client_user_id: Optional[UUID] = None,
        subject: Optional[str] = None,
    ) -> ChatThread:
        """Devuelve thread open del proyecto · crea si no existe."""
        # FIX P2-6: serializar el get-or-create por proyecto (advisory lock
        # transaccional · Pattern #22) para evitar 2 threads 'open' duplicados
        # bajo concurrencia (check-then-insert sin lock).
        await self.db.execute(
            _sa_text("SELECT pg_advisory_xact_lock(hashtext(:k))"),
            {"k": f"chat_thread_{project_id}"},
        )
        existing = (
            await self.db.execute(
                select(ChatThread)
                .where(ChatThread.project_id == project_id)
                .where(ChatThread.status == "open")
                .where(ChatThread.deleted_at.is_(None))
                .limit(1)
            )
        ).scalar_one_or_none()
        if existing:
            return existing

        thread = ChatThread(
            project_id=project_id,
            client_user_id=client_user_id,
            subject=subject,
            status="open",
            messages_count=0,
        )
        self.db.add(thread)
        await self.db.flush()
        await self.db.refresh(thread)
        return thread

    async def list_threads(
        self,
        project_id: UUID,
        status: Optional[str] = None,
    ) -> list[ChatThread]:
        query = (
            select(ChatThread)
            .where(ChatThread.project_id == project_id)
            .where(ChatThread.deleted_at.is_(None))
            .order_by(ChatThread.updated_at.desc().nullslast())
        )
        if status:
            query = query.where(ChatThread.status == status)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def list_messages(
        self,
        thread_id: UUID,
        limit: int = 200,
    ) -> list[ChatMessage]:
        result = await self.db.execute(
            select(ChatMessage)
            .where(ChatMessage.thread_id == thread_id)
            .where(ChatMessage.deleted_at.is_(None))
            .order_by(ChatMessage.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def post_message(
        self,
        thread_id: UUID,
        sender_type: str,
        content: str,
        sender_user_id: Optional[UUID] = None,
        metadata: Optional[dict] = None,
    ) -> ChatMessage:
        if sender_type not in VALID_SENDER_TYPES:
            raise ChatError(
                f"Invalid sender_type: {sender_type}. Allowed: {VALID_SENDER_TYPES}",
            )
        if not content or not content.strip():
            raise ChatError("Message content cannot be empty")

        thread = await self.db.get(ChatThread, thread_id)
        if not thread or thread.deleted_at:
            raise ChatError("Thread not found")

        message = ChatMessage(
            thread_id=thread_id,
            project_id=thread.project_id,
            sender_type=sender_type,
            sender_user_id=sender_user_id,
            content=content.strip(),
            metadata_jsonb=metadata or None,
        )
        self.db.add(message)

        now = datetime.now(timezone.utc)
        thread.messages_count = (thread.messages_count or 0) + 1
        if sender_type == "client":
            thread.last_client_message_at = now
        elif sender_type == "admin":
            thread.last_admin_response_at = now

        await self.db.flush()
        await self.db.refresh(message)

        # SSE push real-time (DEC-MB14-CHAT-WEBSOCKET-PIVOT ADR-038)
        try:
            from backend.app.core.sse_dispatcher import sse_dispatcher

            await sse_dispatcher.dispatch(
                channel=f"project:{thread.project_id}",
                event_type="chat_message_new",
                data={
                    "thread_id": str(thread_id),
                    "message_id": str(message.id),
                    "sender_type": sender_type,
                    "content_preview": content[:120],
                    "created_at": message.created_at.isoformat(),
                },
            )
        except Exception:
            # SSE dispatch no bloquea persistencia mensaje
            pass

        # CLUSTER 5 Phase 5A delta · audit_log Sub-atom 5.A 3-way OR
        # emit chat.message.sent · trazabilidad ENAC. client_id resolved
        # via thread.client_user_id → client_users.client_id when available
        # (system messages may have neither sender_user_id nor client_user_id).
        client_id_for_audit = await self._resolve_client_id_for_thread(thread)
        await _emit_chat_audit_log(
            self.db,
            project_id=thread.project_id,
            client_id=client_id_for_audit,
            accion="chat.message.sent",
            registro_id=message.id,
            usuario=(
                f"cliente:{sender_user_id}" if sender_type == "client"
                else f"admin:{sender_user_id}" if sender_type == "admin"
                else "system"
            ),
            payload={
                "thread_id": str(thread_id),
                "sender_type": sender_type,
                "content_length": len(content),
                "content_preview": content[:120],
            },
        )

        # MB-16.6 · NotificationOrchestrator integration: admin reply
        # → email + portal SSE per cliente preferences (ADR-039).
        # Política conservadora: fallos capturados · NUNCA bloquean
        # persistencia mensaje.
        if sender_type == "admin" and thread.client_user_id is not None:
            await self._notify_admin_reply(thread, message)

        # CLUSTER 5 Phase 5D delta · cliente inbound → Marcos WhatsApp
        # bridge. Best-effort · silently skipped if marcos_whatsapp_number
        # empty (degradación elegante) o whatsapp_provider=mock.
        if sender_type == "client":
            await self._dispatch_client_inbound_to_marcos(
                thread=thread, message=message,
            )

        return message

    async def _resolve_client_id_for_thread(
        self, thread: ChatThread,
    ) -> UUID | None:
        """Resolve client_id from thread.client_user_id for audit_log 3-way OR.

        Returns None if thread has no client_user_id (system-initiated or
        anonymous · audit_log accepts NULL client_id per Sub-atom 5.A pattern).
        """
        if thread.client_user_id is None:
            return None
        try:
            row = (await self.db.execute(
                _sa_text(
                    "SELECT client_id FROM client_users WHERE id = :uid"
                ),
                {"uid": str(thread.client_user_id)},
            )).first()
            return row[0] if row else None
        except Exception:
            logger.exception(
                "client_id resolution failed thread=%s", thread.id,
            )
            return None

    async def mark_messages_read(
        self,
        thread_id: UUID,
        reader_role: str,
        reader_user_id: UUID | None = None,
    ) -> int:
        """Bulk mark unread messages from counterparty as read.

        Cliente reading marks ``sender_type=admin`` messages as read.
        Admin reading marks ``sender_type=client`` messages as read.
        Returns count of messages marked. Idempotent · already-read messages
        unchanged. audit_log Sub-atom 5.A emit ``chat.message.read`` with
        affected message_ids batch.
        """
        if reader_role == "client":
            counterparty = "admin"
        elif reader_role == "admin":
            counterparty = "client"
        else:
            raise ChatError(
                f"Invalid reader_role: {reader_role}. Allowed: client, admin"
            )

        thread = await self.db.get(ChatThread, thread_id)
        if not thread or thread.deleted_at:
            raise ChatError("Thread not found")

        now = datetime.now(timezone.utc)

        # Capture affected ids antes del update (audit trail)
        unread_q = await self.db.execute(
            select(ChatMessage.id)
            .where(ChatMessage.thread_id == thread_id)
            .where(ChatMessage.sender_type == counterparty)
            .where(ChatMessage.read_at.is_(None))
            .where(ChatMessage.deleted_at.is_(None))
        )
        affected_ids = [row[0] for row in unread_q.all()]
        if not affected_ids:
            return 0

        await self.db.execute(
            _sa_update(ChatMessage)
            .where(ChatMessage.id.in_(affected_ids))
            .values(read_at=now)
        )
        await self.db.flush()

        client_id_for_audit = await self._resolve_client_id_for_thread(thread)
        await _emit_chat_audit_log(
            self.db,
            project_id=thread.project_id,
            client_id=client_id_for_audit,
            accion="chat.message.read",
            registro_id=thread_id,
            usuario=(
                f"cliente:{reader_user_id}" if reader_role == "client"
                else f"admin:{reader_user_id}"
            ),
            payload={
                "thread_id": str(thread_id),
                "reader_role": reader_role,
                "marked_count": len(affected_ids),
                "message_ids": [str(mid) for mid in affected_ids],
            },
        )

        return len(affected_ids)

    async def _notify_admin_reply(
        self, thread: ChatThread, message: ChatMessage,
    ) -> None:
        """Resuelve recipient + project_name + dispara notify_chat_admin_reply.

        CLUSTER 5 Phase 5D delta · ALSO dispatch_critical_event for WhatsApp
        delivery when cliente opt-in active (tier MEDIA/ALTA per
        whatsapp_critical_events_routing seed chat_admin_reply). Email +
        WhatsApp coexist · NotificationOrchestrator handles dedup if both
        fire same channel.
        """
        try:
            from backend.app.models.client_portal import ClientUser
            from backend.app.notifications.motor_adapters import (
                notify_chat_admin_reply,
            )

            recipient = await self.db.get(ClientUser, thread.client_user_id)
            if recipient is None or recipient.deleted_at:
                return

            project_row = (await self.db.execute(
                _sa_text(
                    "SELECT nombre FROM projects WHERE id = :pid"
                ),
                {"pid": str(thread.project_id)},
            )).first()
            project_name = project_row[0] if project_row else "tu proyecto"

            await notify_chat_admin_reply(
                self.db,
                recipient_user_id=recipient.id,
                recipient_email=recipient.email,
                recipient_name=recipient.full_name or recipient.email,
                project_id=thread.project_id,
                project_name=project_name,
                thread_id=thread.id,
                message_preview=message.content,
            )

            # CLUSTER 5 Phase 5D delta · ALSO WhatsApp dispatch via M31
            # if cliente opt-in. Best-effort try/except internal.
            await self._dispatch_admin_reply_whatsapp(
                thread=thread,
                message=message,
                recipient=recipient,
                project_name=project_name,
            )
        except Exception:
            logger.exception(
                "ChatService._notify_admin_reply failed thread=%s",
                thread.id,
            )

    async def _dispatch_admin_reply_whatsapp(
        self,
        *,
        thread: ChatThread,
        message: ChatMessage,
        recipient,
        project_name: str,
    ) -> None:
        """CLUSTER 5 Phase 5D delta · admin reply → cliente WhatsApp dispatch.

        Routes via whatsapp_critical_events_routing chat_admin_reply seed.
        Skipped silently when cliente NO opt-in (dispatch_critical_event
        returns skipped_reason internally).
        """
        try:
            from backend.app.notifications.whatsapp_dispatcher import (
                dispatch_critical_event,
            )

            await dispatch_critical_event(
                self.db,
                event_type="chat_admin_reply",
                project_id=thread.project_id,
                client_user_id=recipient.id,
                payload={
                    "proyecto": project_name,
                    "preview": message.content[:120],
                    "link": (
                        f"https://app.fulkro.com/client-portal/chat"
                    ),
                },
            )
        except Exception:
            logger.exception(
                "ChatService WhatsApp dispatch admin reply failed "
                "thread=%s · best-effort fallback",
                thread.id,
            )

    async def _dispatch_client_inbound_to_marcos(
        self,
        *,
        thread: ChatThread,
        message: ChatMessage,
    ) -> None:
        """CLUSTER 5 Phase 5D delta · cliente inbound → Marcos WhatsApp.

        Cliente escribe → notifica Marcos vía WhatsApp Business directo a
        marcos_whatsapp_number (settings env). Bypass per-cliente routing
        table porque destinatario es admin (Marcos), no cliente.

        Mock mode default · production requires whatsapp_provider=360dialog
        + KYC Meta Business done. Skipped silently if marcos_whatsapp_number
        empty (degradación elegante · email path notify_chat_admin_inbound
        future Phase 5D+ extension).
        """
        try:
            from backend.app.config import get_settings
            from backend.app.motors.m31_whatsapp.dialog_360_client import (
                Dialog360Client,
            )

            settings = get_settings()
            # #26 · preferir el número configurado en el panel admin (persistido)
            # sobre el de entorno · best-effort (si no hay admin settings, cae al
            # env). Así Marcos cambia el destino sin reiniciar el servidor.
            admin_number = ""
            try:
                from backend.app.admin_settings.service import (
                    get_settings as get_admin_settings,
                )
                _admin = await get_admin_settings(self.db)
                admin_number = (
                    getattr(
                        _admin.notifications, "marcos_whatsapp_number", None,
                    ) or ""
                )
            except Exception:
                admin_number = ""
            marcos_number = (
                admin_number or settings.marcos_whatsapp_number or ""
            ).strip()
            if not marcos_number:
                return

            project_row = (await self.db.execute(
                _sa_text(
                    "SELECT nombre FROM projects WHERE id = :pid"
                ),
                {"pid": str(thread.project_id)},
            )).first()
            project_name = project_row[0] if project_row else "(proyecto)"

            recipient_name = "Cliente"
            if thread.client_user_id is not None:
                user_row = (await self.db.execute(
                    _sa_text(
                        "SELECT COALESCE(full_name, email) FROM client_users "
                        "WHERE id = :uid"
                    ),
                    {"uid": str(thread.client_user_id)},
                )).first()
                if user_row and user_row[0]:
                    recipient_name = user_row[0]

            body = (
                f"💬 {recipient_name} te escribió en {project_name}: "
                f"\"{message.content[:120]}\"\n\n"
                f"Responder en el portal admin."
            )
            api_key_secret = settings.dialog_360_api_key
            api_key = (
                api_key_secret.get_secret_value()
                if hasattr(api_key_secret, "get_secret_value")
                else (api_key_secret or "")
            )
            client = Dialog360Client(
                api_key=api_key,
                phone_number_id=settings.dialog_360_phone_number_id or "",
                mock_mode=(settings.whatsapp_provider != "360dialog"),
            )
            await client.send_text(to=marcos_number, body=body)
        except Exception:
            logger.exception(
                "ChatService WhatsApp dispatch client inbound to Marcos "
                "failed thread=%s · best-effort",
                thread.id,
            )

    async def get_sla_status(
        self, thread_id: UUID,
    ) -> dict:
        """SLA status thread · breach cuando admin response > 2h post client msg."""
        thread = await self.db.get(ChatThread, thread_id)
        if not thread:
            raise ChatError("Thread not found")

        now = datetime.now(timezone.utc)
        SLA_HOURS = 2

        last_client = thread.last_client_message_at
        last_admin = thread.last_admin_response_at

        if not last_client:
            return {
                "thread_id": str(thread_id),
                "sla_breached": False,
                "reason": "no_client_messages_yet",
                "minutes_since_last_client_msg": None,
            }

        if last_admin and last_admin > last_client:
            # Admin already responded post-client
            return {
                "thread_id": str(thread_id),
                "sla_breached": False,
                "reason": "admin_responded",
                "minutes_since_last_client_msg": int(
                    (now - last_client).total_seconds() / 60,
                ),
            }

        # Pendiente respuesta admin
        elapsed_min = int((now - last_client).total_seconds() / 60)
        breached = elapsed_min > (SLA_HOURS * 60)
        return {
            "thread_id": str(thread_id),
            "sla_breached": breached,
            "reason": "awaiting_admin_response",
            "minutes_since_last_client_msg": elapsed_min,
            "sla_threshold_minutes": SLA_HOURS * 60,
        }
