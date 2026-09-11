"""MCP Tool: prowler_audit — Prowler AWS/Azure/GCP con 3 modos + mapeo ENS.

Wrapper MCP protocol alrededor de ``ProwlerRunner`` del motor M8 (Sesion 10
Paso 4.1). Permite invocar el mismo core desde:

- MCP server ``fulkro-cloud`` (JSON-RPC 2.0 con agente LLM).
- Orchestrator M8 interno (import directo).
- Demo/CLI (import directo).

Modos soportados (parametro ``mode``):

- ``fixture`` — lee un JSON ASFF pre-grabado (fixture_name whitelisted).
- ``mock``    — levanta moto con recursos seed y genera ASFF sintetico.
- ``real``    — ejecuta prowler CLI (requiere creds AWS + binario en PATH).

scope_check sigue fail-closed: sin ``PENTEST_AUTHORIZATION`` cargado, el
tool devuelve ``SCOPE DENIED`` sin ejecutar nada.

Output schema (dict):
    provider, mode, findings: list, summary: dict, error?: str.

``findings`` llegan ya con ``tool_metadata.ens_measures`` poblado via mapper
CIS->ENS (ver prowler_cis_ens_mapper.py).
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from shared.mcp_protocol import MCPTool
from shared.scope_check import check_scope

logger = logging.getLogger(__name__)


# Whitelist de fixtures. Evita que un agente LLM intente leer ficheros
# arbitrarios del disco via este tool.
FIXTURE_WHITELIST: set[str] = {
    "prowler_iam_non_conformant.asff.json",
    "prowler_iam_conformant.asff.json",
    "prowler_s3_mixed.asff.json",
    "prowler_ec2_violations.asff.json",
}


TOOL = MCPTool(
    name="prowler_audit",
    description=(
        "Prowler cloud security audit con mapeo CIS->ENS Anexo II. "
        "Soporta AWS/Azure/GCP. Modos: fixture (ASFF JSON pregrabado), "
        "mock (moto con recursos sembrados), real (prowler CLI contra "
        "cuenta live — requiere credenciales)."
    ),
    input_schema={
        "properties": {
            "provider": {
                "type": "string",
                "enum": ["aws", "azure", "gcp", "kubernetes"],
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
                "default": ["iam", "s3", "ec2"],
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


async def prowler_audit(
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

    services_list = list(services) if services else ["iam", "s3", "ec2"]

    # Import lazy: el runner importa moto solo cuando mode=="mock".
    try:
        from backend.app.motors.m08_verification.tools.prowler_runner import (
            ProwlerRunner,
        )
    except ImportError as exc:  # defensivo: desplegado standalone sin backend import path
        return {
            "error": f"prowler_runner no disponible: {exc}",
            "provider": provider, "mode": mode,
            "findings": [], "summary": {"total": 0},
        }

    if mode == "fixture":
        if not fixture_name or fixture_name not in FIXTURE_WHITELIST:
            return {
                "error": (
                    f"fixture_name requerido y debe estar en whitelist: "
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
        result = await ProwlerRunner.run_mode(
            targets=[provider], mode="fixture",
            provider=provider, fixture_path=fixture_path,
            services=services_list, timeout_seconds=timeout_seconds,
        )
    elif mode == "mock":
        result = await ProwlerRunner.run_mode(
            targets=[provider], mode="mock",
            provider=provider, services=services_list,
            timeout_seconds=timeout_seconds,
        )
    elif mode == "real":
        result = await ProwlerRunner.run_mode(
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

    summary = ProwlerRunner.summarize(result.findings)
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
    """Busca el fixture en la ubicacion canonica tests/fixtures.

    1. Env var ``FULKRO_PROWLER_FIXTURES_DIR`` (override explicito).
    2. Ruta repo relativa a este archivo.
    """
    override = os.environ.get("FULKRO_PROWLER_FIXTURES_DIR")
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
