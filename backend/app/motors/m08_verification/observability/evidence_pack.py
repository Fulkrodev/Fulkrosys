"""Pack de evidencia para auditoría ENAC (doc §16).

El superpoder de auditoría del pipeline NO es "encontrar todo", es producir
un rastro de evidencia impecable, reproducible y trazable de un proceso
riguroso. Este pack sintetiza lo que el auditor verifica (proceso, evidencia,
competencia, cierre):

| Salida | Requisito auditoría |
|--------|---------------------|
| Metodología (PTES/OWASP WSTG) | el "cómo" |
| RoE + autorización | alcance y legalidad |
| EvidenceRecord con fechas | periodicidad y cambio significativo |
| Findings mapeados Anexo II | trazabilidad a medidas |
| Cobertura % | honestidad del alcance probado |
| Estados closed/risk_accepted | remediación y riesgo aceptado |
| Delta reports | evidencia de cierre |
| run_manifest_hash + R6 verify | determinismo + integridad |
| Atestación (Gate 2) | personal cualificado (Alto) |

Devuelve un dict estructurado (renderable a PDF vía M6 downstream).
"""
from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m08_verification.finding_state_machine import FindingState
from backend.app.motors.m08_verification.gates import is_zero_fp_verified
from backend.app.motors.m08_verification.models import (
    EvidenceRecord, VerificationFinding, VerificationRun,
)

METHODOLOGY = ["PTES", "OWASP WSTG", "OSSTMM", "CCN-STIC 808/809"]


async def build_enac_evidence_pack(
    db: AsyncSession, run_id: uuid.UUID,
) -> dict[str, Any]:
    """Construye el pack de evidencia ENAC para un run."""
    run = await db.get(VerificationRun, run_id)
    if run is None:
        raise ValueError(f"VerificationRun {run_id} no existe")

    findings = list((await db.execute(
        select(VerificationFinding).where(
            VerificationFinding.run_id == run_id,
            VerificationFinding.deleted_at.is_(None),
        )
    )).scalars().all())

    # findings por medida ENS Anexo II (trazabilidad)
    by_measure: dict[str, list[dict]] = defaultdict(list)
    for f in findings:
        measure = f.ens_primary_measure or "sin_mapear"
        by_measure[measure].append({
            "finding_id": str(f.id), "title": f.title,
            "severity": f.severity, "state": f.finding_state,
            "verification_level": f.verification_level,
            "zero_fp_verified": is_zero_fp_verified(f.verification_level),
        })

    # estados de cierre
    states = defaultdict(int)
    for f in findings:
        states[f.finding_state or FindingState.DETECTED] += 1

    # evidencia append-only del run (periodicidad/trazabilidad)
    evidence = list((await db.execute(
        select(EvidenceRecord).where(EvidenceRecord.run_id == run_id)
        .order_by(EvidenceRecord.ts.asc())
    )).scalars().all())
    evidence_trail = [
        {"ts": e.ts.isoformat() if e.ts else None, "actor": e.actor,
         "action": e.action, "component": e.component,
         "ens_relevance": e.ens_relevance}
        for e in evidence
    ]

    # integridad R6 (hash chain) · prueba de no-manipulación
    try:
        chain = (await db.execute(text(
            "SELECT ok, total, first_bad_seq FROM fn_audit_log_verify_chain()"
        ))).one()
        chain_integrity = {
            "ok": bool(chain.ok), "total": int(chain.total),
            "first_bad_seq": chain.first_bad_seq,
        }
    except Exception:  # pragma: no cover
        chain_integrity = {"ok": None, "note": "verify_chain no disponible"}

    zero_fp = sum(1 for f in findings if is_zero_fp_verified(f.verification_level))

    category = (run.category or "").upper()
    gate2_required = category in ("ALTO", "ALTA")
    gate2_done = run.autopilot_status == "completed" and not gate2_required

    return {
        "run_id": str(run.id),
        "project_id": str(run.project_id),
        "categoria_ens": run.category,
        "metodologia": METHODOLOGY,
        "autorizacion": {
            "authorized_by": run.authorized_by,
            "authorization_signed_at": (
                run.authorization_signed_at.isoformat()
                if run.authorization_signed_at else None
            ),
            "ephemeral_session": str(run.ephemeral_session_id) if run.ephemeral_session_id else None,
            "ephemeral_revoked_at": (
                run.ephemeral_revoked_at.isoformat() if run.ephemeral_revoked_at else None
            ),
        },
        "determinismo": {
            "run_manifest_hash": run.run_manifest_hash,
            "golden_run_id": str(run.golden_run_id) if run.golden_run_id else None,
        },
        "cobertura": {
            "coverage_pct": float(run.coverage_pct) if run.coverage_pct is not None else 0.0,
            "assets_in_scope": run.assets_in_scope,
            "assets_scanned": run.assets_scanned,
            "partial_run": bool(run.partial_run),
            "tools_attempted": run.tools_attempted or [],
            "tools_failed": run.tools_failed or [],
        },
        "hallazgos": {
            "total": len(findings),
            "zero_fp_verified": zero_fp,
            "por_medida_ens": dict(by_measure),
            "por_estado": dict(states),
            "severidad": {
                "critical": run.critical_count or 0, "high": run.high_count or 0,
                "medium": run.medium_count or 0, "low": run.low_count or 0,
                "info": run.info_count or 0,
            },
        },
        "cierre": {
            "closed": states.get(FindingState.CLOSED, 0),
            "risk_accepted": states.get(FindingState.RISK_ACCEPTED, 0),
            "delta_new": run.delta_new or 0,
            "delta_resolved": run.delta_resolved or 0,
            "delta_persistent": run.delta_persistent or 0,
        },
        "evidence_trail": evidence_trail,
        "integridad_r6": chain_integrity,
        "gate2_atestacion": {
            "required": gate2_required,
            "status": run.autopilot_status,
            "done": gate2_done,
            "external_pentester": run.external_pentester_name,
            "cert": run.external_pentester_cert,
        },
        "disclaimer": (
            "Cobertura máxima demostrable de lo automatizable + evidencia "
            "reproducible y trazable + cierre verificado. NO garantiza ausencia "
            "de vulnerabilidades; minimiza el falso negativo y reporta la "
            "cobertura real (doc §0 honest boundaries)."
        ),
    }
