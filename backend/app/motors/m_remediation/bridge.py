"""Puente diagnóstico/pentest → remediación (FASE 3 · ADR-055).

Convierte los CloudGaps abiertos de un proyecto (detectados por el motor de
diagnóstico cloud y/o surgidos del pentest) en RemediationJobs PROPUESTOS, sin
ejecutarlos. La ejecución queda gateada por la aprobación de un clic
(FASE 4 · proponer→aprobar→ejecutar). NUNCA propone acciones BLOCKED.

Determinista (R1): el mapeo (provider, medida ENS, tipo de recurso) → action_type
se deriva del catálogo canónico ACTION_CATALOG, sin LLM. Idempotente: no
re-propone si ya hay un job vivo o exitoso para el mismo (gap, acción).
"""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy import text as _sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m_cloud_connectors.models import CloudGap
from backend.app.motors.m_remediation.catalog import (
    ACTION_CATALOG,
    RemediationActionSpec,
    RemediationTier,
)
from backend.app.motors.m_remediation.models import (
    RemediationJob,
    RemediationJobStatus,
    RemediationSourceKind,
)
from backend.app.motors.m_remediation.service import RemediationService


# Estados que indican que un job sigue vivo o ya cerró bien → NO re-proponer.
# (FAILED / ROLLED_BACK sí permiten re-proponer en una pasada posterior.)
_NON_REPROPOSABLE = frozenset({
    RemediationJobStatus.QUEUED.value,
    RemediationJobStatus.AWAITING_AUTHORIZATION.value,
    RemediationJobStatus.BLOCKED.value,
    RemediationJobStatus.SKIPPED_COMPLIANT.value,
    RemediationJobStatus.PREFLIGHT.value,
    RemediationJobStatus.SNAPSHOTTING.value,
    RemediationJobStatus.APPLYING.value,
    RemediationJobStatus.VERIFYING.value,
    RemediationJobStatus.SUCCEEDED.value,
})


def build_gap_action_index() -> dict[tuple[str, str], list[RemediationActionSpec]]:
    """Índice inverso del catálogo: (provider, medida ENS) → [acciones].

    Excluye BLOCKED (nunca auto-propuestas). Ordena SAFE_AUTO primero para que,
    ante colisión (p.ej. M365 op.acc.6 = MFA report-only + enforce), se proponga
    por defecto la variante reversible de menor impacto."""
    idx: dict[tuple[str, str], list[RemediationActionSpec]] = {}
    for spec in ACTION_CATALOG.values():
        if spec.tier == RemediationTier.BLOCKED:
            continue
        for measure in spec.ens_measures:
            idx.setdefault((spec.provider, measure), []).append(spec)
    for key in idx:
        idx[key].sort(
            key=lambda s: 0 if s.tier == RemediationTier.SAFE_AUTO else 1
        )
    return idx


_INDEX = build_gap_action_index()


def map_gap_to_action_type(
    provider: str,
    ens_measure_code: str,
    resource_type: Optional[str] = None,
) -> Optional[str]:
    """Resuelve el action_type del catálogo para un gap (determinista).

    Empareja por (provider, medida ENS); si hay varias acciones y se conoce el
    tipo de recurso, prefiere la cuyo target_kind concuerda; si no, la primera
    (SAFE_AUTO preferida). None si el catálogo no cubre ese gap (→ guía manual)."""
    candidates = _INDEX.get((provider, ens_measure_code))
    if not candidates:
        return None
    if resource_type:
        rt = resource_type.lower()
        for spec in candidates:
            tk = spec.target_kind.lower()
            if rt in tk or tk.endswith(rt) or rt.endswith(tk.split(".")[-1]):
                return spec.action_type
    return candidates[0].action_type


async def _connector_provider(
    db: AsyncSession, connector_id: uuid.UUID,
) -> Optional[str]:
    return (
        await db.execute(
            _sa_text("SELECT provider FROM cloud_connectors WHERE id = :cid"),
            {"cid": str(connector_id)},
        )
    ).scalar()


