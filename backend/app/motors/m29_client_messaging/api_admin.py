"""Motor 29 — API endpoints admin (/admin/messages).

Endpoints (plan v4.2 6.10):

  - POST   /admin/messages                              — send/reply
  - GET    /admin/messages                              — inbox admin
  - GET    /admin/messages/unread-count                 — badge sidebar
  - GET    /admin/messages/search                       — full-text GIN
  - GET    /admin/messages/{thread_id}                  — detalle thread
  - POST   /admin/messages/{message_id}/mark-read       — idempotente
  - DELETE /admin/messages/{message_id}                 — soft-delete
  - POST   /admin/messages/{message_id}/attachments     — presigned PUT
  - POST   /admin/messages/{message_id}/attachments/{att_id}/complete
  - GET    /admin/messages/{message_id}/attachments/{att_id}/download

RBAC: ``Depends(require_owner)`` router-level (M29 admin endpoints
admin-only, M-Marcos pool). Cliente accede via api_client.py.

RLS bypass: cada endpoint hace ``SET LOCAL ROLE fulkro_app_bypassrls`` previo a queries
para acceder a mensajes de cualquier cliente (pattern m12 magic_link
consume / m18 communication / m25 lifecycle).
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db
from backend.app.motors.m29_client_messaging.attachments import (
    AttachmentNotFoundError,
    AttachmentService,
    AttachmentUploadIncompleteError,
    AttachmentValidationError,
)
from backend.app.motors.m29_client_messaging.email_forward import forward_message
from backend.app.motors.m29_client_messaging.schemas import (
    AdminSendMessageBody,
    AttachmentOut,
    AttachmentUploadRequest,
    AttachmentUploadResponse,
    MarkReadResponse,
    MessageOut,
    ThreadSummary,
    UnreadCountResponse,
)
from backend.app.motors.m29_client_messaging.service import (
    ClientMessagingService,
    MessageNotFoundError,
    MessagePermissionError,
    ThreadNotFoundError,
)


router = APIRouter(
    prefix="/admin/messages",
    tags=["Motor 29 - Mensajería Admin"],
    dependencies=[Depends(require_owner)],
)


def _resolve_admin_user_id(request: Request) -> uuid.UUID:
    """Extrae user_id del auth_subject (Marcos pool)."""
    subject = getattr(request.state, "auth_subject", None)
    if subject is None or subject.user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="auth_subject ausente en request.state",
        )
    return subject.user.id


# ────────────────────────────────────────────────────────────────────
# SEND
# ────────────────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=MessageOut,
    status_code=status.HTTP_201_CREATED,
)
async def send_message_admin(
    request: Request,
    body: AdminSendMessageBody,
    db: AsyncSession = Depends(get_db),
) -> MessageOut:
    """Marcos envía nuevo mensaje (con M30 picker opcional)."""
    admin_user_id = _resolve_admin_user_id(request)
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))

    svc = ClientMessagingService(db)
    try:
        msg = await svc.send_as_admin(
            admin_user_id=admin_user_id,
            payload=body,
        )
    except ThreadNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc),
        )
    except MessagePermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        )

    # Email forward (notifica al cliente si to_contact_id presente)
    await forward_message(db, msg)

    await db.commit()
    await db.refresh(msg, attribute_names=["attachments"])
    return MessageOut.model_validate(msg)


# ────────────────────────────────────────────────────────────────────
# LIST + DETAIL + SEARCH + UNREAD
# ────────────────────────────────────────────────────────────────────


@router.get("", response_model=list[ThreadSummary])
async def list_threads_admin(
    client_id: Annotated[uuid.UUID | None, Query()] = None,
    contact_id: Annotated[uuid.UUID | None, Query()] = None,
    only_unread: Annotated[bool, Query()] = False,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    db: AsyncSession = Depends(get_db),
) -> list[ThreadSummary]:
    """Inbox admin con filtros opcionales (client_id, contact_id, unread)."""
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    svc = ClientMessagingService(db)
    return await svc.list_threads_for_admin(
        client_id=client_id,
        contact_id=contact_id,
        only_unread=only_unread,
        limit=limit,
    )


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
)
async def unread_count_admin(
    client_id: Annotated[uuid.UUID | None, Query()] = None,
    db: AsyncSession = Depends(get_db),
) -> UnreadCountResponse:
    """Badge sidebar admin — mensajes cliente no leídos."""
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    svc = ClientMessagingService(db)
    return await svc.get_unread_count(
        for_role="admin", client_id=client_id,
    )


@router.get(
    "/search",
    response_model=list[MessageOut],
)
async def search_messages_admin(
    q: Annotated[str, Query(min_length=1, max_length=500)],
    client_id: Annotated[uuid.UUID | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    db: AsyncSession = Depends(get_db),
) -> list[MessageOut]:
    """Full-text search admin sobre body_markdown (GIN index)."""
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    svc = ClientMessagingService(db)
    return await svc.search_messages_admin(
        query=q, client_id=client_id, limit=limit,
    )


@router.get(
    "/{thread_id}",
    response_model=list[MessageOut],
)
async def get_thread_admin(
    thread_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[MessageOut]:
    """Vista admin thread (sin ownership check)."""
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    svc = ClientMessagingService(db)
    return await svc.get_thread_for_admin(thread_id=thread_id)


# ────────────────────────────────────────────────────────────────────
# MARK READ + DELETE
# ────────────────────────────────────────────────────────────────────


@router.post(
    "/{message_id}/mark-read",
    response_model=MarkReadResponse,
)
async def mark_read_admin(
    message_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> MarkReadResponse:
    """Marca mensaje como leído por admin. Idempotente."""
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    svc = ClientMessagingService(db)
    try:
        msg = await svc.mark_as_read(message_id=message_id, by_role="admin")
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


@router.delete(
    "/{message_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def soft_delete_message_admin(
    request: Request,
    message_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft-delete mensaje (admin puede borrar cualquier mensaje)."""
    admin_user_id = _resolve_admin_user_id(request)
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    svc = ClientMessagingService(db)
    try:
        await svc.soft_delete_message(
            message_id=message_id,
            by_user_id=admin_user_id,
            by_role="admin",
        )
    except MessageNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc),
        )
    except MessagePermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc),
        )
    await db.commit()


# ────────────────────────────────────────────────────────────────────
# ATTACHMENTS
# ────────────────────────────────────────────────────────────────────


@router.post(
    "/{message_id}/attachments",
    response_model=AttachmentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_attachment_upload_admin(
    message_id: uuid.UUID,
    body: AttachmentUploadRequest,
    db: AsyncSession = Depends(get_db),
) -> AttachmentUploadResponse:
    """Admin solicita presigned PUT URL."""
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
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
async def complete_attachment_upload_admin(
    message_id: uuid.UUID,
    attachment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> AttachmentOut:
    """Admin confirma upload completado."""
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    svc = AttachmentService(db)
    try:
        att = await svc.mark_upload_complete(message_id, attachment_id)
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
async def get_attachment_download_admin(
    message_id: uuid.UUID,
    attachment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> AttachmentOut:
    """Admin solicita presigned GET URL."""
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    svc = AttachmentService(db)
    try:
        return await svc.get_download_url(message_id, attachment_id)
    except AttachmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc),
        )
    except AttachmentUploadIncompleteError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc),
        )
