"""MCP Tool: openvas_scan — Greenbone/OpenVAS con 3 modos + mapeo ENS.

Wrapper MCP protocol alrededor de ``OpenvasRunner`` del motor M8
(Sesion 10 Paso 4.3). Cobertura de vulnerabilidades ENS-mapeadas:

- Familia NVT -> medidas ENS (Web, DB, SSL/TLS, Windows, SSH, ...).
- Name overrides -> medidas especificas (path traversal, auth bypass,
  HSTS, SMB signing, EOL software, cert expired, RC4, TLSv1.0/1.1).
- CVSS bands -> medidas transversales (parcheo critico op.exp.4 / 7).

Modos (parametro ``mode``):
- ``fixture``  lee XML GMP pregrabado whitelisted.
- ``mock``     XML sintetico inline (sin fixture externo).
- ``real``     python-gvm GMP contra container Greenbone. Requiere env
               GVM_HOST + GVM_USERNAME + GVM_PASSWORD + container vivo
               con feed NVT sincronizado.

scope_check fail-closed valida el target contra la autorizacion antes
de tocar el scanner.
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
    "openvas_report_linux_conformant.xml",
    "openvas_report_linux_high_severity.xml",
    "openvas_report_windows_mixed.xml",
    "openvas_report_web_server_ssl_issues.xml",
}


TOOL = MCPTool(
    name="openvas_scan",
    description=(
        "OpenVAS/Greenbone vulnerability assessment con mapeo familia NVT + "
        "CVSS -> medidas ENS Anexo II (Web Servers, Databases, SSL/TLS, "
        "Windows, etc). Modos: fixture (XML pregrabado), mock (sintetico), "
        "real (GMP contra container Greenbone via python-gvm)."
    ),
    input_schema={
        "properties": {
            "target": {
                "type": "string",
                "description": "IP o hostname target (requerido en modo real).",
            },
            "mode": {
                "type": "string",
                "enum": ["fixture", "mock", "real"],
                "default": "fixture",
            },
            "fixture_name": {
                "type": "string",
                "description": "Fichero fixture XML (solo whitelisted).",
            },
            "scan_config": {
                "type": "string",
                "enum": ["full_and_fast", "full_and_very_deep", "system_discovery"],
                "default": "full_and_fast",
            },
            "timeout_seconds": {"type": "integer", "default": 1800},
        },
        "required": ["target"],
    },
    timeout_seconds=3600,
    risk_level="medium",
    ens_measures=[
        "op.acc.2", "op.acc.4", "op.acc.5", "op.acc.6",
        "op.exp.2", "op.exp.3", "op.exp.4", "op.exp.7",
        "mp.com.1", "mp.com.2", "mp.com.3",
        "mp.info.2", "mp.info.3",
        "mp.sw.1", "mp.sw.2", "mp.s.2",
    ],
)


async def openvas_scan(
    target: str,
    mode: str = "fixture",
    fixture_name: str | None = None,
    scan_config: str = "full_and_fast",
    timeout_seconds: int = 1800,
) -> dict[str, Any]:
    """Entrada publica del tool MCP."""
    scope = check_scope(target, "scan")
    if not scope["allowed"]:
        return {
            "error": f"SCOPE DENIED: {scope['reason']}",
            "target": target, "mode": mode,
            "findings": [], "summary": {"total": 0},
        }

    try:
        from backend.app.motors.m08_verification.tools.openvas_runner import (
            OpenvasRunner,
        )
    except ImportError as exc:
        return {
            "error": f"openvas_runner no disponible: {exc}",
            "target": target, "mode": mode,
            "findings": [], "summary": {"total": 0},
        }

    if mode == "fixture":
        if not fixture_name or fixture_name not in FIXTURE_WHITELIST:
            return {
                "error": (
                    f"fixture_name requerido y en whitelist: "
                    f"{sorted(FIXTURE_WHITELIST)}"
                ),
                "target": target, "mode": mode,
                "findings": [], "summary": {"total": 0},
            }
        fixture_path = _resolve_fixture_path(fixture_name)
        if fixture_path is None:
            return {
                "error": "fixture path no resuelto en filesystem",
                "target": target, "mode": mode,
                "findings": [], "summary": {"total": 0},
            }
        result = await OpenvasRunner.run_mode(
            targets=[target], mode="fixture", fixture_path=fixture_path,
            scan_config=scan_config, timeout_seconds=timeout_seconds,
        )
    elif mode == "mock":
        result = await OpenvasRunner.run_mode(
            targets=[target], mode="mock", scan_config=scan_config,
            timeout_seconds=timeout_seconds,
        )
    elif mode == "real":
        result = await OpenvasRunner.run_mode(
            targets=[target], mode="real", scan_config=scan_config,
            timeout_seconds=timeout_seconds,
        )
    else:
        return {
            "error": f"mode invalido: {mode!r}",
            "target": target, "mode": mode,
            "findings": [], "summary": {"total": 0},
        }

    summary = OpenvasRunner.summarize(result.findings)
    payload: dict[str, Any] = {
        "target": target, "mode": mode,
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
    """Misma logica que prowler_tool/scoutsuite_tool."""
    override = (
        os.environ.get("FULKRO_OPENVAS_FIXTURES_DIR")
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
