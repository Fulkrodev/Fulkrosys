"""MCP Tool: scoutsuite_audit — ScoutSuite AWS/Azure/GCP con 3 modos + ENS.

Wrapper MCP protocol alrededor de ``ScoutSuiteRunner`` del motor M8
(Sesion 10 Paso 4.2). Cobertura multi-cloud complementaria a Prowler:

- AWS: checks adicionales (root account usage, multi-keys, cloudtrail,
  vpc/sg defaults) que Prowler no enfatiza.
- Azure: cobertura nativa (storage blob public, SQL TDE, keyvault RBAC,
  NSG, subscription MFA, diagnostic settings).
- GCP: cobertura nativa (compute firewall, storage public, IAM SA keys,
  audit logging, cloudsql SSL, bigquery public).

Modos (parametro ``mode``):
- ``fixture``  JSON pregrabado whitelisted.
- ``mock``     moto para AWS. Azure/GCP devuelven vacio + error descriptivo.
- ``real``     scout CLI contra cuenta live.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from shared.mcp_protocol import MCPTool
from shared.scope_check import check_scope

logger = logging.getLogger(__name__)


FIXTURE_WHITELIST: set[str] = {
    "scoutsuite_aws_iam_findings.json",
    "scoutsuite_aws_conformant.json",
    "scoutsuite_azure_storage_mixed.json",
    "scoutsuite_gcp_compute_violations.json",
}


TOOL = MCPTool(
    name="scoutsuite_audit",
    description=(
        "ScoutSuite multi-cloud security audit (AWS/Azure/GCP) con mapeo "
        "cloud-checks -> medidas ENS Anexo II. Complementario a Prowler "
        "(cobertura extra AWS + Azure/GCP unicos). Modos: fixture, mock "
        "(AWS only via moto), real (scout CLI)."
    ),
    input_schema={
        "properties": {
            "provider": {
                "type": "string",
                "enum": ["aws", "azure", "gcp", "aliyun", "oracle"],
                "default": "aws",
            },
            "mode": {
                "type": "string",
                "enum": ["fixture", "mock", "real"],
                "default": "fixture",
            },
            "fixture_name": {
                "type": "string",
                "description": "Fichero fixture (solo whitelisted).",
            },
            "services": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Servicios a auditar (p.ej. iam, cloudtrail).",
            },
            "timeout_seconds": {"type": "integer", "default": 3600},
        },
        "required": ["provider"],
    },
    timeout_seconds=3600,
    risk_level="low",
    ens_measures=[
        "op.acc.2", "op.acc.4", "op.acc.5",
        "op.exp.2", "op.exp.8", "op.exp.10",
        "mp.com.1", "mp.com.2",
        "mp.info.2", "mp.info.3", "op.exp.6",
    ],
)


async def scoutsuite_audit(
    provider: str = "aws",
    mode: str = "fixture",
    fixture_name: str | None = None,
    services: list[str] | None = None,
    timeout_seconds: int = 3600,
) -> dict[str, Any]:
    """Entrada publica del tool MCP."""
    scope = check_scope("__local__", "config_audit")
    if not scope["allowed"]:
        return {
            "error": f"SCOPE DENIED: {scope['reason']}",
            "provider": provider, "mode": mode,
            "findings": [], "summary": {"total": 0},
        }

    services_list = list(services) if services else []

    try:
        from backend.app.motors.m08_verification.tools.scoutsuite_runner import (
            ScoutSuiteRunner,
        )
    except ImportError as exc:
        return {
            "error": f"scoutsuite_runner no disponible: {exc}",
            "provider": provider, "mode": mode,
            "findings": [], "summary": {"total": 0},
        }

    if mode == "fixture":
        if not fixture_name or fixture_name not in FIXTURE_WHITELIST:
            return {
                "error": (
                    f"fixture_name requerido y en whitelist: "
                    f"{sorted(FIXTURE_WHITELIST)}"
                ),
                "provider": provider, "mode": mode,
                "findings": [], "summary": {"total": 0},
            }
        fixture_path = _resolve_fixture_path(fixture_name)
        if fixture_path is None:
            return {
                "error": "fixture path no resuelto en filesystem",
                "provider": provider, "mode": mode,
                "findings": [], "summary": {"total": 0},
            }
        result = await ScoutSuiteRunner.run_mode(
            targets=[provider], mode="fixture",
            provider=provider, fixture_path=fixture_path,
            services=services_list, timeout_seconds=timeout_seconds,
        )
    elif mode == "mock":
        result = await ScoutSuiteRunner.run_mode(
            targets=[provider], mode="mock",
            provider=provider, services=services_list,
            timeout_seconds=timeout_seconds,
        )
    elif mode == "real":
        result = await ScoutSuiteRunner.run_mode(
            targets=[provider], mode="real",
            provider=provider, services=services_list,
            timeout_seconds=timeout_seconds,
        )
    else:
        return {
            "error": f"mode invalido: {mode!r}",
            "provider": provider, "mode": mode,
            "findings": [], "summary": {"total": 0},
        }

    summary = ScoutSuiteRunner.summarize(result.findings)
    payload: dict[str, Any] = {
        "provider": provider,
        "mode": mode,
        "findings": list(result.findings),
        "summary": summary,
        "return_code": result.return_code,
        "duration_seconds": result.duration_seconds,
    }
    if result.error:
        payload["error"] = result.error
    if result.timed_out:
        payload["timed_out"] = True
    return payload


def _resolve_fixture_path(name: str) -> Path | None:
    """Misma logica que prowler_tool._resolve_fixture_path."""
    override = (
        os.environ.get("FULKRO_SCOUTSUITE_FIXTURES_DIR")
        or os.environ.get("FULKRO_PROWLER_FIXTURES_DIR")
    )
    if override:
        p = Path(override) / name
        if p.exists():
            return p
    here = Path(__file__).resolve()
    for parent in here.parents:
        if parent.name == "backend":
            candidate = (
                parent / "tests" / "motors" / "m08_verification"
                / "fixtures" / name
            )
            if candidate.exists():
                return candidate
            break
    return None
