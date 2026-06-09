"""SSE stream cliente con audience filtering (1.D.G.C v3.11).

GET /api/v1/client-portal/projects/{project_id}/events

Reusa SSE dispatcher singleton pero filtra events per audience:
- Cliente recibe step_completed (cuando admin terminó · primary_actor=admin)
- Cliente recibe step_unblocked (cuando le toca · primary_actor=cliente)
- Cliente recibe step_blocked (cuando le bloquea · primary_actor=cliente)
- Cliente NO recibe readiness_changed / phase_changed / alert_new (admin-internal)

Auth: get_current_client_user (ADR-013 cliente pool).

Verifica ownership: project_id pertenece al client del session user.
"""
from __future__ import annotations

import asyncio
import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from backend.app.core.sse_dispatcher import event_matches_audience, sse_dispatcher
from backend.app.database import get_db
from backend.app.models.client_portal import ClientUser
from backend.app.motors.m21_portal_cliente.api import get_current_client_user


router = APIRouter()

_HEARTBEAT_INTERVAL_SECONDS = 30


async def _verify_client_owns_project(
    db: AsyncSession, client_user: ClientUser, project_id: UUID,
) -> None:
    """Verify project_id pertenece al client del user · 403 si no."""
    result = await db.execute(
        text(
            "SELECT 1 FROM projects "
            "WHERE id = :pid AND client_id = :cid AND deleted_at IS NULL"
        ),
        {"pid": str(project_id), "cid": str(client_user.client_id)},
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Project not owned by client",
        )


@router.get(
    "/client-portal/projects/{project_id}/events",
    summary="SSE stream cliente · events filtered per audience (1.D.G.C v3.11)",
)
async def client_project_events_stream(
    project_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    client_user: ClientUser = Depends(get_current_client_user),
):
    """Stream cliente-facing SSE events.

    Cliente recibe SOLO eventos relevantes (filtrados via event_matches_audience).
    Admin-internal events (readiness_changed · phase_changed · alert_new) NO leak.

    Frontend hook: useClientProjectEvents (TanStack Query invalidation pattern).
    """
    await _verify_client_owns_project(db, client_user, project_id)

    # Anti SSE pool-exhaustion (auditoría 2026-06-07): FastAPI cachea Depends(get_db)
    # → global auth + get_current_client_user + este endpoint comparten UNA sola
    # sesión. El stream es long-lived y el generador SOLO usa el dispatcher en
    # memoria (no DB), así que liberamos la conexión al pool ANTES de streamear.
    # get_db.finally hará close() de nuevo (idempotente). Sin esto, ~pool_size
    # clientes SSE agotaban el pool y tumbaban la app.
    await db.close()

    channel = f"project:{project_id}"
    last_event_id = request.headers.get("last-event-id")

    async def event_generator():
        sub_iter = sse_dispatcher.subscribe(channel, last_event_id=last_event_id)
        try:
            while True:
                if await request.is_disconnected():
                    break

                try:
                    event = await asyncio.wait_for(
                        sub_iter.__anext__(),
                        timeout=_HEARTBEAT_INTERVAL_SECONDS,
                    )
                except asyncio.TimeoutError:
                    yield {"event": "heartbeat", "data": "ping"}
                    continue
                except StopAsyncIteration:
                    break

                # 1.D.G.C · audience filter cliente
                if not event_matches_audience(
                    event.type, "cliente", event.data,
                ):
                    continue

                yield {
                    "event": event.type,
                    "id": event.event_id,
                    "data": json.dumps(
                        {**event.data, "_timestamp": event.timestamp},
                    ),
                }
        except asyncio.CancelledError:
            pass
        finally:
            await sub_iter.aclose()

    return EventSourceResponse(event_generator())
