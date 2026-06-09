"""SSE realtime WhatsApp inbound · MB-8 closure.

Reuses the m11_copiloto streaming pattern (Q6.C MB-7 cement). Polls the
DB every 1.5s for new WhatsAppMessage rows after a `last_check_at` cursor,
yields each as a JSON SSE data frame. Cliente and admin variants share
this implementation.
"""
from __future__ import annotations

import asyncio
import json as _json
import logging
import uuid
from datetime import datetime, timezone
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import async_session, get_db
from backend.app.models.client_portal import ClientUser
from backend.app.motors.m21_portal_cliente.api import get_current_client_user
from backend.app.motors.m31_whatsapp.models import (
    WhatsAppMessage,
    WhatsAppThread,
)


logger = logging.getLogger(__name__)


POLL_INTERVAL_SECONDS = 1.5
KEEPALIVE_INTERVAL_SECONDS = 25


sse_router = APIRouter(tags=["whatsapp - SSE"])


def _serialize_message_dict(m: WhatsAppMessage) -> dict:
    return {
        "id": str(m.id),
        "thread_id": str(m.thread_id),
        "direction": m.direction,
        "sender_type": m.sender_type,
        "content": m.content,
        "sent_at": m.sent_at.isoformat() if m.sent_at else None,
        "delivered_at": (
            m.delivered_at.isoformat() if m.delivered_at else None
        ),
        "read_at": m.read_at.isoformat() if m.read_at else None,
    }


async def _stream_messages(
    thread_id: uuid.UUID,
    *,
    admin_role: bool,
    request: Request,
    project_id: uuid.UUID | None = None,
) -> AsyncIterator[str]:
    """Common SSE body · yields data frames for new messages.

    FIX P1-3: usa una ``AsyncSession`` EFÍMERA por ciclo de poll (abrir → query
    → cerrar) en vez de retener la sesión de ``get_db`` durante todo el stream.
    Antes, cada ``EventSource`` ocupaba una conexión del pool (20+10) durante
    minutos/horas → ~30 streams agotaban el pool y TODO lo demás fallaba a los
    30s (DoS). Ahora la conexión solo se toma durante la query (~ms), no durante
    el ``sleep`` de 1.5s. El contexto (rol admin / project_id cliente) se re-aplica
    en cada sesión efímera.
    """
    last_check = datetime.now(timezone.utc)
    yield f": connected at {last_check.isoformat()}\n\n"
    last_keepalive = last_check

    try:
        while True:
            if await request.is_disconnected():
                break

            async with async_session() as s:
                if admin_role:
                    await s.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
                elif project_id is not None:
                    await s.execute(
                        text("SELECT set_config('app.current_project_id', :v, true)"),
                        {"v": str(project_id)},
                    )
                rows = (await s.execute(
                    select(WhatsAppMessage).where(
                        WhatsAppMessage.thread_id == thread_id,
                        WhatsAppMessage.sent_at > last_check,
                        WhatsAppMessage.deleted_at.is_(None),
                    ).order_by(WhatsAppMessage.sent_at.asc())
                )).scalars().all()
                # Serializar DENTRO de la sesión (evita acceso a ORM detached).
                payloads = [_serialize_message_dict(m) for m in rows]
                max_sent = max(
                    (m.sent_at for m in rows if m.sent_at), default=None,
                )
            # sesión cerrada · conexión devuelta al pool ANTES del sleep.

            for payload in payloads:
                yield f"data: {_json.dumps(payload, ensure_ascii=False)}\n\n"
            if max_sent and max_sent > last_check:
                last_check = max_sent

            now = datetime.now(timezone.utc)
            if (now - last_keepalive).total_seconds() >= KEEPALIVE_INTERVAL_SECONDS:
                yield ": keepalive\n\n"
                last_keepalive = now

            await asyncio.sleep(POLL_INTERVAL_SECONDS)
    except asyncio.CancelledError:
        return


@sse_router.get("/client-portal/whatsapp/thread/{thread_id}/sse")
async def cliente_whatsapp_sse(
    thread_id: uuid.UUID,
    request: Request,
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
):
    """Cliente SSE · only own thread messages."""
    # Resolve project + verify thread ownership
    proj_row = (await db.execute(text(
        "SELECT id FROM projects WHERE client_id = :cid "
        "AND deleted_at IS NULL ORDER BY created_at DESC LIMIT 1"
    ), {"cid": str(user.client_id)})).first()
    if proj_row is None:
        raise HTTPException(status_code=404, detail="No active project")
    project_id = proj_row[0]
    await db.execute(
        text("SELECT set_config('app.current_project_id', :v, true)"),
        {"v": str(project_id)},
    )

    thread = (await db.execute(
        select(WhatsAppThread).where(
            WhatsAppThread.id == thread_id,
            WhatsAppThread.client_user_id == user.id,
        )
    )).scalar_one_or_none()
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")

    # FIX P1-3: liberar la sesión de get_db ANTES del stream (que usa sesiones
    # efímeras por poll · ver _stream_messages) para no agotar el pool.
    await db.close()
    return StreamingResponse(
        _stream_messages(
            thread_id, admin_role=False, request=request, project_id=project_id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@sse_router.get(
    "/admin/whatsapp/threads/{thread_id}/sse",
    dependencies=[Depends(require_owner)],
)
async def admin_whatsapp_sse(
    thread_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Admin SSE · cross-cliente threads."""
    # FIX P1-3: liberar la sesión de get_db ANTES del stream (sesiones efímeras
    # por poll · ver _stream_messages) para no agotar el pool.
    await db.close()
    return StreamingResponse(
        _stream_messages(thread_id, admin_role=True, request=request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
