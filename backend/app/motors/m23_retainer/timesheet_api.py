"""Timesheet admin API · MB-7.bis atom 7.bis.5 Q6.C."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db
from backend.app.motors.m23_retainer.timesheet_service import (
    TimesheetService,
)


router = APIRouter(
    prefix="/admin/timesheet",
    tags=["admin - Marcos timesheet"],
    dependencies=[Depends(require_owner)],
)


class ManualEntryBody(BaseModel):
    client_id: uuid.UUID
    started_at: datetime
    duration_minutes: int = Field(..., ge=1, le=24 * 60)
    retainer_id: Optional[uuid.UUID] = None
    activity_id: Optional[uuid.UUID] = None
    notes: Optional[str] = Field(None, max_length=4000)


@router.get("/entries")
async def list_entries(
    client_id: Optional[uuid.UUID] = None,
    retainer_id: Optional[uuid.UUID] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> dict:
    svc = TimesheetService()
    rows = await svc.get_entries_filtered(
        db,
        client_id=client_id,
        retainer_id=retainer_id,
        since=since,
        until=until,
        limit=limit,
        offset=offset,
    )
    return {
        "items": [
            {
                "id": str(e.id),
                "client_id": str(e.client_id),
                "retainer_id": str(e.retainer_id) if e.retainer_id else None,
                "activity_id": str(e.activity_id) if e.activity_id else None,
                "started_at": e.started_at.isoformat() if e.started_at else None,
                "ended_at": e.ended_at.isoformat() if e.ended_at else None,
                "duration_minutes": e.duration_minutes,
                "source": e.source,
                "manual_override": e.manual_override,
                "endpoint_path": e.endpoint_path,
                "notes": e.notes,
            }
            for e in rows
        ],
        "limit": limit,
        "offset": offset,
    }


@router.post("/manual-entry", status_code=201)
async def add_manual_entry(
    body: ManualEntryBody,
    db: AsyncSession = Depends(get_db),
) -> dict:
    svc = TimesheetService()
    entry = await svc.add_manual_entry(
        db,
        client_id=body.client_id,
        started_at=body.started_at,
        duration_minutes=body.duration_minutes,
        retainer_id=body.retainer_id,
        activity_id=body.activity_id,
        notes=body.notes,
    )
    await db.commit()
    return {
        "id": str(entry.id),
        "client_id": str(entry.client_id),
        "duration_minutes": entry.duration_minutes,
        "source": entry.source,
    }


@router.get("/summary")
async def summary(db: AsyncSession = Depends(get_db)) -> dict:
    """Returns monthly total + top 3 clients by hours."""
    svc = TimesheetService()
    minutes = await svc.get_monthly_total_minutes(db)
    top = await svc.get_top_clients_by_hours(db, limit=3)
    return {
        "monthly_total_minutes": minutes,
        "monthly_total_hours": round(minutes / 60, 1),
        "top_clients": [
            {
                "client_id": c.client_id,
                "client_name": c.client_name,
                "total_minutes": c.total_minutes,
            }
            for c in top
        ],
    }
