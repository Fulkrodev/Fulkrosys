"""M8 v5.1 - Integracion con M5 Obligations (spec §9.3).

Para cada finding priorizado (severity × effort) se crea una
``Obligation`` en el plan con:

- ``titulo`` = "Remediar <severity>: <title>"
- ``descripcion`` = resumen_no_tecnico de la guia
- ``tipo_ejecucion`` = "remediacion_hallazgo"
- ``fecha_objetivo`` = SLA deadline
- ``measure_code`` = ens_primary_measure
- ``metadata_extra`` incluye finding_id, severity, effort, cve, score

Priorizacion: critical primero, luego high/medium/low; dentro de cada
severidad primero los ``quick_win`` (remediation_effort).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.ens import Obligation
from backend.app.motors.m08_verification.models import (
    VerificationFinding, VerificationRun,
)
from backend.app.motors.m08_verification.remediation.sla_calculator import (
    calculate_deadline, prioritize_findings,
)


async def create_remediation_obligations(
    db: AsyncSession,
    run_id: uuid.UUID,
    *,
    include_severities: set[str] | None = None,
) -> list[Obligation]:
    """Crea obligaciones de remediacion para los findings del run.

    Idempotente: si ya existe una obligacion con
    ``metadata_extra.finding_id == finding.id``, no la duplica.
    """
    run = await db.get(VerificationRun, run_id)
    if not run:
        raise ValueError(f"Run {run_id} no existe")

    stmt = select(VerificationFinding).where(
        VerificationFinding.run_id == run_id,
        VerificationFinding.deleted_at.is_(None),
        VerificationFinding.status.in_(("open", "needs_review")),
        VerificationFinding.zfp_gate5_classification.in_(("confirmed", "probable")),
    )
    findings = list((await db.execute(stmt)).scalars().all())
    if include_severities:
        findings = [
            f for f in findings
            if (f.severity or "info").lower() in include_severities
        ]
    findings = prioritize_findings(findings)

    # Buscar obligaciones existentes para no duplicar
    exist_stmt = select(Obligation).where(
        Obligation.project_id == run.project_id,
        Obligation.tipo_ejecucion == "remediacion_hallazgo",
    )
    existing = (await db.execute(exist_stmt)).scalars().all()
    seen_finding_ids = {
        (o.metadata_extra or {}).get("finding_id") for o in existing
    }

    created: list[Obligation] = []
    for f in findings:
        if str(f.id) in seen_finding_ids:
            continue
        sla = calculate_deadline(f.severity, f.created_at or datetime.now(timezone.utc))
        titulo = f"Remediar {f.severity.upper()}: {f.title}"[:200]
        ob = Obligation(
            project_id=run.project_id,
            descripcion=(
                f.remediation_summary or f.description or titulo
            )[:4000],
            tipo_ejecucion="remediacion_hallazgo",
            entregable_esperado="Evidencia de remediacion + re-test OK",
            responsable=f.affected_host,  # hint — el RSEG asigna luego
            modo_ejecucion="manual",
            estado="pendiente",
            fecha_objetivo=sla.deadline.date(),
            measure_code=f.ens_primary_measure,
            titulo=titulo,
            entregable_tipo="retest_verification",
            metadata_extra={
                "finding_id": str(f.id),
                "run_id": str(run.id),
                "severity": f.severity,
                "effort": f.remediation_effort,
                "cve_id": f.cve_id,
                "confidence_score": float(f.confidence_score or 0),
                "sla_hours": sla.hours_total,
            },
            fuente_normativa={
                "origin": "m08_verification_v5.1",
                "ens_measures": list(f.ens_measures or []),
            },
        )
        db.add(ob)
        created.append(ob)

    await db.flush()
    return created
