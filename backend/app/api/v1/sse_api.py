"""Endpoint SSE stream eventos proyecto (MB-13.3 · ADR-035).

GET /api/v1/projects/{project_id}/events

Eventos emitidos:
- ``readiness_changed`` cuando cambia algún Asset/MageritThreat/
                         DdaEntry/Evidence del proyecto.
- ``phase_changed``     cuando ``projects.fase`` cambia.
- ``alert_new``         cuando AlertService.trigger_alert (MB-13.4).

Heartbeat 30s para detectar conexiones muertas. Cliente reconecta
automáticamente vía EventSource browser API.
"""
from __future__ import annotations

import asyncio
import json
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from backend.app.auth.dependencies import require_owner
from backend.app.core.sse_dispatcher import event_matches_audience, sse_dispatcher
from backend.app.database import get_db

router = APIRouter()

_HEARTBEAT_INTERVAL_SECONDS = 30


@router.get(
    "/projects/{project_id}/events",
    summary="SSE stream eventos relevantes proyecto (MB-13.3)",
)
async def project_events_stream(
    project_id: UUID,
    request: Request,
    _user=Depends(require_owner),
    db: AsyncSession = Depends(get_db),
):
    """Stream eventos SSE para refresh UI event-driven.

    Cliente recomendado: ``new EventSource('/api/v1/projects/{id}/events')``
    + listeners por tipo: ``readiness_changed`` / ``phase_changed`` /
    ``alert_new``.

    Ver ``frontend/lib/hooks/useProjectEvents.ts`` para integración
    TanStack Query (auto invalidate queries en cada evento).
    """
    # Anti SSE pool-exhaustion (auditoría 2026-06-07): libera la conexión DB
    # compartida (Depends(get_db) cacheado · global auth + require_owner) ANTES del
    # stream long-lived · el generador solo usa el dispatcher en memoria.
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

                # 1.D.G.C · admin audience filter (acepta todos · safety extension)
                if not event_matches_audience(
                    event.type, "admin", event.data,
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
