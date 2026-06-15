"""A21 Detector Discrepancias · REST API endpoints (MB-8.A.2).

4 endpoints project-scoped expuestos en `/api/v1/a21`:
- POST   /projects/{id}/a21/scan                → triggers scan
- GET    /projects/{id}/a21/scans               → lista últimas N runs
- GET    /projects/{id}/a21/discrepancies       → lista con filtros
- PATCH  /projects/{id}/a21/discrepancies/{did}/resolve → workflow status

RLS via _set_project_rls (replica pattern m27 conformity api_paso5).
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agents.agent_21_service import DiscrepancyDetectorService
from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db


# Endpoints admin (Marcos-only) · mirror agents/api.py (bug-hunt 2026-06-14):
# evita abuso de coste/operación por client_user. El _set_project_rls() interno
# sólo valida existencia (404), NO autoriza al usuario.
router = APIRouter(
    tags=["Agent 21 - Detector Discrepancias"],
    dependencies=[Depends(require_owner)],
)


async def _set_project_rls(
    project_id: uuid.UUID, db: AsyncSession,
) -> uuid.UUID:
    cid = (await db.execute(
        sa_text("SELECT get_project_owner(:pid)"),
        {"pid": str(project_id)},
    )).scalar()
    if not cid:
        raise HTTPException(404, "Project not found")
    return cid


# ════════════════════════════════════════════════════════════════════
# Schemas
# ════════════════════════════════════════════════════════════════════


class ScanRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    project_id: uuid.UUID
    run_status: str
    motors_scanned: list[str]
    discrepancies_found: int
    started_at: str | None = None
    completed_at: str | None = None
    error_message: str | None = None


class DiscrepancyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    scan_run_id: uuid.UUID
    project_id: uuid.UUID
    discrepancy_type: str
    severity: str
    motor_a: str
    motor_b: str
    description: str
    evidence_a: dict
    evidence_b: dict
    resolution_status: str
    resolution_notes: str | None = None
    resolved_at: str | None = None
    created_at: str | None = None


class ResolveDiscrepancyBody(BaseModel):
    new_status: str = Field(..., description="acknowledged | resolved | dismissed | open")
    notes: str | None = Field(None, max_length=2000)


# ════════════════════════════════════════════════════════════════════
# Endpoints
# ════════════════════════════════════════════════════════════════════


@router.post(
    "/projects/{project_id}/a21/scan",
    response_model=ScanRunOut,
)
async def trigger_scan(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ScanRunOut:
    """Marcos triggerea scan A21 manual."""
    await _set_project_rls(project_id, db)
    svc = DiscrepancyDetectorService()
    try:
        run = await svc.scan_project(db, project_id)
    except Exception as exc:
        raise HTTPException(500, f"Scan failed: {exc}")
    await db.commit()
    return ScanRunOut.model_validate(_serialize_run(run))


@router.get(
    "/projects/{project_id}/a21/scans",
    response_model=list[ScanRunOut],
)
async def list_scans(
    project_id: uuid.UUID,
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[ScanRunOut]:
    await _set_project_rls(project_id, db)
    svc = DiscrepancyDetectorService()
    runs = await svc.list_scan_runs(db, project_id, limit=limit)
    return [ScanRunOut.model_validate(_serialize_run(r)) for r in runs]


@router.get(
    "/projects/{project_id}/a21/discrepancies",
    response_model=list[DiscrepancyOut],
)
async def list_discrepancies(
    project_id: uuid.UUID,
    resolution_status: str | None = Query(None),
    severity: str | None = Query(None),
    scan_run_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> list[DiscrepancyOut]:
    await _set_project_rls(project_id, db)
    svc = DiscrepancyDetectorService()
    rows = await svc.list_discrepancies(
        db, project_id,
        resolution_status=resolution_status,
        severity=severity,
        scan_run_id=scan_run_id,
    )
    return [DiscrepancyOut.model_validate(_serialize_disc(d)) for d in rows]


@router.patch(
    "/projects/{project_id}/a21/discrepancies/{discrepancy_id}/resolve",
    response_model=DiscrepancyOut,
)
async def resolve_discrepancy(
    project_id: uuid.UUID,
    discrepancy_id: uuid.UUID,
    body: ResolveDiscrepancyBody,
    db: AsyncSession = Depends(get_db),
) -> DiscrepancyOut:
    await _set_project_rls(project_id, db)
    svc = DiscrepancyDetectorService()
    try:
        disc = await svc.resolve_discrepancy(
            db, project_id, discrepancy_id,
            new_status=body.new_status,
            notes=body.notes,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    await db.commit()
    return DiscrepancyOut.model_validate(_serialize_disc(disc))


# ════════════════════════════════════════════════════════════════════
# Serializers (avoid datetime str coercion issues in Pydantic v2)
# ════════════════════════════════════════════════════════════════════


def _serialize_run(run) -> dict:
    return {
        "id": run.id,
        "project_id": run.project_id,
        "run_status": run.run_status,
        "motors_scanned": list(run.motors_scanned or []),
        "discrepancies_found": run.discrepancies_found,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "error_message": run.error_message,
    }


def _serialize_disc(disc) -> dict:
    return {
        "id": disc.id,
        "scan_run_id": disc.scan_run_id,
        "project_id": disc.project_id,
        "discrepancy_type": disc.discrepancy_type,
        "severity": disc.severity,
        "motor_a": disc.motor_a,
        "motor_b": disc.motor_b,
        "description": disc.description,
        "evidence_a": disc.evidence_a or {},
        "evidence_b": disc.evidence_b or {},
        "resolution_status": disc.resolution_status,
        "resolution_notes": disc.resolution_notes,
        "resolved_at": disc.resolved_at.isoformat() if disc.resolved_at else None,
        "created_at": disc.created_at.isoformat() if disc.created_at else None,
    }
