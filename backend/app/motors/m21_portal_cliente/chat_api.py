"""Chat REST endpoints (ADR-038 SAN-D MB-14.5).

Cliente:
- GET  /client-portal/chat/threads
- POST /client-portal/chat/threads · {subject?}
- GET  /client-portal/chat/threads/{id}/messages
- POST /client-portal/chat/threads/{id}/messages · {content}

Admin:
- GET  /admin/projects/{id}/chat/threads
- GET  /admin/projects/{id}/chat/threads/{tid}/messages
- POST /admin/projects/{id}/chat/threads/{tid}/messages · {content}
- GET  /admin/projects/{id}/chat/threads/{tid}/sla
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db, set_tenant_context
from backend.app.models.client_portal import ClientUser
from backend.app.motors.m21_portal_cliente.api import get_current_client_user
from backend.app.motors.m21_portal_cliente.chat_service import (
    ChatError,
    ChatService,
)


client_chat_router = APIRouter(tags=["MB-14 - Client Chat"])
admin_chat_router = APIRouter(tags=["MB-14 - Admin Chat"])


class ThreadCreateBody(BaseModel):
    subject: str | None = None


class MessagePostBody(BaseModel):
    content: str


def _serialize_thread(t) -> dict:
    return {
        "id": str(t.id),
        "project_id": str(t.project_id),
        "subject": t.subject,
        "status": t.status,
        "messages_count": t.messages_count,
        "last_client_message_at": (
            t.last_client_message_at.isoformat()
            if t.last_client_message_at else None
        ),
        "last_admin_response_at": (
            t.last_admin_response_at.isoformat()
            if t.last_admin_response_at else None
        ),
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


def _serialize_message(m) -> dict:
    return {
        "id": str(m.id),
        "thread_id": str(m.thread_id),
        "sender_type": m.sender_type,
        "sender_user_id": (
            str(m.sender_user_id) if m.sender_user_id else None
        ),
        "content": m.content,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


async def _resolve_client_project_id(
    db: AsyncSession, client_user: ClientUser,
) -> UUID:
    # projects tiene FORCE RLS (client_isolation USING client_id=current_client_id()):
    # hay que fijar app.current_client_id ANTES de leerla, si no devuelve 0 filas
    # → 404 falso en producción bajo fulkro_app (verificado empíricamente).
    await db.execute(
        text("SELECT set_config('app.current_client_id', :cid, true)"),
        {"cid": str(client_user.client_id)},
    )
    result = await db.execute(
        text(
            "SELECT id FROM projects WHERE client_id = :cid "
            "AND deleted_at IS NULL "
            "ORDER BY created_at DESC LIMIT 1"
        ),
        {"cid": str(client_user.client_id)},
    )
    project_id = result.scalar_one_or_none()
    if not project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Sin proyecto",
        )
    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": str(project_id)},
    )
    await db.execute(
        text("SELECT set_config('app.current_client_id', :cid, true)"),
        {"cid": str(client_user.client_id)},
    )
    return project_id


async def _assert_thread_in_project(
    db: AsyncSession, thread_id: UUID, project_id: UUID,
) -> None:
    """Defense-in-depth ownership check (IDOR · verificado empíricamente).

    El portal cliente corre bajo fulkro_app_bypassrls durante todo el request
    (verify_session lo fija para poder leer client_sessions). Eso DESACTIVA la
    RLS, así que un cliente podía leer/escribir en el hilo de OTRO cliente
    pasando su thread_id directamente (cross-tenant read+write confirmado en el
    roleplay). Comprobamos explícitamente que el hilo pertenece al proyecto del
    cliente. 404 (no 403) para no filtrar la existencia del recurso ajeno."""
    row = (await db.execute(
        text(
            "SELECT 1 FROM chat_threads "
            "WHERE id = :tid AND project_id = :pid AND deleted_at IS NULL"
        ),
        {"tid": str(thread_id), "pid": str(project_id)},
    )).first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found",
        )


# ── Cliente endpoints ─────────────────────────────────────


@client_chat_router.get("/client-portal/chat/threads")
async def client_list_threads(
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> list[dict]:
    project_id = await _resolve_client_project_id(db, user)
    service = ChatService(db)
    threads = await service.list_threads(project_id)
    return [_serialize_thread(t) for t in threads]


@client_chat_router.post("/client-portal/chat/threads")
async def client_create_thread(
    body: ThreadCreateBody,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> dict:
    project_id = await _resolve_client_project_id(db, user)
    service = ChatService(db)
    thread = await service.get_or_create_thread(
        project_id=project_id,
        client_user_id=user.id,
        subject=body.subject,
    )
    await db.commit()  # get_db() no auto-commitea: persistir el thread creado
    return _serialize_thread(thread)


@client_chat_router.get(
    "/client-portal/chat/threads/{thread_id}/messages"
)
async def client_list_messages(
    thread_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> list[dict]:
    project_id = await _resolve_client_project_id(db, user)
    await _assert_thread_in_project(db, thread_id, project_id)
    service = ChatService(db)
    messages = await service.list_messages(thread_id)
    return [_serialize_message(m) for m in messages]


@client_chat_router.post(
    "/client-portal/chat/threads/{thread_id}/messages"
)
async def client_post_message(
    thread_id: UUID,
    body: MessagePostBody,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> dict:
    project_id = await _resolve_client_project_id(db, user)
    await _assert_thread_in_project(db, thread_id, project_id)
    service = ChatService(db)
    try:
        msg = await service.post_message(
            thread_id=thread_id,
            sender_type="client",
            content=body.content,
            sender_user_id=user.id,
        )
    except ChatError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc),
        )
    await db.commit()  # get_db() no auto-commitea: persistir el mensaje
    return _serialize_message(msg)


@client_chat_router.post(
    "/client-portal/chat/threads/{thread_id}/mark-read"
)
async def client_mark_read(
    thread_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> dict:
    """CLUSTER 5 Phase 5B delta · cliente bulk-marks admin messages as read.

    audit_log emit chat.message.read (Sub-atom 5.A 3-way OR) via
    ChatService.mark_messages_read.
    """
    project_id = await _resolve_client_project_id(db, user)
    await _assert_thread_in_project(db, thread_id, project_id)
    service = ChatService(db)
    try:
        marked = await service.mark_messages_read(
            thread_id=thread_id,
            reader_role="client",
            reader_user_id=user.id,
        )
    except ChatError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc),
        )
    await db.commit()  # get_db() no auto-commitea: persistir read_at
    return {"marked_count": marked}


# ── Admin endpoints ─────────────────────────────────────


async def _set_admin_project_rls(project_id: UUID, db: AsyncSession) -> None:
    """Los endpoints admin corren bajo fulkro_app (RLS forzado · NO bypassrls).
    chat_threads/chat_messages filtran por current_project_id → sin fijar el
    contexto de tenant el admin ve 0 hilos y no puede responder (404/[]/400 en
    prod · verificado empíricamente en el roleplay). Resuelve el owner del
    proyecto y fija el contexto (mismo patrón que el resto de endpoints admin
    project-scoped · p.ej. m15 financial_extensions._set_project_rls)."""
    client_id = (await db.execute(
        text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)}
    )).scalar()
    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found",
        )
    await set_tenant_context(db, client_id=client_id, project_id=project_id)


@admin_chat_router.get("/projects/{project_id}/chat/threads")
async def admin_list_threads(
    project_id: UUID,
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_owner),
) -> list[dict]:
    await _set_admin_project_rls(project_id, db)
    service = ChatService(db)
    threads = await service.list_threads(project_id, status=status_filter)
    return [_serialize_thread(t) for t in threads]


@admin_chat_router.get(
    "/projects/{project_id}/chat/threads/{thread_id}/messages"
)
async def admin_list_messages(
    project_id: UUID,
    thread_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_owner),
) -> list[dict]:
    await _set_admin_project_rls(project_id, db)
    service = ChatService(db)
    messages = await service.list_messages(thread_id)
    return [_serialize_message(m) for m in messages]


@admin_chat_router.post(
    "/projects/{project_id}/chat/threads/{thread_id}/messages"
)
async def admin_post_message(
    project_id: UUID,
    thread_id: UUID,
    body: MessagePostBody,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_owner),
) -> dict:
    await _set_admin_project_rls(project_id, db)
    service = ChatService(db)
    try:
        msg = await service.post_message(
            thread_id=thread_id,
            sender_type="admin",
            content=body.content,
            sender_user_id=current_user.id,
        )
    except ChatError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc),
        )
    await db.commit()  # get_db() no auto-commitea: persistir el mensaje admin
    return _serialize_message(msg)


@admin_chat_router.get(
    "/projects/{project_id}/chat/threads/{thread_id}/sla"
)
async def admin_thread_sla(
    project_id: UUID,
    thread_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_owner),
) -> dict:
    await _set_admin_project_rls(project_id, db)
    service = ChatService(db)
    try:
        return await service.get_sla_status(thread_id)
    except ChatError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc),
        )


@admin_chat_router.post(
    "/projects/{project_id}/chat/threads/{thread_id}/mark-read"
)
async def admin_mark_read(
    project_id: UUID,
    thread_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_owner),
) -> dict:
    """CLUSTER 5 Phase 5B delta · admin bulk-marks client messages as read.

    audit_log emit chat.message.read (Sub-atom 5.A) via
    ChatService.mark_messages_read.
    """
    await _set_admin_project_rls(project_id, db)
    service = ChatService(db)
    try:
        marked = await service.mark_messages_read(
            thread_id=thread_id,
            reader_role="admin",
            reader_user_id=current_user.id,
        )
    except ChatError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc),
        )
    await db.commit()  # get_db() no auto-commitea: persistir read_at
    return {"marked_count": marked}
