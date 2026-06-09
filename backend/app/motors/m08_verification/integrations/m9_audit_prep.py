"""M8 v5.1 - Integracion con M9 Audit Prep (spec §9.4).

Expone helpers para:

- ``collect_findings_for_dossier(db, project_id)`` -> findings con mapeo
  ENS listos para incluir en el dossier como seccion 13_INFORMES_TECNICOS
  y para alimentar la matriz 99.
- ``add_verification_reports_to_dossier(...)`` -> devuelve los paths de
  los DOCX/PDF de E-702/E-703/E-704 del ultimo run del proyecto para que
  el dossier_generator los copie a la carpeta correspondiente.

Es el pegamento entre el motor de verificacion y el motor de preparacion
de auditoria.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.documents import Document
from backend.app.motors.m08_verification.models import (
    VerificationFinding, VerificationRun,
)


REPORT_CODES = ("E-702", "E-703", "E-704")


async def collect_findings_for_dossier(
    db: AsyncSession, project_id: uuid.UUID,
) -> list[dict[str, Any]]:
    """Devuelve una vista dict-friendly de los findings del proyecto.

    Solo incluye findings con classification in {confirmed, probable}
    (los que aparecen en el informe). Ordenados por severity DESC,
    status (open primero).
    """
    stmt = select(VerificationFinding).where(
        VerificationFinding.project_id == project_id,
        VerificationFinding.deleted_at.is_(None),
        VerificationFinding.zfp_gate5_classification.in_(
            ("confirmed", "probable"),
        ),
    )
    findings = list((await db.execute(stmt)).scalars().all())

    sev_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    status_rank = {"open": 0, "needs_review": 1, "remediated": 2, "accepted_risk": 3, "false_positive": 4}
    findings.sort(key=lambda f: (
        sev_rank.get((f.severity or "info").lower(), 99),
        status_rank.get((f.status or "open").lower(), 99),
    ))

    out: list[dict[str, Any]] = []
    for f in findings:
        out.append({
            "id": str(f.id),
            "finding_hash": f.finding_hash,
            "title": f.title,
            "severity": f.severity,
            "classification": f.zfp_gate5_classification,
            "confidence_score": float(f.confidence_score or 0),
            "status": f.status,
            "cve_id": f.cve_id,
            "cvss_score": float(f.cvss_score) if f.cvss_score is not None else None,
            "affected_host": f.affected_host,
            "affected_port": f.affected_port,
            "ens_measures": list(f.ens_measures or []),
            "ens_primary_measure": f.ens_primary_measure,
            "mitre_techniques": list(f.mitre_techniques or []),
            "remediation_summary": f.remediation_summary or "",
            "remediated_at": (
                f.remediated_at.isoformat() if f.remediated_at else None
            ),
            "measure_code": f.ens_primary_measure,
            "hash_sha256": (f.raw_outputs[0].get("metadata", {}).get("hash", ""))
                if f.raw_outputs and isinstance(f.raw_outputs, list) and f.raw_outputs[0]
                else None,
        })
    return out


async def get_verification_report_documents(
    db: AsyncSession, project_id: uuid.UUID,
) -> list[Document]:
    """Ultimos DOCX/PDF de E-702/E-703/E-704 emitidos para el proyecto."""
    stmt = (
        select(Document)
        .where(
            Document.project_id == project_id,
            Document.deleted_at.is_(None),
            Document.template_codigo.in_(REPORT_CODES),
        )
        .order_by(Document.created_at.desc())
    )
    docs = list((await db.execute(stmt)).scalars().all())
    # Dedupe: solo el mas reciente por codigo
    seen = {}
    for d in docs:
        if d.template_codigo and d.template_codigo not in seen:
            seen[d.template_codigo] = d
    return list(seen.values())


async def has_verification_run(
    db: AsyncSession, project_id: uuid.UUID,
) -> bool:
    stmt = select(VerificationRun.id).where(
        VerificationRun.project_id == project_id,
        VerificationRun.deleted_at.is_(None),
    ).limit(1)
    return (await db.execute(stmt)).first() is not None


async def count_findings_by_measure(
    db: AsyncSession, project_id: uuid.UUID,
) -> dict[str, int]:
    """``{measure_code: count_open_findings}`` para la matriz 99 del dossier."""
    stmt = select(VerificationFinding).where(
        VerificationFinding.project_id == project_id,
        VerificationFinding.deleted_at.is_(None),
        VerificationFinding.status.in_(("open", "needs_review")),
    )
    findings = (await db.execute(stmt)).scalars().all()
    out: dict[str, int] = {}
    for f in findings:
        codes = set()
        for m in (f.ens_measures or []):
            if isinstance(m, dict) and m.get("measure"):
                codes.add(m["measure"])
            elif isinstance(m, str):
                codes.add(m)
        if f.ens_primary_measure:
            codes.add(f.ens_primary_measure)
        for c in codes:
            out[c] = out.get(c, 0) + 1
    return out
