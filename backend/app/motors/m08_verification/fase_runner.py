"""F1 (FRENTE F) · orquestador interno de fases del vuln-scan/pentest (M8).

Compone los bloques canónicos EXISTENTES — **NO** reusa ``vuln_orchestrator``
(DEPRECADO #19 · rompería su test guard):

    scope (ya derivado en create_run) → scan (runners · SIMULADO si
    USE_MCP_REAL=false · binarios reales en Hetzner) → run_zfp_pipeline
    (5 gates) → persist VerificationFinding (+ EnsMapper) → counters → completed.

Fail-closed: cada sub-fase corre en try/except · si una falla, se registra y el
run NO se marca 'completed' (queda en la fase alcanzada · honesto). Kill-switch:
si ``cancel_requested_at`` != NULL aborta a 'cancelled'.

PE-3 (decisión Marcos 2026-06-06): esto es CÓDIGO + ORQUESTACIÓN + SIMULACIÓN,
cerrado y testeable sin binarios. La ejecución REAL de binarios
(``USE_MCP_REAL=true`` contra el sistema de semillas) es **validación de DEPLOY**
(Hetzner FASE J · F14-DEPLOY) · PUERTA DURA antes del pentest de un cliente real.
Regla ALTA intacta: el motor cubre vuln-scan MEDIA (obligatorio) + pentest
opcional MEDIA + pre-chequeo continuo · ALTA exige pentester EXTERNO
INDEPENDIENTE · este motor COMPLEMENTA, no sustituye.
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Awaitable, Callable, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m08_verification.ens_mapper import EnsMapper
from backend.app.motors.m08_verification.models import (
    VerificationFinding,
    VerificationRun,
)
from backend.app.motors.m08_verification.tools.base import FindingCandidate
from backend.app.motors.m08_verification.zfp_engine import (
    ZfpFinding,
    run_zfp_pipeline,
)

logger = logging.getLogger(__name__)

# candidate_provider: async (run) -> list[FindingCandidate]
CandidateProvider = Callable[[VerificationRun], Awaitable[list[FindingCandidate]]]

_EMPTY_COUNTS = {
    "total": 0, "confirmed": 0,
    "critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0,
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def use_mcp_real() -> bool:
    """DEC-6: defaults False en dev/test son prod-safe (no bug). En Hetzner se
    activa USE_MCP_REAL=true + credenciales scanner."""
    return os.environ.get("USE_MCP_REAL", "").strip().lower() in {"1", "true", "yes"}


async def _default_scan_phase(run: VerificationRun) -> list[FindingCandidate]:
    """Fase de escaneo por defecto.

    USE_MCP_REAL=false (dev/test · prod-safe): NO hay objetivos reales → devuelve
    [] (honesto · no inventa hallazgos). USE_MCP_REAL=true (Hetzner): invocaría
    los runners reales contra el scope · validación-real pendiente de deploy (PE-3).
    """
    if not use_mcp_real():
        logger.info(
            "fase_runner: USE_MCP_REAL=false · scan simulado (0 candidates) "
            "· run=%s", run.id,
        )
        return []
    logger.warning(
        "fase_runner: USE_MCP_REAL=true · invocación real de runners · "
        "validación-real pendiente deploy Hetzner (F14-DEPLOY) · run=%s", run.id,
    )
    # Cableado deploy-time: nuclei/openvas/... → parse_output → FindingCandidate.
    # Se valida contra el sistema de semillas en Hetzner (PE-3 · F14-DEPLOY).
    return []


def _zfp_to_finding(
    run: VerificationRun,
    zf: ZfpFinding,
    ens_measures: list,
    ens_primary: Optional[str],
) -> VerificationFinding:
    """Mapea un ZfpFinding (post-5-gates) a una fila VerificationFinding (F2)."""
    cls = zf.zfp_gate5_classification
    # status CHECK: open|remediated|accepted_risk|false_positive|needs_review
    status = "needs_review" if cls == "needs_review" else "open"
    return VerificationFinding(
        project_id=run.project_id,
        run_id=run.id,
        finding_hash=zf.finding_hash,
        title=zf.title,
        description=zf.description,
        severity=zf.severity,
        status=status,
        cvss_score=zf.cvss_score,
        cvss_vector=zf.cvss_vector,
        cve_id=zf.cve_id,
        cwe_id=zf.cwe_id,
        affected_host=zf.affected_host,
        affected_port=zf.affected_port,
        affected_service=zf.affected_service,
        affected_service_version=zf.affected_service_version,
        affected_url=zf.affected_url,
        affected_os=zf.affected_os,
        tool_sources=zf.tool_sources,
        raw_outputs=zf.raw_outputs,
        confidence_score=zf.confidence_score,
        zfp_gate1_dedup=zf.zfp_gate1_dedup,
        zfp_gate2_fp_filter=zf.zfp_gate2_fp_filter,
        zfp_gate3_cross_tool=zf.zfp_gate3_cross_tool,
        zfp_gate4_retest=zf.zfp_gate4_retest,
        zfp_gate5_classification=cls,
        ens_measures=ens_measures or [],
        ens_primary_measure=ens_primary,
        # Baseline determinista · la curación detallada la añade el
        # remediation_orchestrator (bajo aprobación cliente · ADR-014).
        remediation_summary=(
            f"Remediación pendiente de curación · revisar "
            f"{ens_primary or 'la medida ENS aplicable'} · {zf.title}"
        )[:500],
    )


async def _persist_findings(
    db: AsyncSession, run: VerificationRun, kept: list[ZfpFinding],
) -> dict:
    """F2 · persiste ZfpFinding → VerificationFinding + ENS map determinista."""
    mapper = EnsMapper(db, enable_llm=False)  # determinista en la base
    counts = dict(_EMPTY_COUNTS)
    for zf in kept:
        try:
            ens_measures, ens_primary = await mapper.map(zf)
        except Exception as exc:  # noqa: BLE001 — ENS map best-effort
            logger.warning("fase_runner: ENS map falló · %s", exc)
            ens_measures, ens_primary = [], None
        db.add(_zfp_to_finding(run, zf, ens_measures, ens_primary))
        counts["total"] += 1
        if zf.zfp_gate5_classification == "confirmed":
            counts["confirmed"] += 1
        if zf.severity in counts:
            counts[zf.severity] += 1
    await db.flush()
    return counts


async def run_fases(
    db: AsyncSession,
    run_id: uuid.UUID,
    *,
    candidate_provider: Optional[CandidateProvider] = None,
    retest_callback=None,
    enable_llm_capa3_retest: bool = False,
) -> dict:
    """Orquesta el run end-to-end. Keystone que destapa #38/#39 (F1).

    ``candidate_provider`` permite inyectar candidatos (tests/seeds F8 + futuros
    consumidores) · por defecto usa ``_default_scan_phase`` (gateado USE_MCP_REAL).
    """
    run = await db.get(VerificationRun, run_id)
    if run is None:
        raise ValueError(f"VerificationRun {run_id} no encontrado")

    # Kill-switch pre-check (Marcos pulsó kill antes de arrancar).
    if run.cancel_requested_at is not None:
        run.status = "cancelled"
        run.cancel_completed_at = _now()
        await db.flush()
        return {"run_id": str(run_id), "status": "cancelled", "reason": "kill_switch"}

    failures: list[dict] = []

    # ── Fase 1 · scan ────────────────────────────────────────────────
    run.status = "phase1_running"
    run.phase1_started_at = _now()
    await db.flush()
    candidates: list[FindingCandidate] = []
    try:
        provider = candidate_provider or _default_scan_phase
        candidates = await provider(run)
    except Exception as exc:  # noqa: BLE001 — fail-closed
        failures.append({"fase": "scan", "error": str(exc)})
        logger.exception("fase_runner: fase scan falló · run=%s", run_id)
    run.phase1_completed_at = _now()
    await db.flush()

    # ── Fase 3 · ZFP (5 gates) ───────────────────────────────────────
    run.status = "phase3_validating"
    run.phase3_started_at = _now()
    await db.flush()
    kept: list[ZfpFinding] = []
    rejected: list[ZfpFinding] = []
    try:
        kept, rejected = await run_zfp_pipeline(
            db, candidates,
            retest_callback=retest_callback,
            enable_llm_capa3_retest=enable_llm_capa3_retest,
        )
    except Exception as exc:  # noqa: BLE001 — fail-closed
        failures.append({"fase": "zfp", "error": str(exc)})
        logger.exception("fase_runner: fase zfp falló · run=%s", run_id)

    # ── persist + counters (F2) ──────────────────────────────────────
    counts = dict(_EMPTY_COUNTS)
    try:
        counts = await _persist_findings(db, run, kept)
        run.total_findings = counts["total"]
        run.confirmed_findings = counts["confirmed"]
        run.critical_count = counts["critical"]
        run.high_count = counts["high"]
        run.medium_count = counts["medium"]
        run.low_count = counts["low"]
        run.info_count = counts["info"]
        run.tools_used = sorted({t for zf in kept for t in zf.tool_sources})
    except Exception as exc:  # noqa: BLE001 — fail-closed
        failures.append({"fase": "persist", "error": str(exc)})
        logger.exception("fase_runner: fase persist falló · run=%s", run_id)

    # ── estado final ─────────────────────────────────────────────────
    if failures:
        # Fail-closed: NO se marca 'completed' · queda en phase3_validating.
        await db.flush()
        return {
            "run_id": str(run_id),
            "status": run.status,
            "partial": True,
            "failures": failures,
            "candidates": len(candidates),
            "findings_persisted": counts["total"],
            "rejected": len(rejected),
        }
    run.status = "completed"
    run.completed_at = _now()
    await db.flush()
    return {
        "run_id": str(run_id),
        "status": "completed",
        "candidates": len(candidates),
        "findings_persisted": counts["total"],
        "confirmed": counts["confirmed"],
        "rejected": len(rejected),
    }
