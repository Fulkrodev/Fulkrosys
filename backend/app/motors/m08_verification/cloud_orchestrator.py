"""M8 v5.1 — Orchestrator cloud audits (Sesion 10 Paso 4.1 -> 4.2).

Orquesta Prowler (4.1) + ScoutSuite (4.2) segun provider y categoria ENS.
Funcion pura: recibe un scope + category y devuelve findings normalizados.
No toca DB.

Regla de activacion:

    IF scope["cloud_accounts"] no vacio  AND  category in {"MEDIA","ALTA"}
    THEN:
        - provider == aws    -> Prowler + ScoutSuite (complementarios)
        - provider in {azure, gcp, aliyun, oracle} -> ScoutSuite solo
          (Prowler no soporta con la misma profundidad)

Para BASICA los audits cloud son opcionales (skipped por defecto).
Para MEDIA/ALTA son requisito ENS implicito (RD 311/2022 no cita a los
tools pero exige evidencia de control IAM/logging/cifrado/perimetro cloud).

Consolidacion (4.2):
- Findings de ambos tools se agregan manteniendo ``tool`` para trazabilidad.
- El dedupe por (provider, check_id, affected_host) se delega al ZFP engine
  downstream (backend/app/motors/m08_verification/zfp_engine.py), no aqui:
  el orchestrator debe pasar todos los findings para que el ZFP los clustere
  junto con los del resto de tools no-cloud (nmap/nuclei/zap...).
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Sequence

from backend.app.motors.m08_verification.tools.prowler_runner import (
    ProwlerMode,
    ProwlerRunner,
)
from backend.app.motors.m08_verification.tools.scoutsuite_runner import (
    ScoutSuiteRunner,
)

logger = logging.getLogger(__name__)


TRIGGERING_CATEGORIES: frozenset[str] = frozenset({"MEDIA", "ALTA"})

DEFAULT_SERVICES_AWS: tuple[str, ...] = ("iam", "s3", "ec2")

# Providers donde Prowler es parte de la chain. Resto van solo por
# ScoutSuite (cobertura nativa multi-cloud).
PROWLER_SUPPORTED: frozenset[str] = frozenset({"aws"})

# Providers donde ScoutSuite aporta cobertura cloud-nativa.
SCOUTSUITE_SUPPORTED: frozenset[str] = frozenset({
    "aws", "azure", "gcp", "aliyun", "oracle",
})


async def run_cloud_audit(
    scope: dict[str, Any],
    category: str,
    *,
    mode: ProwlerMode = "fixture",
    fixture_path: Path | None = None,
    services: Sequence[str] = DEFAULT_SERVICES_AWS,
    force: bool = False,
    scoutsuite_fixture_path: Path | None = None,
) -> dict[str, Any]:
    """Ejecuta audit cloud chain (Prowler + ScoutSuite) si scope lo requiere.

    ``fixture_path`` aplica a Prowler. ``scoutsuite_fixture_path`` aplica a
    ScoutSuite (permite mezclar fixtures distintas en modo fixture). Si se
    omite ``scoutsuite_fixture_path``, ScoutSuite se salta en modo fixture
    (no hay fallback razonable sin fixture explicita).

    Returns dict con:
        skipped: bool, reason: str (si skipped)
        findings: list (union Prowler + ScoutSuite)
        summary: dict agregada
        mode_used: str
        providers_audited: list[str]
        tools_run: dict[provider -> list[tool_names]]
        per_tool: dict[tool -> per-provider info]
    """
    cloud_accounts = scope.get("cloud_accounts") or []
    category_upper = (category or "").upper()

    if not force and not cloud_accounts:
        return {
            "skipped": True,
            "reason": "scope.cloud_accounts vacio",
            "findings": [], "summary": {"total": 0},
            "mode_used": None, "providers_audited": [], "tools_run": {},
            "per_tool": {},
        }
    if not force and category_upper not in TRIGGERING_CATEGORIES:
        return {
            "skipped": True,
            "reason": (
                f"category {category_upper!r} fuera de trigger set "
                f"{sorted(TRIGGERING_CATEGORIES)}"
            ),
            "findings": [], "summary": {"total": 0},
            "mode_used": None, "providers_audited": [], "tools_run": {},
            "per_tool": {},
        }

    providers = _detect_providers(cloud_accounts) if cloud_accounts else ["aws"]
    aggregated_findings: list[dict[str, Any]] = []
    per_tool: dict[str, dict[str, dict[str, Any]]] = {"prowler": {}, "scoutsuite": {}}
    tools_run: dict[str, list[str]] = {}

    for provider in providers:
        tools_for_provider: list[str] = []
        # ── Prowler (AWS) ───────────────────────────────────────
        if provider in PROWLER_SUPPORTED:
            p_result = await ProwlerRunner.run_mode(
                targets=[provider], mode=mode, provider=provider,
                fixture_path=fixture_path, services=services,
            )
            aggregated_findings.extend(list(p_result.findings))
            per_tool["prowler"][provider] = {
                "return_code": p_result.return_code,
                "duration_seconds": p_result.duration_seconds,
                "findings_count": len(p_result.findings),
                "error": p_result.error,
                "timed_out": p_result.timed_out,
            }
            tools_for_provider.append("prowler")

        # ── ScoutSuite (todos los providers soportados) ─────────
        if provider in SCOUTSUITE_SUPPORTED:
            ss_fixture = scoutsuite_fixture_path
            # En modo fixture, si no nos pasan path explicito saltamos
            # ScoutSuite en silencio (no todos los tests lo necesitan).
            if mode == "fixture" and ss_fixture is None:
                per_tool["scoutsuite"][provider] = {
                    "skipped": True,
                    "reason": "fixture mode sin scoutsuite_fixture_path",
                    "findings_count": 0,
                }
            else:
                ss_result = await ScoutSuiteRunner.run_mode(
                    targets=[provider], mode=mode, provider=provider,
                    fixture_path=ss_fixture, services=(),
                )
                aggregated_findings.extend(list(ss_result.findings))
                per_tool["scoutsuite"][provider] = {
                    "return_code": ss_result.return_code,
                    "duration_seconds": ss_result.duration_seconds,
                    "findings_count": len(ss_result.findings),
                    "error": ss_result.error,
                    "timed_out": ss_result.timed_out,
                }
                tools_for_provider.append("scoutsuite")
        tools_run[provider] = tools_for_provider

    summary = _summarize(aggregated_findings)
    return {
        "skipped": False,
        "mode_used": mode,
        "providers_audited": providers,
        "tools_run": tools_run,
        "findings": aggregated_findings,
        "summary": summary,
        "per_tool": per_tool,
    }


def _summarize(findings: list[dict[str, Any]]) -> dict[str, Any]:
    """Resumen agregado cross-tool."""
    by_sev: dict[str, int] = {}
    by_tool: dict[str, int] = {}
    by_provider: dict[str, int] = {}
    ens_hits: dict[str, int] = {}
    for f in findings:
        sev = str(f.get("severity", "info"))
        by_sev[sev] = by_sev.get(sev, 0) + 1
        tool = str(f.get("tool", "unknown"))
        by_tool[tool] = by_tool.get(tool, 0) + 1
        md = f.get("tool_metadata", {}) or {}
        prov = md.get("provider") or "unknown"
        by_provider[prov] = by_provider.get(prov, 0) + 1
        for m in md.get("ens_measures", []):
            ens_hits[m] = ens_hits.get(m, 0) + 1
    return {
        "total": len(findings),
        "by_severity": by_sev,
        "by_tool": by_tool,
        "by_provider": by_provider,
        "ens_measures_hit": ens_hits,
        "ens_measures_unique": sorted(ens_hits.keys()),
    }


def _detect_providers(cloud_accounts: list[Any]) -> list[str]:
    """Extrae providers unicos de la lista cloud_accounts del scope.

    Tolerante al formato: cada entry puede ser string ("aws") o dict con
    ``provider`` o ``type``.
    """
    providers: list[str] = []
    seen: set[str] = set()
    for acc in cloud_accounts:
        provider = None
        if isinstance(acc, str):
            provider = acc.lower()
        elif isinstance(acc, dict):
            provider = (acc.get("provider") or acc.get("type") or "").lower()
        if not provider:
            continue
        provider_norm = {"amazon": "aws", "google": "gcp", "azure": "azure", "aws": "aws", "gcp": "gcp"}.get(
            provider, provider,
        )
        if provider_norm not in seen:
            seen.add(provider_norm)
            providers.append(provider_norm)
    if not providers:
        # default fallback cuando hay cuentas pero ningun provider identificable
        providers = ["aws"]
    return providers


def should_trigger(scope: dict[str, Any], category: str) -> bool:
    """Helper booleano — util para tests y UI."""
    if not (scope.get("cloud_accounts") or []):
        return False
    return (category or "").upper() in TRIGGERING_CATEGORIES
