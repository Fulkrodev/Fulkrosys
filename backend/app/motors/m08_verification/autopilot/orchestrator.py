"""Orquestador autopilot determinista (doc §13 · backbone §0-§12).

Reemplaza el stub `scheduler.task_execute_run`. Entre el Gate humano 1
(autorización/scope) y el Gate humano 2 (validación Alto), todo es autopilot:

  scope → sesión efímera + manifest → ejecutar motores MCP (pinneados,
  safe-by-default) → ZFP 1-5 + verification_level → enrich CVSS/EPSS + dedup
  → mapeo ENS/MITRE → persistir Finding canónico → triage agéntico
  (Verdict advisory, anti-injection) → asset graph → evidencia R6 →
  coverage% + golden drift → revocar sesión.

Fail-closed (doc §10): ante fallo de un motor, el run se marca PARCIAL con
cobertura reducida documentada — NUNCA se pierde ni suprime un hallazgo. Si
el LLM cae, los hallazgos deterministas se persisten igual (el backbone no
depende del agente). Excepciones → status='failed', findings intactos.
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.motors.m08_verification.agent.injection_guard import (
    INJECTION_FINDING_TEMPLATE,
    detect_injection_attempt,
)
from backend.app.motors.m08_verification.agent.triage_agent import triage_finding
from backend.app.motors.m08_verification import asset_graph
from backend.app.motors.m08_verification.autopilot.ephemeral_connector import (
    create_ephemeral_session,
    revoke_ephemeral_session,
)
from backend.app.motors.m08_verification.determinism.manifest import (
    build_run_manifest,
    compare_to_golden,
)
from backend.app.motors.m08_verification.enrichment.epss import get_epss_client
from backend.app.motors.m08_verification.enrichment.scoring import (
    compute_dedup_group_id,
    effective_severity,
)
from backend.app.motors.m08_verification.ens_mapper import EnsMapper
from backend.app.motors.m08_verification.finding_state_machine import FindingState
from backend.app.motors.m08_verification.gates import (
    verification_level_for_zfp_finding,
)
from backend.app.motors.m08_verification.mitre_mapper import MitreMapper
from backend.app.motors.m08_verification.models import (
    EvidenceRecord,
    Verdict,
    VerificationFinding,
    VerificationRun,
)
from backend.app.motors.m08_verification.normalization.adapters import (
    mcp_result_to_candidates,
)
from backend.app.motors.m08_verification.zfp_engine import run_zfp_pipeline

logger = logging.getLogger(__name__)

AUTOPILOT_PHASES = (
    "recon", "detection", "normalization", "verification", "triage", "reporting",
)

# Plan de motores por categoría ENS (server, tool, kind). `kind` decide cómo
# construir args desde el scope. Reutiliza el arsenal MCP existente (OPS-045).
# safe-by-default: solo escaneo no destructivo en autopilot (exploitation =
# Gate 2 humano).
CATEGORY_PLAN: dict[str, tuple[tuple[str, str, str], ...]] = {
    "BASICO": (
        ("recon", "nmap_scan", "host"),
        ("recon", "httpx_scan", "web"),
        ("vulnscan", "nuclei_scan", "web_or_host"),
        ("config", "lynis_audit", "host"),
    ),
    "MEDIO": (
        ("recon", "nmap_scan", "host"),
        ("recon", "httpx_scan", "web"),
        ("recon", "subfinder_scan", "domain"),
        ("vulnscan", "nuclei_scan", "web_or_host"),
        ("vulnscan", "openvas_scan", "host"),
        ("vulnscan", "trivy_scan", "host"),
        ("webpentest", "testssl", "web"),
        ("webpentest", "zap", "web"),
        ("sast", "semgrep_scan", "repo"),
        ("cloud", "prowler_audit", "cloud"),
        ("cloud", "scoutsuite_scan", "cloud"),
        ("config", "lynis_audit", "host"),
    ),
    "ALTO": (
        ("recon", "nmap_scan", "host"),
        ("recon", "httpx_scan", "web"),
        ("recon", "subfinder_scan", "domain"),
        ("recon", "amass_scan", "domain"),
        ("vulnscan", "nuclei_scan", "web_or_host"),
        ("vulnscan", "openvas_scan", "host"),
        ("vulnscan", "trivy_scan", "host"),
        ("vulnscan", "grype_scan", "host"),
        ("webpentest", "testssl", "web"),
        ("webpentest", "zap", "web"),
        ("webpentest", "nikto", "web"),
        ("apisec", "arjun", "web"),
        ("sast", "semgrep_scan", "repo"),
        ("sast", "checkov_scan", "repo"),
        ("cloud", "prowler_audit", "cloud"),
        ("cloud", "scoutsuite_scan", "cloud"),
        ("cloud", "kube_security_scan", "cloud"),
        ("config", "lynis_audit", "host"),
    ),
}

# Categoría humana label → clave de run.category ('ALTO'/'MEDIO'/'BASICO')
_CATEGORY_NORM = {
    "ALTA": "ALTO", "ALTO": "ALTO",
    "MEDIA": "MEDIO", "MEDIO": "MEDIO",
    "BASICA": "BASICO", "BASICO": "BASICO",
}


def _normalize_category(cat: str | None) -> str:
    return _CATEGORY_NORM.get((cat or "").upper(), "BASICO")


def _targets_for_kind(kind: str, scope: dict[str, Any]) -> list[str]:
    targets = list(scope.get("targets") or [])
    web = list(scope.get("web_apps") or [])
    cloud = [
        c if isinstance(c, str) else (c.get("asset_name") or c.get("type") or "")
        for c in (scope.get("cloud_accounts") or [])
    ]
    if kind == "host":
        return targets
    if kind == "web":
        return web
    if kind == "web_or_host":
        return web or targets
    if kind == "domain":
        return [t for t in targets if not _looks_like_ip(t)]
    if kind == "cloud":
        return [c for c in cloud if c]
    if kind == "repo":
        return list(scope.get("repos") or [])
    return []


def _looks_like_ip(s: str) -> bool:
    parts = s.split(".")
    return len(parts) == 4 and all(p.isdigit() for p in parts)


async def _dispatch(project_id: uuid.UUID, event_type: str, data: dict) -> None:
    """SSE best-effort (no rompe el run si el dispatcher no está)."""
    try:
        from backend.app.core.sse_dispatcher import sse_dispatcher
        await sse_dispatcher.dispatch(
            channel=f"project:{project_id}",
            event_type=event_type,
            data={**data, "project_id": str(project_id)},
        )
    except Exception as exc:  # pragma: no cover
        logger.debug("SSE dispatch %s skipped: %s", event_type, exc)


async def collect_candidates(
    run: VerificationRun,
    scope: dict[str, Any],
    authorization: dict[str, Any],
    signature: str,
) -> tuple[list[dict], list[str], list[str]]:
    """Ejecuta el arsenal MCP del plan de la categoría sobre el scope.

    Devuelve (candidates, tools_attempted, tools_failed). En dev
    (USE_MCP_REAL=false) `try_invoke_mcp_or_none` devuelve None → no candidates
    (fallback honesto · el run quedará PARCIAL). Cada tool valida scope
    fail-closed vía PENTEST_AUTHORIZATION (scope_enforcer).
    """
    from backend.app.mcp_client import try_invoke_mcp_or_none

    plan = CATEGORY_PLAN.get(_normalize_category(run.category), ())
    candidates: list[dict] = []
    attempted: list[str] = []
    failed: list[str] = []

    import json as _json
    prev_auth = os.environ.get("PENTEST_AUTHORIZATION")
    prev_sig = os.environ.get("PENTEST_AUTHORIZATION_SIG")
    os.environ["PENTEST_AUTHORIZATION"] = _json.dumps(authorization)
    os.environ["PENTEST_AUTHORIZATION_SIG"] = signature
    try:
        for server, tool, kind in plan:
            tgts = _targets_for_kind(kind, scope)
            if not tgts:
                continue
            label = f"{server}:{tool}"
            attempted.append(label)
            for target in tgts:
                try:
                    resp = await try_invoke_mcp_or_none(
                        server=server, tool=tool,
                        args={"target": target}, timeout_seconds=600,
                    )
                    cands = mcp_result_to_candidates(
                        resp, server=server, tool=tool, target=target,
                    )
                    candidates.extend(cands)
                except Exception as exc:  # pragma: no cover — fail-closed
                    logger.warning("MCP %s sobre %s falló: %s", label, target, exc)
                    if label not in failed:
                        failed.append(label)
    finally:
        if prev_auth is None:
            os.environ.pop("PENTEST_AUTHORIZATION", None)
        else:
            os.environ["PENTEST_AUTHORIZATION"] = prev_auth
        if prev_sig is None:
            os.environ.pop("PENTEST_AUTHORIZATION_SIG", None)
        else:
            os.environ["PENTEST_AUTHORIZATION_SIG"] = prev_sig

    return candidates, attempted, failed


async def process_and_persist(
    db: AsyncSession,
    run: VerificationRun,
    candidates: list[dict],
    *,
    enable_triage: bool | None = None,
) -> dict[str, Any]:
    """ZFP 1-5 → enrich → verification_level/state → persist Finding canónico
    → triage Verdict (advisory) → asset graph → evidencia R6. Determinista
    salvo el triage LLM (que es advisory y fail-closed)."""
    if not candidates:
        return {"persisted": 0, "rejected": 0, "verdicts": 0}

    kept, rejected = await run_zfp_pipeline(db, candidates)

    epss = get_epss_client()
    ens_mapper = EnsMapper(db, enable_llm=False)
    mitre_mapper = MitreMapper(enable_llm=False)
    now = datetime.now(timezone.utc)

    persisted: list[VerificationFinding] = []
    verdicts = 0
    sev_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}

    for zf in kept:
        # enrich EPSS + effective severity (nunca baja del suelo determinista)
        epss_score = epss.get(zf.cve_id) if zf.cve_id else None
        eff_sev = effective_severity(
            base_severity=zf.severity,
            cvss_score=float(zf.cvss_score) if zf.cvss_score is not None else None,
            epss_score=epss_score,
        )
        vlevel = verification_level_for_zfp_finding(zf)
        ens_measures, ens_primary = await ens_mapper.map(zf)
        mitre = mitre_mapper.map(zf)
        dedup_gid = compute_dedup_group_id(zf.finding_hash)

        vf = VerificationFinding(
            project_id=run.project_id,
            run_id=run.id,
            finding_hash=zf.finding_hash,
            title=zf.title,
            description=zf.description or "",
            severity=eff_sev,
            cvss_score=zf.cvss_score,
            cvss_vector=zf.cvss_vector,
            cve_id=zf.cve_id,
            cwe_id=zf.cwe_id,
            affected_host=zf.affected_host or "unknown",
            affected_port=zf.affected_port,
            affected_service=zf.affected_service,
            affected_service_version=zf.affected_service_version,
            affected_url=zf.affected_url,
            affected_os=zf.affected_os,
            tool_sources=list(zf.tool_sources or []),
            raw_outputs=list(zf.raw_outputs or []),
            confidence_score=zf.confidence_score,
            zfp_gate1_dedup=zf.zfp_gate1_dedup,
            zfp_gate2_fp_filter=zf.zfp_gate2_fp_filter,
            zfp_gate3_cross_tool=zf.zfp_gate3_cross_tool,
            zfp_gate4_retest=zf.zfp_gate4_retest,
            zfp_gate5_classification=zf.zfp_gate5_classification,
            ens_measures=ens_measures,
            ens_primary_measure=ens_primary,
            mitre_techniques=[
                {"technique": t.get("technique_id"), "tactic": t.get("tactic"),
                 "technique_name": t.get("technique_name")}
                for t in mitre
            ],
            remediation_summary="",
            status="open",
            # ── canónico autopilot v2 ──
            epss_score=epss_score,
            verification_level=vlevel,
            finding_state=FindingState.DETECTED,
            dedup_group_id=dedup_gid,
            first_seen=now,
            last_seen=now,
            source_engine=(zf.tool_sources[0] if zf.tool_sources else None),
            engine_version=None,
        )
        db.add(vf)
        await db.flush()
        persisted.append(vf)
        sev_counts[eff_sev if eff_sev in sev_counts else "info"] += 1

        # asset graph (PKG-lite · fail-soft)
        node_id = await asset_graph.upsert_asset_for_finding(
            db, run.project_id, host=vf.affected_host,
            worst_severity=eff_sev, service=vf.affected_service,
        )
        if node_id:
            vf.asset_node_id = node_id

        # triage agéntico (advisory · anti-injection · fail-closed)
        do_triage = (
            enable_triage if enable_triage is not None
            else bool(_safe_llm_available())
        )
        if do_triage:
            verdict_payload = triage_finding({
                "finding_hash": vf.finding_hash, "title": vf.title,
                "description": vf.description, "severity": vf.severity,
                "cve_id": vf.cve_id, "cvss_score": float(vf.cvss_score) if vf.cvss_score else None,
                "epss_score": epss_score, "affected_host": vf.affected_host,
                "source_engine": vf.source_engine,
                "verification_level": vlevel,
                "raw_output_excerpt": (vf.raw_outputs[0].get("excerpt") if vf.raw_outputs else ""),
            })
            db.add(Verdict(
                project_id=run.project_id, run_id=run.id, finding_id=vf.id,
                model_version=verdict_payload["model_version"],
                prompt_hash=verdict_payload.get("prompt_hash"),
                input_refs=verdict_payload.get("input_refs") or [],
                triage=verdict_payload.get("triage") or {},
                structured_output_valid=verdict_payload["structured_output_valid"],
            ))
            verdicts += 1
            # finding_state → triaged (el verdict NUNCA baja severidad/estado)
            vf.finding_state = FindingState.TRIAGED

        # evidencia append-only R6 (doc §4)
        db.add(EvidenceRecord(
            project_id=run.project_id, client_id=None, run_id=run.id,
            finding_id=vf.id, run_manifest_hash=run.run_manifest_hash,
            actor="system", action="finding.persisted",
            component="m08:autopilot.orchestrator",
            output_hash=vf.finding_hash,
            ens_relevance=ens_primary,
            payload={"severity": eff_sev, "verification_level": vlevel,
                     "classification": vf.zfp_gate5_classification},
        ))

    await db.flush()
    return {
        "persisted": len(persisted),
        "rejected": len(rejected),
        "verdicts": verdicts,
        "severity_counts": sev_counts,
    }


def _safe_llm_available() -> bool:
    try:
        return bool(get_settings().anthropic_api_key.get_secret_value())
    except Exception:
        return False


async def orchestrate_run(
    db: AsyncSession,
    run_id: uuid.UUID | str,
    *,
    candidates_override: list[dict] | None = None,
    enable_triage: bool | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Ejecuta el autopilot end-to-end para un run (doc §13).

    `candidates_override` permite tests deterministas sin MCP real. Devuelve
    un execution_summary. Fail-closed: cualquier excepción → status='failed'
    sin perder findings ya persistidos.
    """
    now = now or datetime.now(timezone.utc)
    run = await db.get(VerificationRun, uuid.UUID(str(run_id)))
    if run is None:
        raise ValueError(f"VerificationRun {run_id} no existe")

    scope = run.scope_jsonb or {}
    category = _normalize_category(run.category)
    targets_all = list(scope.get("targets") or []) + list(scope.get("web_apps") or [])
    assets_in_scope = len(set(map(str, targets_all)))

    run.autopilot_status = "running"
    run.autopilot_phase = "recon"
    run.phase1_started_at = run.phase1_started_at or now
    await db.flush()
    await _dispatch(run.project_id, "m08_autopilot_started", {
        "run_id": str(run.id), "category": category,
        "assets_in_scope": assets_in_scope,
    })

    try:
        # 1. Sesión efímera + manifest (determinismo §11)
        session = create_ephemeral_session(run, scope, now=now)
        manifest, manifest_hash = build_run_manifest(
            scope=scope,
            tool_versions={s_t[0] + ":" + s_t[1]: "pinned"
                           for s_t in CATEGORY_PLAN.get(category, ())},
            config={"category": category, "use_mcp_real": get_settings().use_mcp_real},
            model_version="claude-opus-4-8",
            target_snapshot_ref=session["session_id"],
        )
        run.run_manifest_hash = manifest_hash
        run.assets_in_scope = assets_in_scope
        await db.flush()

        # 2. Recon + detección (ejecutar motores)
        run.autopilot_phase = "detection"
        await db.flush()
        if candidates_override is not None:
            candidates = candidates_override
            attempted = ["override"]
            failed: list[str] = []
        else:
            candidates, attempted, failed = await collect_candidates(
                run, scope, session["authorization"], session["signature"],
            )
        run.tools_attempted = attempted
        run.tools_failed = failed
        await db.flush()

        # 3. Anti-injection: contenido del objetivo manipulador = finding (§7)
        injected = _scan_candidates_for_injection(candidates)
        if injected:
            candidates = candidates + [injected]
        await _dispatch(run.project_id, "m08_phase_change", {
            "run_id": str(run.id), "phase": "verification",
            "raw_candidates": len(candidates),
        })

        # 4. Normalización + verificación + triage + persistencia
        run.autopilot_phase = "verification"
        run.phase2_started_at = run.phase2_started_at or datetime.now(timezone.utc)
        await db.flush()
        result = await process_and_persist(
            db, run, candidates, enable_triage=enable_triage,
        )

        # 5. Reporting · aggregates + coverage + golden drift
        run.autopilot_phase = "reporting"
        sev = result.get("severity_counts", {})
        run.total_findings = result["persisted"]
        run.confirmed_findings = result["persisted"]
        run.critical_count = sev.get("critical", 0)
        run.high_count = sev.get("high", 0)
        run.medium_count = sev.get("medium", 0)
        run.low_count = sev.get("low", 0)
        run.info_count = sev.get("info", 0)
        # Cobertura honesta (doc §12): en dev sin USE_MCP_REAL nada corrió de
        # verdad → 0% + partial. Con override (tests) o MCP real → scanned.
        mcp_real = bool(get_settings().use_mcp_real)
        if candidates_override is not None or mcp_real:
            run.assets_scanned = assets_in_scope
        else:
            run.assets_scanned = 0
        run.coverage_pct = (
            round(100.0 * run.assets_scanned / assets_in_scope, 2)
            if assets_in_scope else 0.0
        )
        run.partial_run = bool(failed) or (
            candidates_override is None and not mcp_real
        )

        # golden drift (si hay golden_run_id con manifest)
        golden_hash = None
        if run.golden_run_id:
            golden = await db.get(VerificationRun, run.golden_run_id)
            golden_hash = golden.run_manifest_hash if golden else None
        drift = compare_to_golden(manifest_hash, golden_hash)

        # 6. Revocar sesión efímera (zero standing access §2)
        revoke_ephemeral_session(run, now=datetime.now(timezone.utc))

        # 7. Estado final: ALTO pausa en Gate 2 humano (atestación)
        completed_at = datetime.now(timezone.utc)
        run.phase2_completed_at = completed_at
        run.completed_at = completed_at
        if category == "ALTO":
            run.autopilot_status = "paused_gate2"  # requiere atestación humana
            run.status = "phase3_validating"
        elif run.partial_run:
            run.autopilot_status = "partial"
            run.status = "completed"
        else:
            run.autopilot_status = "completed"
            run.status = "completed"

        # evidencia run-level (append-only R6)
        db.add(EvidenceRecord(
            project_id=run.project_id, client_id=None, run_id=run.id,
            finding_id=None, run_manifest_hash=manifest_hash,
            actor="system", action="run.completed",
            component="m08:autopilot.orchestrator",
            output_hash=manifest_hash,
            payload={
                "category": category, "findings": result["persisted"],
                "verdicts": result["verdicts"], "rejected": result["rejected"],
                "coverage_pct": float(run.coverage_pct or 0),
                "partial": run.partial_run, "drift": drift,
                "autopilot_status": run.autopilot_status,
                "tools_attempted": attempted, "tools_failed": failed,
            },
        ))
        await db.flush()

        await _dispatch(run.project_id, "m08_run_completed", {
            "run_id": str(run.id), "status": run.autopilot_status,
            "findings": result["persisted"], "coverage_pct": float(run.coverage_pct or 0),
            "partial": run.partial_run, "manifest_hash": manifest_hash,
        })

        return {
            "run_id": str(run.id),
            "autopilot_status": run.autopilot_status,
            "category": category,
            "findings_persisted": result["persisted"],
            "rejected": result["rejected"],
            "verdicts": result["verdicts"],
            "severity_counts": sev,
            "coverage_pct": float(run.coverage_pct or 0),
            "partial_run": run.partial_run,
            "run_manifest_hash": manifest_hash,
            "golden_drift": drift,
            "tools_attempted": attempted,
            "tools_failed": failed,
            "injection_detected": injected is not None,
        }

    except Exception as exc:
        logger.exception("orchestrate_run %s falló: %s", run_id, exc)
        run.autopilot_status = "failed"
        try:
            revoke_ephemeral_session(run, now=datetime.now(timezone.utc))
            await db.flush()
        except Exception:  # pragma: no cover
            pass
        await _dispatch(run.project_id, "m08_run_completed", {
            "run_id": str(run.id), "status": "failed", "error": str(exc)[:300],
        })
        raise


def _scan_candidates_for_injection(candidates: list[dict]) -> dict | None:
    """Si algún candidate trae contenido del objetivo con prompt-injection,
    devuelve un finding sintético de seguridad (doc §7). NUNCA suprime nada."""
    hosts: list[str] = []
    matched_all: set[str] = set()
    for c in candidates:
        blob = " ".join(
            str(c.get(k) or "") for k in ("title", "description", "raw_output_excerpt")
        )
        det = detect_injection_attempt(blob)
        if det["suspicious"]:
            hosts.append(str(c.get("affected_host") or "unknown"))
            matched_all.update(det["matched"])
    if not hosts:
        return None
    tmpl = dict(INJECTION_FINDING_TEMPLATE)
    return {
        "title": tmpl["title"],
        "description": tmpl["description"] + f" Patrones: {sorted(matched_all)}.",
        "severity": tmpl["severity"],
        "affected_host": hosts[0],
        "tool": tmpl["source_engine"],
        "source_engine": tmpl["source_engine"],
        "rule_id": tmpl["rule_id"],
        "raw_output_excerpt": f"injection markers: {sorted(matched_all)}",
        "cve_id": None,
    }
