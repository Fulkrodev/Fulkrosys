"""Motor 29 — Client Messaging: business logic core.

Servicio principal mensajería bidireccional cliente↔admin. Métodos:

  CLIENTE:
    - ``send_as_client`` — POST /client-portal/messages
    - ``list_threads_for_client`` — listado threads cliente
    - ``get_thread_for_client`` — vista thread + attachments

  ADMIN:
    - ``send_as_admin`` — POST /admin/messages (con to_contact_id opcional)
    - ``list_threads_for_admin`` — inbox admin con filtros
    - ``get_thread_for_admin`` — vista thread + attachments
    - ``search_messages`` — full-text search GIN

  COMÚN:
    - ``mark_as_read`` — idempotente per pool
    - ``get_unread_count`` — badge sidebar
    - ``soft_delete_message`` — owner only

Cross-motor:
  - ``log_interaction`` M30 invocado al enviar mensaje a contacto
    (interaction_type='message', source_motor='m29').
  - EmailSender invocado vía ``email_forward.py`` (sub-fase 6.A.4).
  - Audit_log triggers persisten cambios (BD-side).

Pattern coherente con M30 ClientContactService + M18 MinutesService.
"""
from __future__ import annotations

import html
import uuid
from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import and_, desc, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m29_client_messaging.models import (
    ClientMessage,
    ClientMessageAttachment,
)
from backend.app.motors.m29_client_messaging.schemas import (
    AdminSendMessageBody,
    ClientSendMessageBody,
    MessageOut,
    ThreadSummary,
    UnreadCountResponse,
)


# ====================================================================
# Excepciones de dominio
# ====================================================================


class MessageNotFoundError(Exception):
    """Mensaje no encontrado por id (o soft-deleted)."""


class ThreadNotFoundError(Exception):
    """Thread no encontrado o no pertenece al cliente solicitante."""


class ThreadOwnershipError(Exception):
    """Cliente intenta acceder a thread de otro cliente (RLS guard
    redundante service-side; RLS BD ya filtra)."""


class MessagePermissionError(Exception):
    """Pool no autorizado para esta operación (ej. cliente intenta
    soft-delete mensaje del admin)."""


# ====================================================================
# Helpers internos
# ====================================================================


def _excerpt(body: str, max_chars: int = 200) -> str:
    """Trunca body al máximo de chars + ellipsis si overflow."""
    if len(body) <= max_chars:
        return body
    return body[: max_chars - 1].rstrip() + "…"


def _render_safe_html(body_markdown: str) -> str:
    """Render conservador HTML-safe del markdown.

    Server-side mantiene defensa profunda: HTML escape básico para
    evitar XSS si un consumer renderiza body_html sin sanitizar.

    Render markdown completo (negritas, listas, links) sucede client-side
    via remark + rehype-sanitize (plan v4.2 6.31). Aquí solo escapamos
    para tener un fallback seguro en emails out-of-band y previews.
    """
    return html.escape(body_markdown).replace("\n", "<br>")


# ====================================================================
# Servicio
# ====================================================================


