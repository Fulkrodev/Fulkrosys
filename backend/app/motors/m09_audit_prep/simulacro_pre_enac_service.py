"""SimulacroPreEnacService · orchestrator delgado · pure functional.

Sesión 3B-2B.10 Ejecutable 5 Phase 10.3 (2026-05-27).

Composes 5 existing services + 2 nuevos para ejecutar simulacro Pre-ENAC
end-to-end · ~80 LOC orchestrator + return SimulacroReport.

Pipeline:
  1. AuditDryRunService.execute_dry_run (M10 + A11 senior layer · existing)
  2. compute_dda_evidence_gaps (m09 Phase C3 · existing)
  3. compute_workflow_state(role_filter='admin') (m11 Phase 1D · existing)
  4. check_audit_log_integrity (Phase 10.1 NEW · R6 verify)
  5. open_loop_for_gap per critical/high gap (Phase 10.2 NEW)
  6. generate_draft_audit_report(title_override='Simulacro Pre-ENAC') (existing)

audit_log emit Sub-atom 5.A 3-way OR:
  - simulacro.pre_enac.executed (entry point)
  - simulacro.pre_enac.report_generated (final · post-PDF)
  - audit.integrity.checked (Phase 10.1 helper)
  - corrective.loop.opened (Phase 10.2 per gap)

OPS-026 DRY · reuse 78% existing infrastructure · only orchestrator + 2 helpers nuevos.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from typing import Optional

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agents.services.audit_dry_run_service import AuditDryRunService
from backend.app.motors.m09_audit_prep.audit_events import (
    SIMULACRO_PRE_ENAC_EXECUTED,
    SIMULACRO_PRE_ENAC_REPORT_GENERATED,
)
from backend.app.motors.m09_audit_prep.audit_log_integrity_checker import (
    IntegrityReport,
    check_audit_log_integrity,
)
from backend.app.motors.m09_audit_prep.corrective_loop_service import (
    LoopState,
    open_loop_for_gap,
)
from backend.app.motors.m09_audit_prep.dda_evidence_gap_service import (
    DdaEvidenceGapMatrix,
    GapStatus,
    compute_dda_evidence_gaps,
)
from backend.app.motors.m09_audit_prep.draft_report_generator import (
    DraftReportBytes,
    DraftReportOptions,
    generate_draft_audit_report,
)
from backend.app.motors.m11_copiloto.workflow_state_scanner import (
    WorkflowScannerOptions,
    WorkflowState,
    compute_workflow_state,
)


@dataclass
class SimulacroReport:
    """End-to-end simulacro Pre-ENAC report · JSON-serializable.

    Composes outputs de 5 existing services + 2 nuevos · summary metadata.
    """

    project_id: str
    executed_at: str
    overall_readiness_score: int  # 0-100 from dry-run
    total_gaps: int
    critical_gaps: int
    high_gaps: int
    coverage_pct: float  # DdA evidence coverage
    current_phase: str  # workflow phase
    integrity_ok: bool  # audit_log hash chain integrity
    integrity_first_bad_seq: Optional[int]
    corrective_loops_opened: int
    pdf_sha256: str
    signature_hex: str
    signed_at: str
    pdf_size_bytes: int
    loops_metadata: list[dict] = field(default_factory=list)
    # F7 (FRENTE F): resumen del último vuln-scan/pentest interno (evidencia
    # mp.s.2) · convierte el simulacro en consumidor real del motor M8.
    pentest_summary: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


async def compute_pentest_summary(
    db: AsyncSession, project_id: uuid.UUID,
) -> dict:
    """F7 (FRENTE F) · resumen del ÚLTIMO run de verificación (M8) para el
    simulacro/dossier. Evidencia de mp.s.2 (vuln-scan) · pura (raw SQL).

    nota_honesta: en ALTA el pentest debe ser de un tercero EXTERNO
    INDEPENDIENTE · este escaneo COMPLEMENTA, no sustituye (PE-3 · Marcos).
    """
    run = (await db.execute(sa_text(
        "SELECT id, status, mode, category, total_findings, confirmed_findings, "
        "critical_count, high_count, completed_at FROM verification_runs "
        "WHERE project_id = :pid AND deleted_at IS NULL "
        "ORDER BY created_at DESC LIMIT 1"
    ), {"pid": str(project_id)})).mappings().first()

    nota = (
        "Vuln-scan/pentest interno de Fulkro (evidencia mp.s.2). En categoría "
        "ALTA el pentest debe realizarlo un tercero EXTERNO INDEPENDIENTE; este "
        "escaneo COMPLEMENTA (continuo / pre-auditoría / endurecimiento), NO "
        "sustituye al externo en ALTA."
    )
    if run is None:
        return {"has_run": False, "nota_honesta": nota,
                "note": "Sin escaneo de verificación ejecutado todavía."}

    measures = (await db.execute(sa_text(
        "SELECT DISTINCT ens_primary_measure FROM verification_findings "
        "WHERE run_id = :rid AND ens_primary_measure IS NOT NULL "
        "AND deleted_at IS NULL"
    ), {"rid": str(run["id"])})).scalars().all()

    return {
        "has_run": True,
        "last_run_id": str(run["id"]),
        "status": run["status"],
        "mode": run["mode"],
        "category": run["category"],
        "total_findings": int(run["total_findings"] or 0),
        "confirmed_findings": int(run["confirmed_findings"] or 0),
        "critical_count": int(run["critical_count"] or 0),
        "high_count": int(run["high_count"] or 0),
        "ens_measures_hit": sorted([m for m in measures if m]),
        "completed_at": (
            run["completed_at"].isoformat() if run["completed_at"] else None
        ),
        "nota_honesta": nota,
    }


async def _resolve_client_id(
    db: AsyncSession, project_id: uuid.UUID,
) -> Optional[uuid.UUID]:
    """Lookup client_id from projects table · None si project not found."""
    row = (await db.execute(sa_text(
        "SELECT client_id FROM projects WHERE id = :pid"
    ), {"pid": str(project_id)})).first()
    return row[0] if row else None


async def _emit_simulacro_event(
    db: AsyncSession,
    *,
    accion: str,
    project_id: uuid.UUID,
    client_id: Optional[uuid.UUID],
    payload: dict,
    usuario: Optional[str] = None,
) -> None:
    """audit_log emit Sub-atom 5.A 3-way OR."""
    await db.execute(sa_text(
        "INSERT INTO audit_log (id, tabla, registro_id, accion, usuario, "
        "project_id, client_id, payload_new, timestamp) "
        "VALUES (gen_random_uuid(), 'simulacro_pre_enac', :rid, "
        ":accion, :user, :pid, :cid, :payload, now())"
    ), {
        "rid": str(project_id),
        "accion": accion,
        "user": usuario or "system",
        "pid": str(project_id),
        "cid": str(client_id) if client_id else None,
        "payload": json.dumps(payload),
    })


async def run_simulacro_pre_enac(
    db: AsyncSession,
    project_id: uuid.UUID,
    *,
    executor_id: Optional[uuid.UUID] = None,
    usuario: Optional[str] = None,
) -> SimulacroReport:
    """Execute simulacro Pre-ENAC end-to-end · returns SimulacroReport.

    Args:
        db: AsyncSession
        project_id: target project
        executor_id: admin actor (audit trail)
        usuario: audit_log usuario string

    Returns:
        SimulacroReport con dry-run + gap matrix + workflow + integrity +
        corrective loops + signed PDF metadata.
    """
    client_id = await _resolve_client_id(db, project_id)

    await _emit_simulacro_event(
        db,
        accion=SIMULACRO_PRE_ENAC_EXECUTED,
        project_id=project_id,
        client_id=client_id,
        payload={"executor_id": str(executor_id) if executor_id else None},
        usuario=usuario,
    )

    dry_run_service = AuditDryRunService(db)
    dry_run_result = await dry_run_service.execute_dry_run(
        project_id, executor_id=executor_id,
    )

    gap_matrix: DdaEvidenceGapMatrix = await compute_dda_evidence_gaps(
        db, project_id,
    )

    workflow_state: WorkflowState = await compute_workflow_state(
        db, project_id, WorkflowScannerOptions(role_filter="admin"),
    )

    integrity: IntegrityReport = await check_audit_log_integrity(
        db, project_id=project_id,
    )

    loops_opened: list[LoopState] = []
    for medida in gap_matrix.medidas:
        if medida.status not in (GapStatus.MISSING, GapStatus.PARTIAL):
            continue
        if medida.severity not in ("critical", "high"):
            continue
        loop = await open_loop_for_gap(
            db,
            project_id,
            gap_id=medida.medida_code,
            gap_type="dda_evidence_gap",
            severity=str(medida.severity),
            client_id=client_id,
            metadata={"simulacro": True, "min_required": medida.min_required},
            usuario=usuario,
        )
        loops_opened.append(loop)

    draft_options = DraftReportOptions(
        recommendation=None,
        auditor_name="Simulacro Pre-ENAC",
    )
    report_bytes: DraftReportBytes = await generate_draft_audit_report(
        db, project_id, options=draft_options,
    )

    overall_score = int(getattr(dry_run_result, "overall_readiness_score", 0) or 0)
    total_gaps = (
        gap_matrix.total_missing + gap_matrix.total_partial
    )
    severity_summary = gap_matrix.severity_summary
    # FIX P0-2: GapSeveritySummary expone critical_missing/high_partial (NO
    # critical_count/high_count) → el getattr caía SIEMPRE al default 0, dejando
    # GATE-7 (workflow_gates.clean_audit_sim) ciego: permitía solicitar auditoría
    # ENAC / firmar la Declaración de Conformidad con NC mayores abiertas. Leer
    # los atributos reales para que el conteo persistido en audit_log sea veraz.
    critical_gaps = int(getattr(severity_summary, "critical_missing", 0) or 0)
    high_gaps = int(getattr(severity_summary, "high_partial", 0) or 0)

    # F7 (FRENTE F): el simulacro consume el último vuln-scan/pentest (mp.s.2).
    pentest_summary = await compute_pentest_summary(db, project_id)

    simulacro_report = SimulacroReport(
        project_id=str(project_id),
        executed_at=report_bytes.signed_at,
        overall_readiness_score=overall_score,
        total_gaps=total_gaps,
        critical_gaps=critical_gaps,
        high_gaps=high_gaps,
        coverage_pct=gap_matrix.coverage_pct,
        current_phase=workflow_state.current_phase,
        integrity_ok=integrity.ok,
        integrity_first_bad_seq=integrity.first_bad_seq,
        corrective_loops_opened=len(loops_opened),
        pdf_sha256=report_bytes.pdf_sha256,
        signature_hex=report_bytes.signature_hex,
        signed_at=report_bytes.signed_at,
        pdf_size_bytes=len(report_bytes.pdf_bytes),
        loops_metadata=[
            {
                "loop_id": l.loop_id,
                "gap_id": l.gap_id,
                "severity": l.severity,
            }
            for l in loops_opened
        ],
        pentest_summary=pentest_summary,
    )

    await _emit_simulacro_event(
        db,
        accion=SIMULACRO_PRE_ENAC_REPORT_GENERATED,
        project_id=project_id,
        client_id=client_id,
        payload={
            "pdf_sha256": report_bytes.pdf_sha256,
            "overall_score": overall_score,
            "total_gaps": total_gaps,
            # #42 (FRENTE D): persistir los conteos REALES de NC (no hardcodear
            # 0) para que GATE-7 require_clean_audit_sim lea las NC mayores del
            # JSONB del último simulacro.
            "critical_gaps": critical_gaps,
            "high_gaps": high_gaps,
            "coverage_pct": gap_matrix.coverage_pct,
            "corrective_loops_opened": len(loops_opened),
            "loops_opened": len(loops_opened),
            "integrity_ok": integrity.ok,
        },
        usuario=usuario,
    )

    return simulacro_report
