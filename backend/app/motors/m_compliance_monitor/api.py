"""Admin API for the FULKRO Self-Monitoring System (atom 9.bis.6).

All endpoints require ``require_owner`` (Marcos / future co-DPO). The
subsystem is platform-global (no tenant context), so no RLS is applied.

Endpoints
---------

GET  /admin/compliance/monitor/status         — aggregate dashboard snapshot
GET  /admin/compliance/monitor/checks         — list all 17 checks + state
POST /admin/compliance/monitor/checks/{name}/run — manually trigger one check
GET  /admin/compliance/monitor/alerts          — list alerts (filter status)
POST /admin/compliance/monitor/alerts/{id}/resolve — manual resolve
GET  /admin/compliance/monitor/reports         — list status reports
POST /admin/compliance/monitor/sync-registry   — upsert CHECK_REGISTRY rows
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db
from backend.app.models.auth import User
from backend.app.models.compliance_monitor import (
    ALERT_OPEN,
    ComplianceAlert,
    ComplianceCheck,
    ComplianceReport,
    STATUS_GREEN,
    STATUS_RED,
    STATUS_UNKNOWN,
    STATUS_YELLOW,
)
from backend.app.motors.m_compliance_monitor.checks import CHECK_REGISTRY
from backend.app.motors.m_compliance_monitor.schemas import (
    AlertOut,
    AlertResolveBody,
    CheckOut,
    CheckRunResult,
    MonitorStatusOut,
    ReportOut,
    TriggerCheckOut,
)
from backend.app.motors.m_compliance_monitor.service import (
    ComplianceMonitorService,
)


router = APIRouter(
    prefix="/admin/compliance/monitor",
    tags=["MB-9.bis atom 6 — Self-Monitoring"],
    dependencies=[Depends(require_owner)],
)


# ── GET /status ────────────────────────────────────────────────────────


@router.get("/status", response_model=MonitorStatusOut)
async def get_status(db: AsyncSession = Depends(get_db)) -> MonitorStatusOut:
    counts_row = await db.execute(
        select(ComplianceCheck.status, func.count(ComplianceCheck.id)).group_by(
            ComplianceCheck.status
        )
    )
    counts = {s: c for s, c in counts_row.all()}
    total = sum(counts.values())

    open_alerts = (
        await db.execute(
            select(func.count(ComplianceAlert.id)).where(
                ComplianceAlert.status == ALERT_OPEN
            )
        )
    ).scalar() or 0

    last_run = (
        await db.execute(select(func.max(ComplianceCheck.last_run_at)))
    ).scalar()
    last_report = (
        await db.execute(select(func.max(ComplianceReport.generated_at)))
    ).scalar()

    red = counts.get(STATUS_RED, 0)
    yellow = counts.get(STATUS_YELLOW, 0)
    unknown = counts.get(STATUS_UNKNOWN, 0)
    green = counts.get(STATUS_GREEN, 0)
    overall = (
        STATUS_RED if red > 0
        else STATUS_YELLOW if (yellow > 0 or unknown > 0)
        else STATUS_GREEN if total > 0
        else STATUS_UNKNOWN
    )

    return MonitorStatusOut(
        overall=overall,
        green=green,
        yellow=yellow,
        red=red,
        unknown=unknown,
        total=total,
        open_alerts=open_alerts,
        last_run_at=last_run,
        last_report_at=last_report,
    )


# ── GET /checks ────────────────────────────────────────────────────────


@router.get("/checks", response_model=list[CheckOut])
async def list_checks(
    db: AsyncSession = Depends(get_db),
    category: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
) -> list[CheckOut]:
    stmt = select(ComplianceCheck)
    if category:
        stmt = stmt.where(ComplianceCheck.category == category)
    if status_filter:
        stmt = stmt.where(ComplianceCheck.status == status_filter)
    rows = (await db.execute(stmt.order_by(ComplianceCheck.check_name))).scalars().all()
    return [CheckOut.model_validate(r) for r in rows]


# ── POST /checks/{name}/run ────────────────────────────────────────────


_LOGGER = logging.getLogger(__name__)

# #38 · namespace estable para derivar registro_id (UUID) de recursos sin UUID
# propio (check name, registry) · el audit_log exige registro_id UUID NOT NULL.
_MONITOR_AUDIT_NS = uuid.uuid5(uuid.NAMESPACE_DNS, "fulkro.compliance_monitor")


async def _emit_monitor_audit(
    db: AsyncSession,
    *,
    tabla: str,
    registro_id: uuid.UUID,
    accion: str,
    usuario: str,
    payload: dict | None = None,
) -> None:
    """#38 · R6 dogfooding: el monitor de compliance se auto-traza. Subsistema
    platform-global (sin tenant) → audit_log system-level (project_id/client_id
    NULL · la RLS 3-way OR de Sub-atom 5.A admite el caso NULL+NULL). In-txn (se
    commitea con la mutación) · best-effort (no rompe la operación)."""
    try:
        await db.execute(
            text(
                "INSERT INTO audit_log (id, tabla, registro_id, accion, usuario, "
                "project_id, client_id, payload_new, timestamp) "
                "VALUES (gen_random_uuid(), :tabla, :rid, :accion, :usuario, "
                "NULL, NULL, CAST(:payload AS jsonb), now())"
            ),
            {
                "tabla": tabla,
                "rid": str(registro_id),
                "accion": accion,
                "usuario": (usuario or "marcos")[:255],
                "payload": json.dumps(payload or {}),
            },
        )
    except Exception:  # pragma: no cover · best-effort
        _LOGGER.exception("#38 audit_log monitor emit failed · accion=%s", accion)


@router.post(
    "/checks/{name}/run",
    response_model=TriggerCheckOut,
    status_code=status.HTTP_200_OK,
)
async def run_check(
    name: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_owner),
) -> TriggerCheckOut:
    if name not in CHECK_REGISTRY:
        raise HTTPException(404, detail=f"Unknown check: {name}")
    svc = ComplianceMonitorService(db)
    await svc.sync_registry()
    outcome = await svc.run_check(name)
    await _emit_monitor_audit(
        db,
        tabla="compliance_checks",
        registro_id=uuid.uuid5(_MONITOR_AUDIT_NS, name),
        accion="compliance.check.run",
        usuario=user.email or str(user.id),
        payload={
            "check": name,
            "status": outcome.result.status,
            "alert_created": outcome.alert_created,
        },
    )
    await db.commit()
    return TriggerCheckOut(
        check_name=outcome.check_name,
        result=CheckRunResult(
            check_name=outcome.check_name,
            status=outcome.result.status,
            severity=outcome.result.severity,
            message=outcome.result.message,
            details=outcome.result.details,
            ran_at=datetime.now(timezone.utc),
        ),
        alert_created=outcome.alert_created,
        alert_id=outcome.alert_id,
    )


# ── GET /alerts ────────────────────────────────────────────────────────


@router.get("/alerts", response_model=list[AlertOut])
async def list_alerts(
    db: AsyncSession = Depends(get_db),
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, le=500),
) -> list[AlertOut]:
    stmt = select(ComplianceAlert).order_by(desc(ComplianceAlert.triggered_at)).limit(limit)
    if status_filter:
        stmt = stmt.where(ComplianceAlert.status == status_filter)
    rows = (await db.execute(stmt)).scalars().all()
    return [AlertOut.model_validate(r) for r in rows]


# ── POST /alerts/{id}/resolve ──────────────────────────────────────────


@router.post("/alerts/{alert_id}/resolve", response_model=AlertOut)
async def resolve_alert(
    alert_id: UUID,
    body: AlertResolveBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_owner),
) -> AlertOut:
    svc = ComplianceMonitorService(db)
    try:
        row = await svc.resolve_alert(
            alert_id,
            resolved_by=user.email or str(user.id),
            resolution_note=body.resolution_note,
        )
    except KeyError as e:
        raise HTTPException(404, detail=str(e))
    await _emit_monitor_audit(
        db,
        tabla="compliance_alerts",
        registro_id=alert_id,
        accion="compliance.alert.resolved",
        usuario=user.email or str(user.id),
        payload={"resolution_note": (body.resolution_note or "")[:500]},
    )
    await db.commit()
    return AlertOut.model_validate(row)


# ── GET /reports ───────────────────────────────────────────────────────


@router.get("/reports", response_model=list[ReportOut])
async def list_reports(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=20, le=200),
) -> list[ReportOut]:
    rows = (
        await db.execute(
            select(ComplianceReport)
            .order_by(desc(ComplianceReport.generated_at))
            .limit(limit)
        )
    ).scalars().all()
    return [ReportOut.model_validate(r) for r in rows]


# ── POST /sync-registry ────────────────────────────────────────────────


@router.post("/sync-registry")
async def sync_registry(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_owner),
) -> dict[str, int]:
    svc = ComplianceMonitorService(db)
    created = await svc.sync_registry()
    await _emit_monitor_audit(
        db,
        tabla="compliance_registry",
        registro_id=uuid.uuid5(_MONITOR_AUDIT_NS, "registry"),
        accion="compliance.registry.synced",
        usuario=user.email or str(user.id),
        payload={"created": created},
    )
    await db.commit()
    return {"created": created, "total_registered": len(CHECK_REGISTRY)}
