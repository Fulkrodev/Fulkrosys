"""SimulacroPreEnac REST endpoints · Sesión 3B-2B.10 Phase 10.4.

Routes:
- POST /projects/{id}/simulacro-pre-enac/execute · trigger orchestrator
- GET  /projects/{id}/simulacro-pre-enac/report   · last report (no re-trigger)

R23 project-scoped admin · require_owner pool · ADR-013 sostained.
"""
from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db, set_tenant_context
from backend.app.motors.m09_audit_prep.simulacro_pre_enac_service import (
    SimulacroReport,
    run_simulacro_pre_enac,
)


router = APIRouter(tags=["Simulacro Pre-ENAC (Sesión 3B-2B.10)"])


async def _scope_project(db: AsyncSession, project_id: UUID) -> None:
    """Resolve project owner + set RLS tenant context (canonical admin pattern).

    Sin esto, las consultas del orquestador corren bajo ``fulkro_app`` con RLS
    pero sin ``app.current_project_id`` → la política filtra el proyecto → 404
    "Project not found" (bug latente · ningún spec ejecutaba el simulacro).
    Mismo patrón que m10_audit_sim (get_project_owner → set_tenant_context).
    """
    row = (await db.execute(
        sa_text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)},
    )).first()
    if row is None or row[0] is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )
    await set_tenant_context(db, client_id=row[0], project_id=project_id)


class SimulacroReportResponse(BaseModel):
    project_id: str
    executed_at: str
    overall_readiness_score: int
    total_gaps: int
    critical_gaps: int
    high_gaps: int
    coverage_pct: float
    current_phase: str
    integrity_ok: bool
    integrity_first_bad_seq: int | None
    corrective_loops_opened: int
    pdf_sha256: str
    signature_hex: str
    signed_at: str
    pdf_size_bytes: int
    loops_metadata: list[dict]


@router.post(
    "/admin/projects/{project_id}/simulacro-pre-enac/execute",
    response_model=SimulacroReportResponse,
)
async def execute_simulacro_pre_enac(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_owner),
) -> SimulacroReportResponse:
    """Execute simulacro Pre-ENAC orchestrator end-to-end."""
    await _scope_project(db, project_id)
    try:
        report: SimulacroReport = await run_simulacro_pre_enac(
            db,
            project_id,
            executor_id=current_user.id,
            usuario=current_user.email,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc),
        )
    # get_db() NO auto-commitea: sin esto, audit_log (executed+report_generated),
    # los corrective_loops y el dry-run se descartan al cerrar la sesión → GATE-7
    # (require_clean_audit_sim) bloquearía ENAC para siempre. Espejo de m10:104.
    await db.commit()
    return SimulacroReportResponse(**report.to_dict())


@router.get(
    "/admin/projects/{project_id}/simulacro-pre-enac/last-report",
    response_model=SimulacroReportResponse,
)
async def get_last_simulacro_report(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_owner),
) -> SimulacroReportResponse:
    """Retrieve last simulacro report metadata from audit_log · NO re-trigger."""
    await _scope_project(db, project_id)
    row = (await db.execute(sa_text(
        "SELECT payload_new, timestamp FROM audit_log "
        "WHERE tabla = 'simulacro_pre_enac' "
        "AND accion = 'simulacro.pre_enac.report_generated' "
        "AND project_id = :pid "
        "ORDER BY seq DESC LIMIT 1"
    ), {"pid": str(project_id)})).first()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No simulacro Pre-ENAC ejecutado todavía para este proyecto",
        )

    payload, ts = row
    payload_dict = payload if isinstance(payload, dict) else json.loads(payload)

    return SimulacroReportResponse(
        project_id=str(project_id),
        executed_at=ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
        overall_readiness_score=int(payload_dict.get("overall_score", 0) or 0),
        total_gaps=int(payload_dict.get("total_gaps", 0) or 0),
        # El service SÍ persiste estos campos en payload_new (service.py:319-321);
        # antes se devolvían hardcodeados a 0 → GATE-7 (require_clean_audit_sim)
        # no veía los gaps críticos/altos reales.
        critical_gaps=int(payload_dict.get("critical_gaps", 0) or 0),
        high_gaps=int(payload_dict.get("high_gaps", 0) or 0),
        coverage_pct=float(payload_dict.get("coverage_pct", 0.0) or 0.0),
        current_phase=str(payload_dict.get("current_phase", "") or ""),
        integrity_ok=bool(payload_dict.get("integrity_ok", False)),
        # P3 · estos cinco venian hardcodeados a vacio/cero aunque el service
        # ya tuviera el dato. Ahora el service los persiste y aqui se leen: un
        # informe firmado se recupera CON su firma, o no se recupera firmado.
        integrity_first_bad_seq=payload_dict.get("integrity_first_bad_seq"),
        corrective_loops_opened=int(payload_dict.get("loops_opened", 0) or 0),
        pdf_sha256=str(payload_dict.get("pdf_sha256", "")),
        signature_hex=str(payload_dict.get("signature_hex", "") or ""),
        signed_at=str(
            payload_dict.get("signed_at")
            or (ts.isoformat() if hasattr(ts, "isoformat") else ts)
        ),
        pdf_size_bytes=int(payload_dict.get("pdf_size_bytes", 0) or 0),
        loops_metadata=list(payload_dict.get("loops_metadata") or []),
    )
