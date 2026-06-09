"""DLQ admin REST endpoints · Sesión 3B-2B.11 Ejecutable 6 Phase 11.3.

Routes (R23 admin top-level legitimate cross-cliente · ADR-013 require_owner pool):
- GET  /admin/notifications/dlq                      list entries paginated
- GET  /admin/notifications/dlq/summary              count breakdown widget
- POST /admin/notifications/dlq/{event_id}/reprocess re-queue dispatch
- POST /admin/notifications/dlq/{event_id}/resolve   mark resolved soft-delete
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db
from backend.app.notifications.dlq_service import (
    DlqEntry,
    DlqSummary,
    get_dlq_summary,
    list_dlq_entries,
    reprocess_dlq_entry,
    resolve_dlq_entry,
)


router = APIRouter(tags=["Notifications DLQ (Sesión 3B-2B.11)"])


class DlqEntryResponse(BaseModel):
    event_id: str
    event_type: str
    recipient_email: str
    project_id: str | None
    status: str
    retry_count: int
    error: str | None
    channels_attempted: list
    channels_failed: list
    template_used: str | None
    created_at: str
    updated_at: str


class DlqListResponse(BaseModel):
    items: list[DlqEntryResponse]
    count: int


class DlqSummaryResponse(BaseModel):
    total_count: int
    last_24h_count: int
    by_event_type: dict[str, int]


class DlqResolveBody(BaseModel):
    resolution_note: str = Field(min_length=1, max_length=500)


class DlqActionResponse(BaseModel):
    success: bool
    rows_affected: int = 0
    reason: str | None = None


@router.get(
    "/admin/notifications/dlq",
    response_model=DlqListResponse,
)
async def list_dlq(
    project_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_owner),
) -> DlqListResponse:
    """List failed notification events con retry_count >= MAX_RETRIES."""
    entries: list[DlqEntry] = await list_dlq_entries(
        db, project_id=project_id, limit=limit, offset=offset,
    )
    return DlqListResponse(
        items=[DlqEntryResponse(**e.to_dict()) for e in entries],
        count=len(entries),
    )


@router.get(
    "/admin/notifications/dlq/summary",
    response_model=DlqSummaryResponse,
)
async def dlq_summary(
    project_id: UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_owner),
) -> DlqSummaryResponse:
    """Admin dashboard widget summary count + 24h delta + breakdown by type."""
    summary: DlqSummary = await get_dlq_summary(db, project_id=project_id)
    return DlqSummaryResponse(**summary.to_dict())


@router.post(
    "/admin/notifications/dlq/{event_id}/reprocess",
    response_model=DlqActionResponse,
)
async def reprocess(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_owner),
) -> DlqActionResponse:
    """Re-queue dispatch · resets retry_count to 0 + status='queued'.

    Atomic UPDATE protects concurrent reprocess race (WHERE guard).
    """
    result = await reprocess_dlq_entry(
        db, event_id, usuario=current_user.email,
    )
    if not result["reprocessed"] and result.get("reason") == "not_found":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="DLQ entry not found",
        )
    return DlqActionResponse(
        success=result["reprocessed"],
        rows_affected=result.get("rows_affected", 0),
        reason=result.get("reason"),
    )


@router.post(
    "/admin/notifications/dlq/{event_id}/resolve",
    response_model=DlqActionResponse,
)
async def resolve(
    event_id: UUID,
    body: DlqResolveBody,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_owner),
) -> DlqActionResponse:
    """Mark DLQ entry as resolved manual · soft-delete with resolution_note."""
    result = await resolve_dlq_entry(
        db, event_id,
        resolution_note=body.resolution_note,
        usuario=current_user.email,
    )
    if not result["resolved"] and result.get("reason") == "not_found":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="DLQ entry not found",
        )
    return DlqActionResponse(
        success=result["resolved"],
        rows_affected=result.get("rows_affected", 0),
        reason=result.get("reason"),
    )
