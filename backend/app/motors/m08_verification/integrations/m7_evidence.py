"""M8 v5.1 - Integracion con M7 Evidence Catalog (spec §9.1).

Para cada finding confirmado/probable se genera una evidencia Tipo E
en el catalogo de evidencias con:

- ``measure_code`` = ens_primary_measure del finding
- ``tipo`` = "verification_finding"
- ``evidence_type_id`` = "E-702" (informe tecnico) o
                          "E-704" (informe red team) si el run es external
- ``vigente`` = True, validity 180 dias desde created_at
- ``hash_sha256`` = hash del raw_output_excerpt + tool_sources
- ``metadata_extra`` incluye finding_id, severity, confidence, ZFP gates

Cuando se emite el E-702 completo, se genera una evidencia adicional
de tipo ``informe_verificacion_tecnica`` con validity 365 dias,
asociada a ``op.exp.5`` (gestion de vulnerabilidades).

Este modulo se invoca desde el report_generator tras emitir los
informes, pero tambien puede ejecutarse standalone con
``backfill_evidence_for_run(run_id)``.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.documents import Evidence
from backend.app.models.ens import EnsMeasure
from backend.app.motors.m08_verification.models import (
    VerificationFinding, VerificationRun,
)


FINDING_EVIDENCE_VALIDITY_DAYS = 180
REPORT_EVIDENCE_VALIDITY_DAYS = 365


def _finding_hash(f: VerificationFinding) -> str:
    payload = {
        "finding_hash": f.finding_hash,
        "title": f.title,
        "severity": f.severity,
        "tool_sources": list(f.tool_sources or []),
        "ens_measures": list(f.ens_measures or []),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8"),
    ).hexdigest()


async def _measure_id_for_code(
    db: AsyncSession, code: str | None,
) -> uuid.UUID | None:
    if not code:
        return None
    stmt = select(EnsMeasure.id).where(EnsMeasure.codigo == code)
    r = await db.execute(stmt)
    row = r.first()
    return row[0] if row else None


async def create_evidence_for_finding(
    db: AsyncSession, finding: VerificationFinding,
) -> Evidence | None:
    """Genera (si corresponde) la evidencia para un finding.

    Solo los findings classification in {confirmed, probable} y status
    'open' generan evidencia (vigente True). Los demas quedan fuera
    del catalogo.
    """
    if finding.zfp_gate5_classification not in ("confirmed", "probable"):
        return None
    if finding.status not in ("open", "needs_review", "remediated"):
        return None
    measure_code = finding.ens_primary_measure
    measure_id = await _measure_id_for_code(db, measure_code)

    now = datetime.now(timezone.utc)
    digest = _finding_hash(finding)
    ev = Evidence(
        project_id=finding.project_id,
        measure_id=measure_id,
        measure_code=measure_code,
        tipo="verification_finding",
        fuente="m08_verification",
        evidence_type_id="E-702",
        nombre_tipo="Hallazgo verificado (v5.1)",
        hash_sha256=digest,
        fecha_evidencia=now.date(),
        fecha_caducidad=now.date() + timedelta(days=FINDING_EVIDENCE_VALIDITY_DAYS),
        vigente=True,
        metadata_extra={
            "finding_id": str(finding.id),
            "run_id": str(finding.run_id),
            "severity": finding.severity,
            "classification": finding.zfp_gate5_classification,
            "confidence_score": float(finding.confidence_score or 0),
            "cve_id": finding.cve_id,
            "affected_host": finding.affected_host,
            "tool_sources": list(finding.tool_sources or []),
            "status": finding.status,
        },
    )
    db.add(ev)
    await db.flush()
    return ev


async def create_evidence_for_run_report(
    db: AsyncSession,
    run: VerificationRun,
    *,
    report_codigo: str = "E-702",
    docx_path: str | None = None,
    rendered_hash: str | None = None,
) -> Evidence:
    """Genera la evidencia Tipo E del informe completo (365 dias)."""
    now = datetime.now(timezone.utc)
    measure_code = "op.exp.5"
    measure_id = await _measure_id_for_code(db, measure_code)
    ev = Evidence(
        project_id=run.project_id,
        measure_id=measure_id,
        measure_code=measure_code,
        tipo="informe_verificacion_tecnica",
        fuente=f"m08_verification.{report_codigo}",
        evidence_type_id=report_codigo,
        nombre_tipo=f"Informe {report_codigo} emitido",
        fichero_path=docx_path,
        hash_sha256=rendered_hash or _finding_hash_placeholder(run),
        fecha_evidencia=now.date(),
        fecha_caducidad=now.date() + timedelta(days=REPORT_EVIDENCE_VALIDITY_DAYS),
        vigente=True,
        metadata_extra={
            "run_id": str(run.id),
            "category": run.category,
            "mode": run.mode,
            "security_score": run.security_score,
            "total_findings": run.total_findings,
            "confirmed_findings": run.confirmed_findings,
        },
    )
    db.add(ev)
    await db.flush()
    return ev


def _finding_hash_placeholder(run: VerificationRun) -> str:
    return hashlib.sha256(str(run.id).encode("utf-8")).hexdigest()


async def backfill_evidence_for_run(
    db: AsyncSession, run_id: uuid.UUID,
) -> list[Evidence]:
    """Crea evidencias para TODOS los findings del run (idempotente).

    Para evitar duplicados, salta los findings que ya tienen una
    Evidence cuyo ``metadata_extra.finding_id`` coincide.
    """
    run = await db.get(VerificationRun, run_id)
    if not run:
        raise ValueError(f"Run {run_id} no existe")
    stmt = select(VerificationFinding).where(
        VerificationFinding.run_id == run_id,
        VerificationFinding.deleted_at.is_(None),
    )
    findings = (await db.execute(stmt)).scalars().all()

    existing_stmt = select(Evidence).where(
        Evidence.project_id == run.project_id,
        Evidence.tipo == "verification_finding",
    )
    existing = (await db.execute(existing_stmt)).scalars().all()
    seen_finding_ids = {
        (e.metadata_extra or {}).get("finding_id") for e in existing
    }

    created = []
    for f in findings:
        if str(f.id) in seen_finding_ids:
            continue
        ev = await create_evidence_for_finding(db, f)
        if ev:
            created.append(ev)
    return created


async def get_findings_for_project(
    db: AsyncSession, project_id: uuid.UUID,
    *, only_open: bool = True,
) -> list[VerificationFinding]:
    """Devuelve los findings (opcionalmente solo abiertos) de un proyecto."""
    stmt = select(VerificationFinding).where(
        VerificationFinding.project_id == project_id,
        VerificationFinding.deleted_at.is_(None),
    )
    if only_open:
        stmt = stmt.where(VerificationFinding.status.in_(("open", "needs_review")))
    r = await db.execute(stmt)
    return list(r.scalars().all())
