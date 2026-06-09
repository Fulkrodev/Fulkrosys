"""BIA API · SAN-C MB-11.5.

Endpoints
---------
- POST /api/v1/projects/{id}/bia/analyses · crea entry BIA per servicio
- GET  /api/v1/projects/{id}/bia/analyses · lista entries proyecto
- GET  /api/v1/projects/{id}/bia/summary  · agregado max RTO/RPO + total impact

Wire-up frontend (ADR-034): frontend/lib/admin-bia/api.ts + BiaPanel.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.models.core import Project
from backend.app.motors.m19_risk.bia_service import (
    aggregate_bia_summary,
    create_bia_entry,
    list_bia_entries,
)

router = APIRouter(prefix="/projects", tags=["M19 - BIA (MB-11.5)"])


class BiaEntryCreate(BaseModel):
    service_name: str = Field(..., max_length=200)
    rto_hours: int = Field(..., ge=0)
    rpo_hours: int = Field(..., ge=0)
    daily_impact_eur: Optional[Decimal] = None
    stakeholders: Optional[list[str]] = None
    minimum_resources: Optional[dict] = None


class BiaEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    service_name: str
    rto_hours: int
    rpo_hours: int
    daily_impact_eur: Optional[Decimal] = None
    stakeholders: Optional[list[str]] = None
    minimum_resources: Optional[dict] = None


class BiaSummaryResponse(BaseModel):
    services_count: int
    max_rto_hours: Optional[int]
    max_rpo_hours: Optional[int]
    total_daily_impact_eur: Optional[Decimal]


async def _ensure_project_exists(db: AsyncSession, project_id: uuid.UUID) -> None:
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(404, "Project not found")


@router.post(
    "/{project_id}/bia/analyses",
    response_model=BiaEntryResponse,
    status_code=201,
)
async def post_bia_entry(
    project_id: uuid.UUID,
    body: BiaEntryCreate,
    db: AsyncSession = Depends(get_db),
) -> BiaEntryResponse:
    await _ensure_project_exists(db, project_id)
    entry = await create_bia_entry(
        db,
        project_id=project_id,
        service_name=body.service_name,
        rto_hours=body.rto_hours,
        rpo_hours=body.rpo_hours,
        daily_impact_eur=body.daily_impact_eur,
        stakeholders=body.stakeholders,
        minimum_resources=body.minimum_resources,
    )
    await db.commit()
    return BiaEntryResponse.model_validate(entry)


@router.get(
    "/{project_id}/bia/analyses",
    response_model=list[BiaEntryResponse],
)
async def get_bia_entries(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[BiaEntryResponse]:
    await _ensure_project_exists(db, project_id)
    entries = await list_bia_entries(db, project_id)
    return [BiaEntryResponse.model_validate(e) for e in entries]


@router.get(
    "/{project_id}/bia/summary",
    response_model=BiaSummaryResponse,
)
async def get_bia_summary(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> BiaSummaryResponse:
    await _ensure_project_exists(db, project_id)
    return BiaSummaryResponse(**await aggregate_bia_summary(db, project_id))
