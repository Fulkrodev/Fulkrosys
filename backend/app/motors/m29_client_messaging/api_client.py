"""Motor 29 — API endpoints cliente (/client-portal/messages).

Endpoints (plan v4.2 6.9):

  - POST   /client-portal/messages — send new thread o reply
  - GET    /client-portal/messages — list threads del cliente
  - GET    /client-portal/messages/{thread_id} — detalle thread
  - POST   /client-portal/messages/{message_id}/mark-read — idempotente
  - POST   /client-portal/messages/{message_id}/attachments —
           crear upload + presigned PUT URL
  - POST   /client-portal/messages/{message_id}/attachments/{att_id}/complete —
           verify upload (HEAD MinIO)
  - GET    /client-portal/messages/{message_id}/attachments/{att_id}/download —
           presigned GET URL TTL 7d
  - GET    /client-portal/messages/unread-count — badge sidebar

Auth: ``get_current_client_user`` dep (cookie + CSRF triple binding).
RLS: cliente pool establece ``app.current_client_id`` via global dep
context — RLS BD filtra automáticamente. Service-side ownership checks
redundantes para mensajes de error explícitos.

Pattern coherente con m21_portal_cliente portal_router endpoints.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db, set_tenant_context
from backend.app.models.client_portal import ClientUser
from backend.app.motors.m21_portal_cliente.api import (
    get_current_client_user,
)
from backend.app.motors.m29_client_messaging.attachments import (
    AttachmentNotFoundError,
    AttachmentService,
    AttachmentUploadIncompleteError,
    AttachmentValidationError,
)
from backend.app.motors.m29_client_messaging.email_forward import forward_message
from backend.app.motors.m29_client_messaging.schemas import (
    AttachmentOut,
    AttachmentUploadRequest,
    AttachmentUploadResponse,
    ClientSendMessageBody,
    MarkReadResponse,
    MessageOut,
    ThreadSummary,
    UnreadCountResponse,
)
from backend.app.motors.m29_client_messaging.service import (
    ClientMessagingService,
    MessageNotFoundError,
    ThreadOwnershipError,
)


router = APIRouter(
    prefix="/client-portal/messages",
    tags=["Motor 29 - Mensajería Cliente"],
)


# ────────────────────────────────────────────────────────────────────
# SEND + LIST + DETAIL
# ────────────────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=MessageOut,
    status_code=status.HTTP_201_CREATED,
)
async def send_message_client(
    body: ClientSendMessageBody,
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> MessageOut:
    """Cliente envía nuevo mensaje (nuevo thread o reply existing)."""
    await set_tenant_context(db, client_id=user.client_id)

    svc = ClientMessagingService(db)
    try:
        msg = await svc.send_as_client(
            client_id=user.client_id,
            client_user_id=user.id,
            payload=body,
        )
    except ThreadOwnershipError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc),
        )

    # Email forward out-of-band (Marcos recibe notificación)
    await forward_message(db, msg)

    await db.commit()
    await db.refresh(msg, attribute_names=["attachments"])
    return MessageOut.model_validate(msg)


@router.get("", response_model=list[ThreadSummary])
async def list_threads_client(
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> list[ThreadSummary]:
    """Lista threads del cliente ordenados por último mensaje DESC."""
    await set_tenant_context(db, client_id=user.client_id)
    svc = ClientMessagingService(db)
    return await svc.list_threads_for_client(client_id=user.client_id)


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
)
async def unread_count_client(
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> UnreadCountResponse:
    """Badge sidebar cliente — mensajes admin no leídos."""
    await set_tenant_context(db, client_id=user.client_id)
    svc = ClientMessagingService(db)
    return await svc.get_unread_count(
        for_role="client", client_id=user.client_id,
    )


@router.get(
    "/{thread_id}",
    response_model=list[MessageOut],
)
async def get_thread_client(
    thread_id: uuid.UUID,
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> list[MessageOut]:
    """Mensajes del thread + attachments. Valida ownership cliente."""
    await set_tenant_context(db, client_id=user.client_id)
    svc = ClientMessagingService(db)
    try:
        return await svc.get_thread_for_client(
            thread_id=thread_id, client_id=user.client_id,
        )
    except ThreadOwnershipError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc),
        )


# ────────────────────────────────────────────────────────────────────
# MARK READ
# ────────────────────────────────────────────────────────────────────


@router.post(
    "/{message_id}/mark-read",
    response_model=MarkReadResponse,
)
async def mark_read_client(
    message_id: uuid.UUID,
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> MarkReadResponse:
    """Marca mensaje como leído por cliente. Idempotente."""
    await set_tenant_context(db, client_id=user.client_id)
    svc = ClientMessagingService(db)
    try:
        msg = await svc.mark_as_read(
            message_id=message_id, by_role="client", client_id=user.client_id,
        )
    except MessageNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc),
        )
    await db.commit()
    return MarkReadResponse(
        message_id=msg.id,
        is_read_by_admin=msg.is_read_by_admin,
        is_read_by_client=msg.is_read_by_client,
    )


# ────────────────────────────────────────────────────────────────────
# ATTACHMENTS
# ────────────────────────────────────────────────────────────────────


@router.post(
    "/{message_id}/attachments",
    response_model=AttachmentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_attachment_upload_client(
    message_id: uuid.UUID,
    body: AttachmentUploadRequest,
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> AttachmentUploadResponse:
    """Cliente solicita presigned PUT URL para subir adjunto."""
    await set_tenant_context(db, client_id=user.client_id)
    # Ownership: validar que el mensaje pertenece al cliente
    await _ensure_message_belongs_to_client(db, message_id, user.client_id)

    svc = AttachmentService(db)
    try:
        resp = await svc.create_upload(message_id, body)
    except AttachmentValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        )
    except MessageNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc),
        )
    await db.commit()
    return resp


@router.post(
    "/{message_id}/attachments/{attachment_id}/complete",
    response_model=AttachmentOut,
)
async def complete_attachment_upload_client(
    message_id: uuid.UUID,
    attachment_id: uuid.UUID,
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> AttachmentOut:
    """Cliente confirma upload completado. Service hace HEAD MinIO."""
    await set_tenant_context(db, client_id=user.client_id)
    await _ensure_message_belongs_to_client(db, message_id, user.client_id)

    svc = AttachmentService(db)
    try:
        att = await svc.mark_upload_complete(attachment_id)
    except AttachmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc),
        )
    except AttachmentUploadIncompleteError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc),
        )
    except AttachmentValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        )
    await db.commit()
    return att


@router.get(
    "/{message_id}/attachments/{attachment_id}/download",
    response_model=AttachmentOut,
)
async def get_attachment_download_client(
    message_id: uuid.UUID,
    attachment_id: uuid.UUID,
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> AttachmentOut:
    """Cliente solicita presigned GET URL para descargar adjunto."""
    await set_tenant_context(db, client_id=user.client_id)
    await _ensure_message_belongs_to_client(db, message_id, user.client_id)

    svc = AttachmentService(db)
    try:
        return await svc.get_download_url(attachment_id)
    except AttachmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc),
        )
    except AttachmentUploadIncompleteError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc),
        )


# ────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────


async def _ensure_message_belongs_to_client(
    db: AsyncSession,
    message_id: uuid.UUID,
    client_id: uuid.UUID,
) -> None:
    """Valida que el mensaje pertenece al cliente (defensa profunda).

    RLS BD ya filtra (client_isolation) pero validamos service-side
    para mensaje 404 explícito vs constraint violation oscuro.
    """
    from backend.app.motors.m29_client_messaging.models import ClientMessage
    msg = await db.get(ClientMessage, message_id)
    if msg is None or msg.deleted_at is not None or msg.client_id != client_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mensaje {message_id} no encontrado.",
        )
