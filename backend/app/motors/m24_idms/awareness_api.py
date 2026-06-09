"""Awareness training API · SAN-C MB-11.5.

Endpoints
---------
- POST /api/v1/projects/{id}/awareness/sessions · schedule sesión
- GET  /api/v1/projects/{id}/awareness/sessions · lista sesiones
- POST /api/v1/awareness/sessions/{sid}/attendance · record attendance
- GET  /api/v1/projects/{id}/awareness/coverage?expected={n}&window_days={d}

Wire-up frontend (ADR-034): frontend/lib/admin-awareness/api.ts +
AwarenessPanel.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.models.awareness import AwarenessSession
from backend.app.models.core import Project
from backend.app.motors.m24_idms.awareness_tracker import (
    calculate_coverage,
    list_sessions,
    record_attendance,
    schedule_session,
)

router = APIRouter(tags=["M24 - Awareness training (MB-11.5)"])


class SessionCreate(BaseModel):
    title: str = Field(..., max_length=200)
    scheduled_date: datetime
    topics: Optional[list[str]] = None
    mandatory: bool = True


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    scheduled_date: datetime
    topics: Optional[list[str]] = None
    mandatory: bool
    completed_at: Optional[datetime] = None


class AttendanceCreate(BaseModel):
    attendee_email: str = Field(..., max_length=200)
    method: str  # in_person | virtual | recorded
    magic_link_token: Optional[str] = Field(None, max_length=100)


class AttendanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    session_id: uuid.UUID
    attendee_email: str
    method: str
    attended_at: datetime


class CoverageResponse(BaseModel):
    unique_attendees: int
    expected_attendees: int
    coverage_pct: float
    window_start: str


async def _ensure_project_exists(db: AsyncSession, project_id: uuid.UUID) -> None:
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(404, "Project not found")


@router.post(
    "/projects/{project_id}/awareness/sessions",
    response_model=SessionResponse,
    status_code=201,
)
async def post_schedule_session(
    project_id: uuid.UUID,
    body: SessionCreate,
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    await _ensure_project_exists(db, project_id)
    s = await schedule_session(
        db,
        project_id=project_id,
        title=body.title,
        scheduled_date=body.scheduled_date,
        topics=body.topics,
        mandatory=body.mandatory,
    )
    await db.commit()
    return SessionResponse.model_validate(s)


@router.get(
    "/projects/{project_id}/awareness/sessions",
    response_model=list[SessionResponse],
)
async def get_sessions(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[SessionResponse]:
    await _ensure_project_exists(db, project_id)
    sessions = await list_sessions(db, project_id)
    return [SessionResponse.model_validate(s) for s in sessions]


@router.post(
    "/awareness/sessions/{session_id}/attendance",
    response_model=AttendanceResponse,
    status_code=201,
)
async def post_record_attendance(
    session_id: uuid.UUID,
    body: AttendanceCreate,
    db: AsyncSession = Depends(get_db),
) -> AttendanceResponse:
    aware_session = await db.get(AwarenessSession, session_id)
    if aware_session is None:
        raise HTTPException(404, "Awareness session not found")
    try:
        attendance = await record_attendance(
            db,
            session_id=session_id,
            attendee_email=body.attendee_email,
            method=body.method,
            magic_link_token=body.magic_link_token,
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    await db.commit()
    return AttendanceResponse.model_validate(attendance)


@router.get(
    "/projects/{project_id}/awareness/coverage",
    response_model=CoverageResponse,
)
async def get_coverage(
    project_id: uuid.UUID,
    expected: int = Query(..., gt=0, description="Empleados esperados (denominador)"),
    window_days: int = Query(365, gt=0, le=3650),
    db: AsyncSession = Depends(get_db),
) -> CoverageResponse:
    await _ensure_project_exists(db, project_id)
    return CoverageResponse(
        **await calculate_coverage(
            db,
            project_id=project_id,
            expected_attendees=expected,
            window_days=window_days,
        )
    )