class ClientMessagingService:
    """Servicio mensajería cliente↔admin (motor 29)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ----------------------------------------------------------------
    # CLIENTE — send + list + get
    # ----------------------------------------------------------------

    async def send_as_client(
        self,
        client_id: uuid.UUID,
        client_user_id: uuid.UUID,
        payload: ClientSendMessageBody,
    ) -> ClientMessage:
        """Cliente envía mensaje (nuevo thread o reply existing).

        Si ``payload.thread_id`` ausente: crea thread nuevo (UUID gen).
        Si presente: valida que el thread pertenece al cliente (mismo
        ``client_id``) — RLS BD ya filtraría pero validamos en service
        para mensaje de error explícito en lugar de FK violation.
        """
        thread_id = payload.thread_id or uuid.uuid4()

        if payload.thread_id is not None:
            owns = await self._thread_belongs_to_client(
                payload.thread_id, client_id,
            )
            if not owns:
                raise ThreadOwnershipError(
                    f"Thread {payload.thread_id} no pertenece al cliente "
                    f"{client_id} o no existe."
                )

        message = ClientMessage(
            client_id=client_id,
            project_id=payload.project_id,
            thread_id=thread_id,
            from_role="client",
            from_user_id=client_user_id,
            to_contact_id=None,  # cliente envía al admin general
            body_markdown=payload.body_markdown,
            body_html=_render_safe_html(payload.body_markdown),
            is_read_by_admin=False,
            is_read_by_client=True,  # auto-read por sender propio
        )
        self.db.add(message)
        await self.db.flush()
        await self.db.refresh(message)
        return message

    async def list_threads_for_client(
        self,
        client_id: uuid.UUID,
        *,
        limit: int = 50,
    ) -> list[ThreadSummary]:
        """Lista threads del cliente ordenados por último mensaje DESC."""
        return await self._list_threads(
            filter_client_id=client_id, limit=limit,
        )

    async def get_thread_for_client(
        self,
        thread_id: uuid.UUID,
        client_id: uuid.UUID,
    ) -> list[MessageOut]:
        """Mensajes del thread + attachments. Valida ownership."""
        owns = await self._thread_belongs_to_client(thread_id, client_id)
        if not owns:
            raise ThreadOwnershipError(
                f"Thread {thread_id} no pertenece al cliente {client_id}."
            )
        return await self._fetch_thread_messages(thread_id)

    # ----------------------------------------------------------------
    # ADMIN — send + list + get + search
    # ----------------------------------------------------------------

    async def send_as_admin(
        self,
        admin_user_id: uuid.UUID,
        payload: AdminSendMessageBody,
    ) -> ClientMessage:
        """Marcos envía/responde con M30 picker opcional.

        Modos:
          - Nuevo thread: ``payload.client_id`` requerido + sin thread_id.
          - Reply: ``payload.thread_id`` requerido. ``client_id`` derivado
            del thread (validamos coherencia si client_id también enviado).

        Auto-log M30: si ``payload.to_contact_id`` presente, post-flush
        invoca ``ClientContactService.log_interaction``. Silent fail si
        contacto no existe (consistente A18/M14 pattern).
        """
        # Resolver client_id según modo
        if payload.thread_id is not None:
            # Reply: derivar client_id del thread
            client_id = await self._client_id_from_thread(payload.thread_id)
            if client_id is None:
                raise ThreadNotFoundError(
                    f"Thread {payload.thread_id} no existe."
                )
            # Si payload.client_id presente, validar coherencia
            if payload.client_id is not None and payload.client_id != client_id:
                raise ThreadNotFoundError(
                    f"Thread {payload.thread_id} pertenece a "
                    f"{client_id}, no a {payload.client_id}."
                )
            thread_id = payload.thread_id
        else:
            # Nuevo thread: client_id requerido
            if payload.client_id is None:
                raise MessagePermissionError(
                    "Nuevo thread requiere client_id en payload."
                )
            client_id = payload.client_id
            thread_id = uuid.uuid4()

        message = ClientMessage(
            client_id=client_id,
            project_id=payload.project_id,
            thread_id=thread_id,
            from_role="admin",
            from_user_id=admin_user_id,
            to_contact_id=payload.to_contact_id,
            body_markdown=payload.body_markdown,
            body_html=_render_safe_html(payload.body_markdown),
            is_read_by_admin=True,  # auto-read por sender propio
            is_read_by_client=False,
        )
        self.db.add(message)
        await self.db.flush()
        await self.db.refresh(message)

        # M30 cross-motor integration: log interaction si contact destinatario
        if payload.to_contact_id is not None:
            await self._log_interaction_m30(
                contact_id=payload.to_contact_id,
                message=message,
            )

        return message

    async def list_threads_for_admin(
        self,
        *,
        client_id: uuid.UUID | None = None,
        contact_id: uuid.UUID | None = None,
        only_unread: bool = False,
        limit: int = 50,
    ) -> list[ThreadSummary]:
        """Inbox admin con filtros opcionales."""
        return await self._list_threads(
            filter_client_id=client_id,
            filter_to_contact_id=contact_id,
            only_unread_for_admin=only_unread,
            limit=limit,
        )

    async def get_thread_for_admin(
        self,
        thread_id: uuid.UUID,
    ) -> list[MessageOut]:
        """Vista admin thread (sin ownership check; admin ve todos)."""
        return await self._fetch_thread_messages(thread_id)

    async def search_messages_admin(
        self,
        query: str,
        *,
        client_id: uuid.UUID | None = None,
        limit: int = 25,
    ) -> list[MessageOut]:
        """Full-text search admin sobre body_markdown vía GIN.

        Pattern: ``to_tsvector('spanish', body_markdown) @@ plainto_tsquery``.
        """
        if not query.strip():
            return []
        from sqlalchemy.orm import selectinload

        stmt = (
            select(ClientMessage)
            .where(
                ClientMessage.deleted_at.is_(None),
                text(
                    "to_tsvector('spanish', body_markdown) "
                    "@@ plainto_tsquery('spanish', :q)"
                ).bindparams(q=query),
            )
            .options(selectinload(ClientMessage.attachments))
            .order_by(desc(ClientMessage.created_at))
            .limit(limit)
        )
        if client_id is not None:
            stmt = stmt.where(ClientMessage.client_id == client_id)
        result = await self.db.execute(stmt)
        messages = list(result.scalars())
        return [
            MessageOut.model_validate(m) for m in messages
        ]

    # ----------------------------------------------------------------
    # COMÚN — mark_as_read + unread_count + soft_delete
    # ----------------------------------------------------------------

    async def mark_as_read(
        self,
        message_id: uuid.UUID,
        by_role: Literal["client", "admin"],
        client_id: uuid.UUID | None = None,
    ) -> ClientMessage:
        """Marca mensaje como leído por pool. Idempotente.

        Cliente sólo puede marcar mensajes con ``from_role='admin'``
        (no tiene sentido marcar propio como read).
        Admin sólo puede marcar mensajes con ``from_role='client'``.

        ``client_id`` (defensa-en-profundidad IDOR): el portal corre bajo
        bypassrls, así que validamos explícitamente que el mensaje pertenece
        al cliente que lo marca. 404 si es de otro tenant (verificado en el
        roleplay: sin esto un cliente podía voltear el flag de lectura de un
        mensaje admin→otro-cliente).
        """
        msg = await self.db.get(ClientMessage, message_id)
        if msg is None or msg.deleted_at is not None:
            raise MessageNotFoundError(f"Mensaje {message_id} no existe.")

        if client_id is not None and msg.client_id != client_id:
            raise MessageNotFoundError(f"Mensaje {message_id} no existe.")

        if by_role == "client":
            if msg.from_role != "admin":
                # cliente intenta marcar propio mensaje → noop idempotente
                return msg
            msg.is_read_by_client = True
        elif by_role == "admin":
            if msg.from_role != "client":
                return msg
            msg.is_read_by_admin = True

        await self.db.flush()
        await self.db.refresh(msg)
        return msg

    async def get_unread_count(
        self,
        *,
        for_role: Literal["client", "admin"],
        client_id: uuid.UUID | None = None,
    ) -> UnreadCountResponse:
        """Counts para badge sidebar.

        Para ``for_role='admin'``: mensajes con ``from_role='client'`` y
        ``is_read_by_admin=False``. ``client_id`` opcional filtra.

        Para ``for_role='client'``: mensajes con ``from_role='admin'`` y
        ``is_read_by_client=False``. ``client_id`` requerido (RLS también
        scopea).
        """
        if for_role == "admin":
            unread_filter = and_(
                ClientMessage.from_role == "client",
                ClientMessage.is_read_by_admin.is_(False),
                ClientMessage.deleted_at.is_(None),
            )
        else:
            if client_id is None:
                raise MessagePermissionError(
                    "client_id requerido para unread_count cliente."
                )
            unread_filter = and_(
                ClientMessage.from_role == "admin",
                ClientMessage.is_read_by_client.is_(False),
                ClientMessage.client_id == client_id,
                ClientMessage.deleted_at.is_(None),
            )

        if client_id is not None and for_role == "admin":
            unread_filter = and_(
                unread_filter,
                ClientMessage.client_id == client_id,
            )

        # Total mensajes
        total_stmt = select(func.count(ClientMessage.id)).where(unread_filter)
        total = (await self.db.execute(total_stmt)).scalar_one() or 0

        # Threads únicos
        threads_stmt = select(
            func.count(func.distinct(ClientMessage.thread_id))
        ).where(unread_filter)
        threads = (await self.db.execute(threads_stmt)).scalar_one() or 0

        return UnreadCountResponse(
            unread_total=total, unread_threads=threads,
        )

    async def soft_delete_message(
        self,
        message_id: uuid.UUID,
        by_user_id: uuid.UUID,
        by_role: Literal["client", "admin"],
    ) -> None:
        """Soft-delete (set deleted_at). Solo el sender puede borrar
        su propio mensaje; admin puede borrar cualquiera (moderación)."""
        msg = await self.db.get(ClientMessage, message_id)
        if msg is None or msg.deleted_at is not None:
            raise MessageNotFoundError(f"Mensaje {message_id} no existe.")

        is_owner = msg.from_user_id == by_user_id
        is_admin_moderating = by_role == "admin"
        if not (is_owner or is_admin_moderating):
            raise MessagePermissionError(
                f"User {by_user_id} no puede borrar mensaje {message_id} "
                f"(no es owner ni admin)."
            )

        msg.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()

    # ----------------------------------------------------------------
    # Helpers privados
    # ----------------------------------------------------------------

    async def _thread_belongs_to_client(
        self,
        thread_id: uuid.UUID,
        client_id: uuid.UUID,
    ) -> bool:
        """True si existe ≥1 mensaje en el thread con ese client_id."""
        stmt = select(ClientMessage.id).where(
            ClientMessage.thread_id == thread_id,
            ClientMessage.client_id == client_id,
            ClientMessage.deleted_at.is_(None),
        ).limit(1)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def _client_id_from_thread(
        self,
        thread_id: uuid.UUID,
    ) -> uuid.UUID | None:
        """Devuelve client_id del thread (basado en primer mensaje)."""
        stmt = select(ClientMessage.client_id).where(
            ClientMessage.thread_id == thread_id,
            ClientMessage.deleted_at.is_(None),
        ).order_by(ClientMessage.created_at).limit(1)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _fetch_thread_messages(
        self,
        thread_id: uuid.UUID,
    ) -> list[MessageOut]:
        """Mensajes del thread ordenados ASC + attachments eager-load."""
        from sqlalchemy.orm import selectinload

        stmt = (
            select(ClientMessage)
            .where(
                ClientMessage.thread_id == thread_id,
                ClientMessage.deleted_at.is_(None),
            )
            .options(selectinload(ClientMessage.attachments))
            .order_by(ClientMessage.created_at)
        )
        result = await self.db.execute(stmt)
        messages = list(result.scalars())
        return [MessageOut.model_validate(m) for m in messages]

    async def _list_threads(
        self,
        *,
        filter_client_id: uuid.UUID | None = None,
        filter_to_contact_id: uuid.UUID | None = None,
        only_unread_for_admin: bool = False,
        limit: int = 50,
    ) -> list[ThreadSummary]:
        """Agrega thread summaries desde tabla messages.

        Estrategia: subquery con ROW_NUMBER() PARTITION BY thread_id
        ORDER BY created_at DESC para fetch último mensaje + agregaciones.
        """
        # Filtros base (deleted_at IS NULL siempre)
        conditions = [ClientMessage.deleted_at.is_(None)]
        if filter_client_id is not None:
            conditions.append(ClientMessage.client_id == filter_client_id)
        if filter_to_contact_id is not None:
            conditions.append(
                ClientMessage.to_contact_id == filter_to_contact_id
            )

        # Subquery: last message per thread
        last_msg_subq = (
            select(
                ClientMessage.thread_id,
                func.max(ClientMessage.created_at).label("last_at"),
            )
            .where(*conditions)
            .group_by(ClientMessage.thread_id)
            .subquery()
        )

        # Join para obtener info completa del último mensaje
        stmt = (
            select(ClientMessage)
            .join(
                last_msg_subq,
                and_(
                    ClientMessage.thread_id == last_msg_subq.c.thread_id,
                    ClientMessage.created_at == last_msg_subq.c.last_at,
                ),
            )
            .where(*conditions)
            .order_by(desc(ClientMessage.created_at))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        last_messages = list(result.scalars())

        # Para cada thread, calcular agregaciones (count, unread, attachments)
        summaries: list[ThreadSummary] = []
        for last_msg in last_messages:
            thread_id = last_msg.thread_id

            # Total mensajes en thread
            total_stmt = select(func.count(ClientMessage.id)).where(
                ClientMessage.thread_id == thread_id,
                ClientMessage.deleted_at.is_(None),
            )
            total = (await self.db.execute(total_stmt)).scalar_one() or 0

            # Unread for admin (mensajes from_role='client' no leídos)
            ua_stmt = select(func.count(ClientMessage.id)).where(
                ClientMessage.thread_id == thread_id,
                ClientMessage.from_role == "client",
                ClientMessage.is_read_by_admin.is_(False),
                ClientMessage.deleted_at.is_(None),
            )
            ua = (await self.db.execute(ua_stmt)).scalar_one() or 0

            # Unread for client (mensajes from_role='admin' no leídos)
            uc_stmt = select(func.count(ClientMessage.id)).where(
                ClientMessage.thread_id == thread_id,
                ClientMessage.from_role == "admin",
                ClientMessage.is_read_by_client.is_(False),
                ClientMessage.deleted_at.is_(None),
            )
            uc = (await self.db.execute(uc_stmt)).scalar_one() or 0

            # Filter only_unread_for_admin si aplica
            if only_unread_for_admin and ua == 0:
                continue

            # has_attachments check
            attach_stmt = select(func.count(ClientMessageAttachment.id)).where(
                ClientMessageAttachment.message_id.in_(
                    select(ClientMessage.id).where(
                        ClientMessage.thread_id == thread_id,
                        ClientMessage.deleted_at.is_(None),
                    )
                ),
                ClientMessageAttachment.deleted_at.is_(None),
            )
            attach_count = (
                await self.db.execute(attach_stmt)
            ).scalar_one() or 0

            summaries.append(
                ThreadSummary(
                    thread_id=thread_id,
                    client_id=last_msg.client_id,
                    last_message_id=last_msg.id,
                    last_message_excerpt=_excerpt(last_msg.body_markdown),
                    last_message_at=last_msg.created_at,
                    last_message_from_role=last_msg.from_role,  # type: ignore[arg-type]
                    total_messages=total,
                    unread_for_admin=ua,
                    unread_for_client=uc,
                    has_attachments=attach_count > 0,
                    last_to_contact_id=last_msg.to_contact_id,
                )
            )

        return summaries

    async def _log_interaction_m30(
        self,
        *,
        contact_id: uuid.UUID,
        message: ClientMessage,
    ) -> None:
        """Auto-log M30 timeline al enviar mensaje a contacto.

        Silent fail si contacto no existe (pattern A18/M14): el envío
        del mensaje NO debe romper si el contacto fue borrado entre
        composición y envío.
        """
        from backend.app.motors.m30_client_contacts.service import (
            ClientContactService,
            ContactNotFoundError,
        )
        try:
            await ClientContactService(self.db).log_interaction(
                contact_id=contact_id,
                interaction_type="message",
                source_motor="m29",
                source_id=message.id,
                summary=_excerpt(message.body_markdown, 200),
                details={
                    "thread_id": str(message.thread_id),
                    "client_id": str(message.client_id),
                    "from_role": message.from_role,
                },
            )
        except ContactNotFoundError:
            # contacto borrado entre composición y envío — no rompe send
            pass
