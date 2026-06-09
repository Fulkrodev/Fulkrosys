"""Motor Meetings — API endpoints (sub-bloque 7.A.4).

Endpoints `/api/v1/admin/meetings` con `require_owner` router-level
(M-Marcos pool admin-only).

Endpoints (10 total):
  POST   ""                       create_meeting
  GET    ""                       list_meetings (filters)
  GET    /search                  search FTS GIN español
  GET    /by-client/{client_id}   vista histórica + interlocutor JOIN
  GET    /{meeting_id}            detail + interlocutor mini-card
  PATCH  /{meeting_id}            update partial pre-completion
  POST   /{meeting_id}/complete   notes + duration + auto-log M30
  POST   /{meeting_id}/cancel     idempotente
  POST   /{meeting_id}/sse-init   genera sse_session_id
  POST   /{meeting_id}/post-action 4 acciones cross-motor (stub 7.A.6)
  DELETE /{meeting_id}            soft delete (delegated cancel)

Pattern uniform commit() pre return (5.5.F.0).
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db
from backend.app.motors.m_meetings.schemas import (
    MeetingCancel,
    MeetingComplete,
    MeetingCreate,
    MeetingDetail,
    MeetingListItem,
    MeetingPostActionRequest,
    MeetingPostActionResponse,
    MeetingSearchResult,
    MeetingStatus,
    MeetingUpdate,
    SSEStartResponse,
)
from backend.app.motors.m_meetings.service import (
    MeetingNotFoundError,
    MeetingService,
    MeetingStateError,
)


router = APIRouter(
    prefix="/admin/meetings",
    tags=["Meetings (FASE 7) - Reuniones externas"],
    dependencies=[Depends(require_owner)],
)


# ────────────────────────────────────────────────────────────────────
# CRUD
# ────────────────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=MeetingDetail,
    status_code=status.HTTP_201_CREATED,
)
async def create_meeting_endpoint(
    payload: MeetingCreate,
    db: AsyncSession = Depends(get_db),
) -> MeetingDetail:
    """Crea meeting en estado 'scheduled'."""
    svc = MeetingService(db)
    meeting = await svc.create_meeting(payload)
    detail = await svc.build_detail(meeting)
    await db.commit()
    return detail


@router.get(
    "",
    response_model=list[MeetingListItem],
)
async def list_meetings_endpoint(
    client_id: Annotated[uuid.UUID | None, Query()] = None,
    project_id: Annotated[uuid.UUID | None, Query()] = None,
    meeting_status: Annotated[MeetingStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    db: AsyncSession = Depends(get_db),
) -> list[MeetingListItem]:
    """Lista meetings con filtros."""
    svc = MeetingService(db)
    if client_id is not None:
        # Vista histórica con JOIN interlocutor
        return await svc.get_meetings_by_client(client_id, limit=limit)
    meetings = await svc.list_meetings(
        client_id=None,
        project_id=project_id,
        status=meeting_status,
        limit=limit,
    )
    # Map sin JOIN (interlocutor_name=None)
    return [
        MeetingListItem(
            id=m.id,
            client_id=m.client_id,
            project_id=m.project_id,
            title=m.title,
            platform=m.platform,
            etapa_k=m.etapa_k,
            interlocutor_contact_id=m.interlocutor_contact_id,
            interlocutor_name=None,
            meeting_date=m.meeting_date,
            status=m.status,
            duration_minutes=m.duration_minutes,
            has_notes=bool(m.notes_markdown),
        )
        for m in meetings
    ]


@router.get(
    "/search",
    response_model=list[MeetingSearchResult],
)
async def search_meetings_endpoint(
    q: Annotated[str, Query(min_length=1, max_length=500)],
    client_id: Annotated[uuid.UUID | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    db: AsyncSession = Depends(get_db),
) -> list[MeetingSearchResult]:
    """Full-text search GIN español sobre notes_markdown."""
    svc = MeetingService(db)
    return await svc.search_meetings_fts(
        query=q, client_id=client_id, limit=limit,
    )


@router.get(
    "/by-client/{client_id}",
    response_model=list[MeetingListItem],
)
async def by_client_endpoint(
    client_id: uuid.UUID,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    db: AsyncSession = Depends(get_db),
) -> list[MeetingListItem]:
    """Vista histórica meetings cliente con interlocutor JOIN resolved."""
    svc = MeetingService(db)
    return await svc.get_meetings_by_client(client_id, limit=limit)


@router.get(
    "/{meeting_id}",
    response_model=MeetingDetail,
)
async def get_meeting_endpoint(
    meeting_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> MeetingDetail:
    """Detail meeting + interlocutor mini-card M30."""
    svc = MeetingService(db)
    try:
        meeting = await svc.get_meeting_by_id(meeting_id)
    except MeetingNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc),
        )
    return await svc.build_detail(meeting)


@router.patch(
    "/{meeting_id}",
    response_model=MeetingDetail,
)
async def update_meeting_endpoint(
    meeting_id: uuid.UUID,
    payload: MeetingUpdate,
    db: AsyncSession = Depends(get_db),
) -> MeetingDetail:
    """PATCH partial pre-completion (no permite si completed/cancelled)."""
    svc = MeetingService(db)
    try:
        meeting = await svc.update_meeting(meeting_id, payload)
    except MeetingNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc),
        )
    except MeetingStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc),
        )
    detail = await svc.build_detail(meeting)
    await db.commit()
    return detail


# ────────────────────────────────────────────────────────────────────
# WORKFLOW transitions
# ────────────────────────────────────────────────────────────────────


@router.post(
    "/{meeting_id}/complete",
    response_model=MeetingDetail,
)
async def complete_meeting_endpoint(
    meeting_id: uuid.UUID,
    payload: MeetingComplete,
    db: AsyncSession = Depends(get_db),
) -> MeetingDetail:
    """Completa meeting: notes + status + auto-log M30 cross-motor."""
    svc = MeetingService(db)
    try:
        meeting = await svc.complete_meeting(meeting_id, payload)
    except MeetingNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc),
        )
    except MeetingStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc),
        )
    detail = await svc.build_detail(meeting)
    await db.commit()
    return detail


@router.post(
    "/{meeting_id}/cancel",
    response_model=MeetingDetail,
)
async def cancel_meeting_endpoint(
    meeting_id: uuid.UUID,
    payload: MeetingCancel,
    db: AsyncSession = Depends(get_db),
) -> MeetingDetail:
    """Cancela meeting (idempotente)."""
    svc = MeetingService(db)
    try:
        meeting = await svc.cancel_meeting(meeting_id, payload)
    except MeetingNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc),
        )
    except MeetingStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc),
        )
    detail = await svc.build_detail(meeting)
    await db.commit()
    return detail


@router.post(
    "/{meeting_id}/sse-init",
    response_model=SSEStartResponse,
)
async def sse_init_endpoint(
    meeting_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> SSEStartResponse:
    """Genera sse_session_id (idempotente) para A18 stream."""
    svc = MeetingService(db)
    try:
        resp = await svc.init_sse_session(meeting_id)
    except MeetingNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc),
        )
    await db.commit()
    return resp


# ────────────────────────────────────────────────────────────────────
# POST-MEETING ACTIONS (wiring detail en 7.A.6)
# ────────────────────────────────────────────────────────────────────


@router.post(
    "/{meeting_id}/post-action",
    response_model=MeetingPostActionResponse,
)
async def post_action_endpoint(
    meeting_id: uuid.UUID,
    payload: MeetingPostActionRequest,
    db: AsyncSession = Depends(get_db),
) -> MeetingPostActionResponse:
    """Dispatch 4 acciones cross-motor post-meeting.

    Action types (wiring en 7.A.6 actions.py):
      - propuesta → A19 RedactorPropuestasAgent
      - create_project → core projects service
      - k6_signature → M12 magic link FIRMA_DOCUMENTO
      - email_summary → EmailSender consolidado
    """
    svc = MeetingService(db)
    try:
        meeting = await svc.get_meeting_by_id(meeting_id)
    except MeetingNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc),
        )

    from backend.app.motors.m_meetings.actions import dispatch_post_action

    response = await dispatch_post_action(db, meeting, payload)
    await db.commit()
    return response


# ────────────────────────────────────────────────────────────────────
# DELETE (soft via cancel)
# ────────────────────────────────────────────────────────────────────


@router.delete(
    "/{meeting_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def soft_delete_meeting_endpoint(
    meeting_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft delete delegated a cancel_meeting con reason='admin_delete'."""
    svc = MeetingService(db)
    try:
        await svc.soft_delete_meeting(meeting_id)
    except MeetingNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc),
        )
    await db.commit()
