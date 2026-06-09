"""Métricas de observabilidad M8 (doc §12).

- Cobertura% (métrica de honestidad clave · "¿lo probasteis todo?").
- FP-rate post-gate4 (calidad del pipeline · solo sobre lo verificado).
- MTTR por severidad (tiempo medio de remediación · venta de velocidad).
- Tendencia de hallazgos (últimos N runs).
- Drift de determinismo (manifest hashes distintos entre runs).
- Salud del pipeline (runs parciales/fallidos).

Agregados ON-QUERY (ADR-025 · sin tabla de métricas nueva).
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m08_verification.finding_state_machine import FindingState
from backend.app.motors.m08_verification.gates import ZERO_FP_LEVELS
from backend.app.motors.m08_verification.models import (
    VerificationFinding, VerificationRun,
)


async def compute_observability_metrics(
    db: AsyncSession, project_id: uuid.UUID,
) -> dict[str, Any]:
    """Calcula el cuadro de métricas de observabilidad para un proyecto."""
    # ── último run + cobertura ──
    last_run = (await db.execute(
        select(VerificationRun)
        .where(
            VerificationRun.project_id == project_id,
            VerificationRun.deleted_at.is_(None),
        )
        .order_by(VerificationRun.created_at.desc())
        .limit(1)
    )).scalar_one_or_none()
    coverage = {
        "coverage_pct": float(last_run.coverage_pct) if last_run and last_run.coverage_pct is not None else 0.0,
        "assets_in_scope": last_run.assets_in_scope if last_run else 0,
        "assets_scanned": last_run.assets_scanned if last_run else 0,
        "partial_run": bool(last_run.partial_run) if last_run else None,
        "run_id": str(last_run.id) if last_run else None,
        "autopilot_status": last_run.autopilot_status if last_run else None,
    }

    # ── FP-rate post-gate4 (solo hallazgos verificados activamente) ──
    post_gate4_stmt = select(func.count()).select_from(VerificationFinding).where(
        VerificationFinding.project_id == project_id,
        VerificationFinding.deleted_at.is_(None),
        VerificationFinding.verification_level.in_(tuple(ZERO_FP_LEVELS)),
    )
    post_gate4 = (await db.execute(post_gate4_stmt)).scalar() or 0
    fp_stmt = post_gate4_stmt.where(
        VerificationFinding.finding_state == FindingState.FALSE_POSITIVE,
    )
    fp_count = (await db.execute(fp_stmt)).scalar() or 0
    fp_rate = round(fp_count / post_gate4, 4) if post_gate4 else 0.0

    # ── MTTR por severidad (remediated_at - created_at) ──
    secs = func.extract(
        "epoch", VerificationFinding.remediated_at - VerificationFinding.created_at,
    )
    mttr_rows = (await db.execute(
        select(VerificationFinding.severity, func.avg(secs))
        .where(
            VerificationFinding.project_id == project_id,
            VerificationFinding.deleted_at.is_(None),
            VerificationFinding.remediated_at.isnot(None),
        )
        .group_by(VerificationFinding.severity)
    )).all()
    mttr_by_severity = {
        sev: round(float(avg) / 3600.0, 2) if avg is not None else None
        for sev, avg in mttr_rows
    }

    # ── tendencia (últimos 10 runs) ──
    trend_rows = (await db.execute(
        select(
            VerificationRun.id, VerificationRun.completed_at,
            VerificationRun.total_findings, VerificationRun.critical_count,
            VerificationRun.high_count, VerificationRun.run_manifest_hash,
        )
        .where(
            VerificationRun.project_id == project_id,
            VerificationRun.deleted_at.is_(None),
        )
        .order_by(VerificationRun.created_at.desc())
        .limit(10)
    )).all()
    trend = [
        {
            "run_id": str(r.id),
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            "total": r.total_findings or 0,
            "critical": r.critical_count or 0,
            "high": r.high_count or 0,
        }
        for r in reversed(trend_rows)
    ]

    # ── drift de determinismo (manifest hashes distintos) ──
    manifests = [r.run_manifest_hash for r in trend_rows if r.run_manifest_hash]
    drift = {
        "runs_with_manifest": len(manifests),
        "distinct_manifests": len(set(manifests)),
        "drift_detected": len(set(manifests)) > 1,
    }

    # ── salud del pipeline ──
    total_runs = (await db.execute(
        select(func.count()).select_from(VerificationRun).where(
            VerificationRun.project_id == project_id,
            VerificationRun.deleted_at.is_(None),
        )
    )).scalar() or 0
    partial_runs = (await db.execute(
        select(func.count()).select_from(VerificationRun).where(
            VerificationRun.project_id == project_id,
            VerificationRun.deleted_at.is_(None),
            VerificationRun.partial_run.is_(True),
        )
    )).scalar() or 0
    failed_runs = (await db.execute(
        select(func.count()).select_from(VerificationRun).where(
            VerificationRun.project_id == project_id,
            VerificationRun.deleted_at.is_(None),
            VerificationRun.autopilot_status == "failed",
        )
    )).scalar() or 0
    pipeline_health = {
        "total_runs": total_runs,
        "partial_runs": partial_runs,
        "failed_runs": failed_runs,
        "partial_rate": round(partial_runs / total_runs, 4) if total_runs else 0.0,
        "failed_rate": round(failed_runs / total_runs, 4) if total_runs else 0.0,
    }

    return {
        "coverage": coverage,
        "fp_rate_post_gate4": fp_rate,
        "fp_post_gate4_total": post_gate4,
        "mttr_hours_by_severity": mttr_by_severity,
        "finding_trend": trend,
        "determinism_drift": drift,
        "pipeline_health": pipeline_health,
    }
