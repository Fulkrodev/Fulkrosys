"""M8 v5.1 — Orchestrator de vulnerability scanning (Sesion 10 Paso 4.3).

DEPRECADO (#19 Ola 7) · NO es el path de produccion. El flujo canonico de
vuln-scan es ``VerificationService.create_run`` (m08_verification/service.py) +
endpoints ``/projects/{id}/verification/*`` + runners gated por ``USE_MCP_REAL``.
Este orquestador quedo huerfano (solo lo invocan tests de OpenvasRunner) · se
conserva como utilidad de bajo nivel pero NO debe cablearse a endpoints nuevos
(evita duplicar caminos de scan · ver test guard test_vuln_orchestrator_deprecated).
El scan REAL (binarios nuclei/openvas/prowler + ``USE_MCP_REAL=true`` +
credenciales de proveedor) se habilita en produccion (Hetzner · FASE J); en
dev/test corre en modo fixture. Nota credenciales (#19): los scanners de infra
(AWS/Azure/GCP via scoutsuite/prowler) usan credenciales de proveedor (ENV/perfil),
dominio DISTINTO del OAuth M16 (M365/Graph · config discovery #18) — no hay puente
1:1 entre ambos; el aprovisionamiento de credenciales del scanner es operativo de
despliegue (FASE J), no un cable de aplicacion.

Coordina tools NO-cloud que escanean red/host/servicios:
- OpenVAS (4.3): vulnerability assessment profundo (NVT feed).
- Nuclei   (existente pre-Sesion 10): plantillas HTTP/API rapidas.

Los tools son complementarios:
- Nuclei tiene fingerprinting web/API rapido, baja false-positive rate,
  buena cobertura CVE recientes de aplicacion.
- OpenVAS tiene cobertura profunda de servicios/OS/red (cientos de miles
  de NVT), util para baseline ENS Media/Alta cuando Nuclei no alcanza.

Regla de activacion:

    IF scope["targets"] no vacio  AND  category in {BASICA, MEDIA, ALTA}
    THEN ejecutar ambos en chain (OpenVAS + Nuclei).

A diferencia del cloud_orchestrator (que salta BASICA), el vuln scanning
es requisito **tambien** para BASICA ENS.

Consolidacion delegada al ZFP engine M8 downstream. Aqui se agregan
findings manteniendo ``tool`` para trazabilidad.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from backend.app.motors.m08_verification.tools.openvas_runner import (
    OpenVASMode,
    OpenvasRunner,
)

logger = logging.getLogger(__name__)


TRIGGERING_CATEGORIES: frozenset[str] = frozenset({"BASICA", "MEDIA", "ALTA"})


async def run_vuln_audit(
    scope: dict[str, Any],
    category: str,
    *,
    openvas_mode: OpenVASMode = "fixture",
    openvas_fixture_path: Path | None = None,
    openvas_scan_config: str = "full_and_fast",
    include_nuclei: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    """Ejecuta chain de vulnerability scanning.

    ``include_nuclei`` queda en False por default: la integracion con el
    NucleiRunner existente se delega al caller (orchestrator global M8)
    para no duplicar invocaciones cuando ya esta presente en pipeline.

    Returns dict con:
        skipped, reason, tools_run, findings, summary, per_tool.
    """
    targets = scope.get("targets") or []
    category_upper = (category or "").upper()

    if not force and not targets:
        return {
            "skipped": True,
            "reason": "scope.targets vacio",
            "findings": [], "summary": {"total": 0},
            "tools_run": [], "per_tool": {},
        }
    if not force and category_upper not in TRIGGERING_CATEGORIES:
        return {
            "skipped": True,
            "reason": (
                f"category {category_upper!r} fuera de trigger set "
                f"{sorted(TRIGGERING_CATEGORIES)}"
            ),
            "findings": [], "summary": {"total": 0},
            "tools_run": [], "per_tool": {},
        }

    tools_run: list[str] = []
    per_tool: dict[str, dict[str, Any]] = {}
    aggregated_findings: list[dict[str, Any]] = []

    # ── OpenVAS ─────────────────────────────────────────────────
    openvas_result = await OpenvasRunner.run_mode(
        targets=targets,
        mode=openvas_mode,
        fixture_path=openvas_fixture_path,
        scan_config=openvas_scan_config,
    )
    aggregated_findings.extend(list(openvas_result.findings))
    per_tool["openvas"] = {
        "return_code": openvas_result.return_code,
        "duration_seconds": openvas_result.duration_seconds,
        "findings_count": len(openvas_result.findings),
        "error": openvas_result.error,
        "timed_out": openvas_result.timed_out,
    }
    tools_run.append("openvas")

    # ── Nuclei (opcional, caller gestiona fixture/target) ──────
    if include_nuclei:
        try:
            from backend.app.motors.m08_verification.tools.nuclei_runner import (
                NucleiRunner,
            )
            # Por defecto, modo real (nuclei suele estar instalado); si
            # no, el runner degrada solo.
            nuclei_result = await NucleiRunner.run(targets=targets)
            aggregated_findings.extend(list(nuclei_result.findings))
            per_tool["nuclei"] = {
                "return_code": nuclei_result.return_code,
                "duration_seconds": nuclei_result.duration_seconds,
                "findings_count": len(nuclei_result.findings),
                "error": nuclei_result.error,
                "timed_out": nuclei_result.timed_out,
            }
            tools_run.append("nuclei")
        except Exception as exc:  # pragma: no cover
            logger.warning("vuln_orchestrator: nuclei no disponible: %s", exc)
            per_tool["nuclei"] = {"skipped": True, "reason": str(exc)}

    return {
        "skipped": False,
        "targets": list(targets),
        "tools_run": tools_run,
        "findings": aggregated_findings,
        "summary": _summarize(aggregated_findings),
        "per_tool": per_tool,
    }


def _summarize(findings: list[dict[str, Any]]) -> dict[str, Any]:
    by_sev: dict[str, int] = {}
    by_tool: dict[str, int] = {}
    ens_hits: dict[str, int] = {}
    cve_refs_total = 0
    for f in findings:
        sev = str(f.get("severity", "info"))
        by_sev[sev] = by_sev.get(sev, 0) + 1
        tool = str(f.get("tool", "unknown"))
        by_tool[tool] = by_tool.get(tool, 0) + 1
        md = f.get("tool_metadata", {}) or {}
        for m in md.get("ens_measures", []):
            ens_hits[m] = ens_hits.get(m, 0) + 1
        cve_refs = md.get("cve_refs") or []
        cve_refs_total += len(cve_refs)
    return {
        "total": len(findings),
        "by_severity": by_sev,
        "by_tool": by_tool,
        "ens_measures_hit": ens_hits,
        "ens_measures_unique": sorted(ens_hits.keys()),
        "cve_references_total": cve_refs_total,
    }


def should_trigger(scope: dict[str, Any], category: str) -> bool:
    if not (scope.get("targets") or []):
        return False
    return (category or "").upper() in TRIGGERING_CATEGORIES