async def propose_remediations_for_project(
    db: AsyncSession,
    project_id: uuid.UUID,
    *,
    created_by_user_id: uuid.UUID | None = None,
    client_id: uuid.UUID | None = None,
) -> dict:
    """Crea RemediationJobs PROPUESTOS desde los CloudGaps abiertos del proyecto.

    NO ejecuta nada (la ejecución requiere aprobación · FASE 4). Idempotente.
    El llamador DEBE haber fijado el tenant context RLS (cloud_gaps tiene RLS).

    Returns: {"created": [...jobs...], "skipped": [{gap_id, reason}], "total_gaps": n}
    """
    gaps = (
        await db.execute(
            select(CloudGap).where(
                CloudGap.project_id == project_id,
                CloudGap.resolved_at.is_(None),
            )
        )
    ).scalars().all()

    svc = RemediationService(db)
    created: list[dict] = []
    skipped: list[dict] = []

    for gap in gaps:
        if gap.connector_id is None:
            skipped.append({"gap_id": str(gap.id), "reason": "gap sin conector"})
            continue
        provider = await _connector_provider(db, gap.connector_id)
        if not provider:
            skipped.append({"gap_id": str(gap.id), "reason": "conector no resuelto"})
            continue
        raw = gap.raw_evidence or {}
        resource_type = raw.get("resource_type") or raw.get("asset_type")
        action_type = map_gap_to_action_type(
            provider, gap.ens_measure_code, resource_type,
        )
        if not action_type:
            skipped.append({
                "gap_id": str(gap.id),
                "reason": (
                    f"sin acción de catálogo para {provider}/"
                    f"{gap.ens_measure_code} (→ guía manual)"
                ),
            })
            continue
        # Idempotencia: no re-proponer si ya hay job vivo/exitoso para gap+acción.
        existing = (
            await db.execute(
                select(RemediationJob.id).where(
                    RemediationJob.source_gap_id == gap.id,
                    RemediationJob.action_type == action_type,
                    RemediationJob.status.in_(_NON_REPROPOSABLE),
                ).limit(1)
            )
        ).scalar()
        if existing:
            skipped.append({"gap_id": str(gap.id), "reason": "job ya propuesto"})
            continue
        target_ref = (
            raw.get("resource_external_id")
            or raw.get("asset_name")
            or raw.get("resource_name")
            or gap.title
        )
        job = await svc.create_job(
            project_id=project_id,
            action_type=action_type,
            source_kind=RemediationSourceKind.CLOUD_GAP,
            source_gap_id=gap.id,
            connector_id=gap.connector_id,
            target_ref=str(target_ref)[:200] if target_ref else None,
            created_by_user_id=created_by_user_id,
            client_id=client_id,
        )
        created.append({
            "job_id": str(job.id),
            "gap_id": str(gap.id),
            "action_type": action_type,
            "tier": job.tier,
            "status": job.status,
            "ens_measure_code": gap.ens_measure_code,
            "severity": gap.severity,
        })

    return {
        "created": created,
        "skipped": skipped,
        "total_gaps": len(gaps),
    }


async def propose_remediations_from_findings(
    db: AsyncSession,
    project_id: uuid.UUID,
    *,
    created_by_user_id: uuid.UUID | None = None,
    client_id: uuid.UUID | None = None,
) -> dict:
    """Crea RemediationJobs PROPUESTOS desde los VerificationFindings (host) del
    proyecto · §6 cierra el puente pentest→remediación (antes sólo CloudGap, los
    findings de host nunca llegaban a remediación → 100% manual).

    Sólo findings 'open' verificados (zfp_gate5_classification confirmed/probable)
    con medida ENS primaria. Mapea (host, medida ENS) → action_type del catálogo
    (provider='host'). NO ejecuta (requiere aprobación · FASE 4). Idempotente por
    (source_finding_id, action_type). El llamador fija el tenant context RLS.

    Returns: {"created": [...], "skipped": [...], "total_findings": n}
    """
    from backend.app.motors.m08_verification.models import VerificationFinding

    findings = (
        await db.execute(
            select(VerificationFinding).where(
                VerificationFinding.project_id == project_id,
                VerificationFinding.status == "open",
                VerificationFinding.zfp_gate5_classification.in_(
                    ("confirmed", "probable"),
                ),
                VerificationFinding.ens_primary_measure.isnot(None),
            )
        )
    ).scalars().all()

    svc = RemediationService(db)
    created: list[dict] = []
    skipped: list[dict] = []

    for f in findings:
        measure = f.ens_primary_measure
        resource_type = f.affected_service or f.affected_os
        action_type = map_gap_to_action_type("host", measure, resource_type)
        if not action_type:
            skipped.append({
                "finding_id": str(f.id),
                "reason": (
                    f"sin acción de catálogo para host/{measure} (→ guía manual)"
                ),
            })
            continue
        # Idempotencia: no re-proponer si ya hay job vivo/exitoso para finding+acción.
        existing = (
            await db.execute(
                select(RemediationJob.id).where(
                    RemediationJob.source_finding_id == f.id,
                    RemediationJob.action_type == action_type,
                    RemediationJob.status.in_(_NON_REPROPOSABLE),
                ).limit(1)
            )
        ).scalar()
        if existing:
            skipped.append({"finding_id": str(f.id), "reason": "job ya propuesto"})
            continue
        job = await svc.create_job(
            project_id=project_id,
            action_type=action_type,
            source_kind=RemediationSourceKind.HOST_FINDING,
            source_finding_id=f.id,
            target_ref=str(f.affected_host)[:200] if f.affected_host else None,
            created_by_user_id=created_by_user_id,
            client_id=client_id,
        )
        created.append({
            "job_id": str(job.id),
            "finding_id": str(f.id),
            "action_type": action_type,
            "tier": job.tier,
            "status": job.status,
            "ens_measure_code": measure,
            "severity": f.severity,
        })

    return {
        "created": created,
        "skipped": skipped,
        "total_findings": len(findings),
    }
