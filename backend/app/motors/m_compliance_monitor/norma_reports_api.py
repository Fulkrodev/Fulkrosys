"""Admin API for per-norma compliance reports (mini-atom 3).

Endpoints under ``/api/v1/admin/compliance/norma-reports``:

- GET  /              · list every registered plugin + latest score
- GET  /{norma_key}   · history (paginated) of reports for one norma
- GET  /{norma_key}/latest · latest report (md + json + score)
- POST /{norma_key}/run   · trigger an ad-hoc report generation
- POST /reviewed/{id}     · mark a report as reviewed (notes optional)
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db
from backend.app.models.auth import User
from backend.app.models.compliance_norma_reports import (
    FulkroComplianceNormaReport,
)
from backend.app.motors.m_compliance_monitor.norma_reports_service import (
    ComplianceNormaReportsService,
    NormaNotRegisteredError,
)
from backend.app.motors.m_compliance_monitor.normas import NormaRegistry


router = APIRouter(
    prefix="/admin/compliance/norma-reports",
    tags=["MB-9.bis mini-atom 3 — Norma reports"],
    dependencies=[Depends(require_owner)],
)


# ── Schemas ────────────────────────────────────────────────────────────


class NormaSummaryOut(BaseModel):
    norma_key: str
    norma_name: str
    regulatory_basis_url: str
    frequency: str
    priority: str
    checks_owned: list[str]
    latest_score: float | None
    latest_status: str | None
    latest_generated_at: datetime | None


class NormaReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    norma_key: str
    norma_name: str
    period_start: datetime
    period_end: datetime
    compliance_score: float
    status: str
    checks_total: int
    checks_passed: int
    checks_warning: int
    checks_failed: int
    generated_at: datetime
    storage_path_dev: str | None
    storage_path_prod: str | None
    email_sent_at: datetime | None
    reviewed_by_marcos_at: datetime | None
    reviewed_marcos_notes: str | None


class NormaReportDetailOut(NormaReportOut):
    report_md_content: str
    report_json_content: dict[str, Any]


class ReviewBody(BaseModel):
    notes: str | None = Field(default=None, max_length=4000)


# ── Endpoints ──────────────────────────────────────────────────────────


@router.get("", response_model=list[NormaSummaryOut])
async def list_normas(db: AsyncSession = Depends(get_db)) -> list[NormaSummaryOut]:
    """Plugin registry summary + latest score per norma."""
    svc = ComplianceNormaReportsService(db)
    latest = await svc.latest_per_norma()
    out: list[NormaSummaryOut] = []
    for module in NormaRegistry.get_all():
        row = latest.get(module.norma_key)
        out.append(
            NormaSummaryOut(
                norma_key=module.norma_key,
                norma_name=module.norma_name,
                regulatory_basis_url=module.regulatory_basis_url,
                frequency=module.frequency,
                priority=module.priority,
                checks_owned=list(module.checks_owned),
                latest_score=float(row.compliance_score) if row else None,
                latest_status=row.status if row else None,
                latest_generated_at=row.generated_at if row else None,
            )
        )
    return out


@router.get("/{norma_key}", response_model=list[NormaReportOut])
async def get_norma_history(
    norma_key: str,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=24, le=200),
) -> list[NormaReportOut]:
    rows = (
        await db.execute(
            select(FulkroComplianceNormaReport)
            .where(FulkroComplianceNormaReport.norma_key == norma_key)
            .order_by(desc(FulkroComplianceNormaReport.generated_at))
            .limit(limit)
        )
    ).scalars().all()
    return [NormaReportOut.model_validate(r) for r in rows]


@router.get("/{norma_key}/latest", response_model=NormaReportDetailOut)
async def get_norma_latest(
    norma_key: str, db: AsyncSession = Depends(get_db)
) -> NormaReportDetailOut:
    row = (
        await db.execute(
            select(FulkroComplianceNormaReport)
            .where(FulkroComplianceNormaReport.norma_key == norma_key)
            .order_by(desc(FulkroComplianceNormaReport.generated_at))
            .limit(1)
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"No reports yet for {norma_key}",
        )
    return NormaReportDetailOut.model_validate(row)


@router.post(
    "/{norma_key}/run",
    response_model=NormaReportDetailOut,
    status_code=status.HTTP_201_CREATED,
)
async def run_norma_report(
    norma_key: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_owner),
) -> NormaReportDetailOut:
    """Trigger an ad-hoc report generation for one norma."""
    svc = ComplianceNormaReportsService(db)
    try:
        row = await svc.generate_report(norma_key)
    except NormaNotRegisteredError:
        raise HTTPException(
            status_code=404,
            detail=f"Norma not registered: {norma_key}",
        )
    # #J-GAP1 (#49) · R6 dogfooding: trazar la generación de reporte de norma en
    # audit_log (antes esta acción no se auto-trazaba · cierra el lazo R7).
    from backend.app.motors.m_compliance_monitor.api import _emit_monitor_audit
    await _emit_monitor_audit(
        db,
        tabla="fulkro_compliance_norma_reports",
        registro_id=row.id,
        accion="compliance.norma_report.run",
        usuario=user.email or str(user.id),
        payload={"norma_key": norma_key, "report_id": str(row.id)},
    )
    await db.commit()
    return NormaReportDetailOut.model_validate(row)


@router.post("/reviewed/{report_id}", response_model=NormaReportOut)
async def mark_reviewed(
    report_id: UUID,
    body: ReviewBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_owner),
) -> NormaReportOut:
    row = (
        await db.execute(
            select(FulkroComplianceNormaReport).where(
                FulkroComplianceNormaReport.id == report_id
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, detail="Report not found")
    row.reviewed_by_marcos_at = datetime.now(timezone.utc)
    row.reviewed_marcos_notes = body.notes
    await db.flush()
    # #J-GAP1 (#49) · R6 dogfooding: trazar la revisión por Marcos en audit_log.
    from backend.app.motors.m_compliance_monitor.api import _emit_monitor_audit
    await _emit_monitor_audit(
        db,
        tabla="fulkro_compliance_norma_reports",
        registro_id=row.id,
        accion="compliance.norma_report.reviewed",
        usuario=user.email or str(user.id),
        payload={"report_id": str(row.id)},
    )
    await db.commit()
    return NormaReportOut.model_validate(row)
