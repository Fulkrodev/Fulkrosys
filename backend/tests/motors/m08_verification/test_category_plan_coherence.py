"""Regresión batch2: cada (server, tool) de CATEGORY_PLAN del autopilot debe
existir como MCPTool.name REAL registrado en backend/mcp_servers.

Antes httpx_scan/subfinder_scan/amass_scan/grype_scan/testssl/zap/nikto/arjun/
scoutsuite_scan NO existían → "tool not found" → escaneo MEDIO/ALTO degradado en
silencio (dossier ENAC falso-incompleto). Este guard lee el `name=` real de los
ficheros *_tool.py (sin importar los servers · self-maintaining) y falla si
CATEGORY_PLAN deriva de nuevo.
"""
from __future__ import annotations

import re
from pathlib import Path

from backend.app.motors.m08_verification.autopilot.orchestrator import (
    CATEGORY_PLAN,
)

_MCP_SERVERS = Path(__file__).resolve().parents[3] / "mcp_servers"
_NAME_RE = re.compile(r"""name\s*=\s*["']([a-z0-9_]+)["']""")


def _registered_tool_names() -> set[str]:
    names: set[str] = set()
    for tool_file in _MCP_SERVERS.glob("*/tools/*_tool.py"):
        text = tool_file.read_text(encoding="utf-8")
        # El primer name= del fichero es el MCPTool.name (registro del tool).
        m = _NAME_RE.search(text)
        if m:
            names.add(m.group(1))
    return names


def test_category_plan_tools_exist_in_registry():
    registered = _registered_tool_names()
    assert registered, "No se encontró ningún MCPTool.name en mcp_servers"
    missing: list[str] = []
    for category, plan in CATEGORY_PLAN.items():
        for _server, tool, _kind in plan:
            if tool not in registered:
                missing.append(f"{category}:{tool}")
    assert not missing, (
        f"CATEGORY_PLAN referencia tools NO registrados en mcp_servers: {missing}"
    )
