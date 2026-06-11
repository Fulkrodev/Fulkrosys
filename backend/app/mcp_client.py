"""MCP client base — FASE 9.C.

Wrapper para invocar tools de MCP servers (JSON-RPC 2.0 over stdio)
desde el backend FastAPI.

Soporta feature flag USE_MCP_REAL (default false):

- USE_MCP_REAL=false: invoke_mcp devuelve un dict stub
  {"_fallback": True, ...} y los callers degradan al runner subprocess
  legacy. Comportamiento por defecto en dev/CI.
- USE_MCP_REAL=true: spawn del server.py via asyncio.create_subprocess_exec
  y dialogo JSON-RPC 2.0 sobre stdin/stdout. Cada llamada inicializa
  conexion -> tools/call -> read response -> close.

Protocolo (vease backend/mcp_servers/shared/mcp_protocol.py):

    {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
    {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
     "params": {"name": "<tool>", "arguments": {...}}}

Scope enforcement:
- Cada server tool ya invoca shared.scope_check.check_scope antes
  de ejecutar el binario. invoke_mcp no duplica el check; la auth
  se propaga via env var PENTEST_AUTHORIZATION que el server.py
  process hereda al spawn.

Errores: MCPInvocationError envuelve cualquier fallo (server crash,
timeout, JSON parse, JSON-RPC error). Los callers deben hacer fallback
a su runner legacy.

TODO-FASE-13-MCPS-FULL-MIGRATION-001: Tier 3 (full migration de todos
los runners M08+M21 con eliminacion del path subprocess legacy) queda
documentado para hardening pre-deploy.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


def use_mcp_real() -> bool:
    """Devuelve settings.use_mcp_real (env var FULKRO_USE_MCP_REAL · pydantic).

    Migrado de os.getenv directo a settings pattern · SAN-B.MB-7.1.
    Honra overrides via env var en tests sin reload settings (pydantic
    Settings.model_config: env_file = .env reload por test fixture).
    """
    # Reload settings cada call para tests que muten env var en runtime
    # (existing test_mcp_client.py::test_use_mcp_real_truthy_values pattern).
    return os.getenv("USE_MCP_REAL", "false").lower() in ("true", "1", "yes")


async def try_invoke_mcp_or_none(
    server: str,
    tool: str,
    args: dict,
    timeout_seconds: int = 600,
) -> dict | None:
    """Helper para runners m08: invoca MCP si flag activo, devuelve None
    si fallback (caller usa runner directo).

    Returns:
        - dict con MCP response (data + meta) si wrapper exitoso
        - None si flag off, MCP no disponible, o invocación falló
          (caller responsabilidad: hacer fallback runner directo)

    Refs: SAN-B.MB-7.1 wire-up pattern uniforme 8 runners.
    """
    if not use_mcp_real():
        return None
    try:
        mcp_resp = await invoke_mcp(MCPInvocation(
            server=server, tool=tool, args=args, timeout_seconds=timeout_seconds,
        ))
        if mcp_resp.get("_fallback") or mcp_resp.get("_unavailable"):
            return None
        return mcp_resp
    except (MCPInvocationError, FileNotFoundError, OSError) as exc:
        # Ejecutable 8 Pasada 16 (a · código): el contrato `or_none` exige degradación
        # graceful → runner directo. Antes solo capturaba MCPInvocationError; si docker/MCP
        # no está disponible (FileNotFoundError "docker not available" / OSError subprocess),
        # propagaba y rompía el flujo. Ahora también degrada a None (fallback runner directo).
        logger.warning(
            "MCP wrapper %s/%s failed · fallback runner directo: %s",
            server, tool, exc,
        )
        return None


# Mapeo server -> ruta absoluta a server.py.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_MCP_SERVERS_DIR = _REPO_ROOT / "backend" / "mcp_servers"

_KNOWN_SERVERS = {
    "scope_enforcer": _MCP_SERVERS_DIR / "scope_enforcer" / "server.py",
    "recon": _MCP_SERVERS_DIR / "recon" / "server.py",
    "webpentest": _MCP_SERVERS_DIR / "webpentest" / "server.py",
    "vulnscan": _MCP_SERVERS_DIR / "vulnscan" / "server.py",
    "infra": _MCP_SERVERS_DIR / "infra" / "server.py",
    "redteam": _MCP_SERVERS_DIR / "redteam" / "server.py",
    "cloud": _MCP_SERVERS_DIR / "cloud" / "server.py",
    "config": _MCP_SERVERS_DIR / "config" / "server.py",
    "phishing": _MCP_SERVERS_DIR / "phishing" / "server.py",
    "apisec": _MCP_SERVERS_DIR / "apisec" / "server.py",
    "mobile": _MCP_SERVERS_DIR / "mobile" / "server.py",
    "wireless": _MCP_SERVERS_DIR / "wireless" / "server.py",
    "cracking": _MCP_SERVERS_DIR / "cracking" / "server.py",
    "sast": _MCP_SERVERS_DIR / "sast" / "server.py",
}


# ── Matriz de capacidades por host (honesta · NUNCA finge un resultado) ──────
# tool-based: el scanner corre REAL si su binario está presente (shutil.which).
# hardware/infra-bound: NO ejecutables en un VPS cloud (requieren hardware
# dedicado o infra ofensiva aparte). Se reportan con su razón física · jamás
# producen un finding falso ni rompen el flujo (invoke_mcp corta limpio).
_SCANNER_REQUIRED_TOOL: dict[str, str | None] = {
    "scope_enforcer": None,   # Python puro · siempre disponible
    "recon": "nmap",
    "vulnscan": "nuclei",
    "webpentest": "testssl.sh",   # ZAP profundo corre en contenedor aparte (perfil scanner)
    "infra": "nmap",
    "config": "lynis",
    "cloud": "prowler",
    "apisec": "nuclei",
    "sast": "semgrep",
}
# Servicios de engagement ESPECIALIZADO (bajo demanda · infra/hardware dedicado).
# NO son escaneo cloud automatizado ni placeholders: son un tier distinto que se
# activa por engagement con su propia máquina/infra (y consentimiento explícito en
# los ofensivos). Cada uno con su vía REAL de activación documentada.
_DEDICATED_ENGAGEMENT: dict[str, dict[str, str]] = {
    "wireless": {
        "reason": "WiFi en modo monitor (antena física · prueba on-site presencial)",
        "alternative": "engagement on-site con adaptador WiFi — por naturaleza NO es remoto",
    },
    "cracking": {
        "reason": "cracking de hashes (hashcat · requiere GPU)",
        "alternative": "box GPU on-demand levantada solo durante el engagement y destruida al cerrar",
    },
    "mobile": {
        "reason": "análisis de apps móviles (emulador/dispositivo Android/iOS)",
        "alternative": "device farm (BrowserStack / AWS Device Farm) o box dedicada por engagement",
    },
    "phishing": {
        "reason": "campañas de phishing (dominios + infra de envío · ofensivo · requiere consentimiento explícito)",
        "alternative": "GoPhish en VM dedicada + dominios del engagement",
    },
    "redteam": {
        "reason": "adversary emulation / C2 (ofensivo · requiere reglas de enfrentamiento firmadas)",
        "alternative": "infra C2 dedicada por engagement",
    },
}


def _offensive_provisionable(server: str) -> bool:
    """True si el provisioner ofensivo on-demand está configurado y el tier es
    cloud-provisionable (wireless NO · es físico on-site). Chequea Settings sin
    importar el módulo m08 (evita ciclo)."""
    if server == "wireless":
        return False
    try:
        from backend.app.config import get_settings
        s = get_settings()
        token = s.hetzner_cloud_token.get_secret_value()
        return bool(getattr(s, "offensive_provisioner_enabled", False)) and bool(token)
    except Exception:
        return False


def scanner_capability(server: str) -> dict[str, Any]:
    """Declara si un MCP scanner puede correr REAL en este host.

    Honesto y determinista. NUNCA finge un resultado:
    - on_demand_engagement → ``available=False`` (tier dedicado · NO cloud
      automático) con su razón + vía de activación real. Si el provisioner
      ofensivo está configurado, ``provisionable_on_demand=True`` (la box se
      levanta y se destruye sola para el engagement autorizado).
    - tool-based → ``available=True`` solo si el binario está presente.
    """
    if server in _DEDICATED_ENGAGEMENT:
        info = _DEDICATED_ENGAGEMENT[server]
        return {
            "server": server, "available": False, "kind": "on_demand_engagement",
            "reason": info["reason"], "alternative": info["alternative"],
            "provisionable_on_demand": _offensive_provisionable(server),
        }
    tool = _SCANNER_REQUIRED_TOOL.get(server)
    if tool is None:
        return {"server": server, "available": True, "kind": "builtin", "reason": ""}
    present = shutil.which(tool) is not None
    return {
        "server": server, "available": present, "kind": "tool", "tool": tool,
        "reason": "" if present else f"herramienta '{tool}' no instalada en este host",
    }


def scanner_capabilities() -> dict[str, dict[str, Any]]:
    """Matriz completa de capacidades por scanner (para autopilot / report / UI)."""
    return {s: scanner_capability(s) for s in _KNOWN_SERVERS}


class MCPInvocationError(Exception):
    """Error invocando un MCP server (spawn, protocolo, timeout)."""


class MCPInvocation(BaseModel):
    """Argumentos para una llamada MCP."""

    server: str = Field(..., description="Nombre MCP server (recon, webpentest...)")
    tool: str = Field(..., description="Tool name dentro del server (nmap_scan, zap_spider_scan...)")
    args: dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: int = Field(default=600, ge=1, le=3600)


def _resolve_server_path(server: str) -> Path:
    if server not in _KNOWN_SERVERS:
        raise MCPInvocationError(
            f"MCP server {server!r} desconocido. Disponibles: {sorted(_KNOWN_SERVERS)}"
        )
    path = _KNOWN_SERVERS[server]
    if not path.exists():
        raise MCPInvocationError(f"MCP server {server!r} no encontrado en {path}")
    return path


async def _send_recv(proc: asyncio.subprocess.Process, request: dict, timeout: float) -> dict:
    """Envia un JSON-RPC request y devuelve el response decodificado."""
    if proc.stdin is None or proc.stdout is None:
        raise MCPInvocationError("MCP server proc sin stdin/stdout")
    payload = (json.dumps(request) + "\n").encode()
    proc.stdin.write(payload)
    await proc.stdin.drain()
    try:
        line = await asyncio.wait_for(proc.stdout.readline(), timeout=timeout)
    except asyncio.TimeoutError as exc:
        raise MCPInvocationError(f"timeout leyendo respuesta MCP ({timeout}s)") from exc
    if not line:
        raise MCPInvocationError("MCP server cerro stdout sin respuesta")
    try:
        return json.loads(line.decode().strip())
    except json.JSONDecodeError as exc:
        raise MCPInvocationError(f"respuesta MCP no es JSON: {line[:200]!r}") from exc


async def invoke_mcp(invocation: MCPInvocation) -> dict[str, Any]:
    """Invoca tool en un MCP server.

    Si USE_MCP_REAL=false: devuelve dict stub indicando fallback. Los
    callers deben usar su runner legacy.

    Si USE_MCP_REAL=true: spawn server.py via subprocess, dialogo
    JSON-RPC initialize -> tools/call, devuelve el result del
    response (parsed JSON con content+meta).

    Raises:
        MCPInvocationError: cualquier fallo de spawn / protocolo / timeout.
    """
    if not use_mcp_real():
        return {
            "_fallback": True,
            "server": invocation.server,
            "tool": invocation.tool,
            "reason": "USE_MCP_REAL=false (default)",
        }

    # Capacidad por host: si el scanner no puede correr REAL aquí (hardware/infra
    # bound, o binario ausente), cortamos LIMPIO con su razón física · NUNCA se
    # intenta un subprocess condenado ni se finge un resultado.
    cap = scanner_capability(invocation.server)
    if not cap["available"]:
        return {
            "_unavailable": True,
            "server": invocation.server,
            "tool": invocation.tool,
            "kind": cap.get("kind"),
            "reason": cap["reason"],
        }

    server_path = _resolve_server_path(invocation.server)
    server_dir = server_path.parent
    mcp_servers_root = _MCP_SERVERS_DIR

    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    sep = ";" if sys.platform == "win32" else ":"
    env["PYTHONPATH"] = f"{mcp_servers_root}{sep}{existing}" if existing else str(mcp_servers_root)

    proc = await asyncio.create_subprocess_exec(
        sys.executable, str(server_path),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
        cwd=str(server_dir),
    )

    try:
        # 1. initialize handshake
        init_resp = await _send_recv(
            proc,
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            timeout=10.0,
        )
        if "error" in init_resp:
            raise MCPInvocationError(f"initialize fallo: {init_resp['error']}")

        # 2. tools/call
        call_resp = await _send_recv(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": invocation.tool, "arguments": invocation.args},
            },
            timeout=float(invocation.timeout_seconds),
        )
        if "error" in call_resp:
            raise MCPInvocationError(f"tools/call fallo: {call_resp['error']}")

        result = call_resp.get("result", {})
        # Decodificamos el primer content text si es JSON.
        contents = result.get("content", [])
        decoded: dict | None = None
        if contents and isinstance(contents, list):
            text = (contents[0] or {}).get("text", "")
            if text:
                try:
                    decoded = json.loads(text)
                except json.JSONDecodeError:
                    decoded = {"raw_text": text}
        return {
            "_fallback": False,
            "server": invocation.server,
            "tool": invocation.tool,
            "data": decoded,
            "meta": result.get("meta", {}),
        }
    finally:
        try:
            if proc.stdin and not proc.stdin.is_closing():
                proc.stdin.close()
        except Exception:
            pass
        try:
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
        except Exception:
            pass


__all__ = [
    "MCPInvocation",
    "MCPInvocationError",
    "invoke_mcp",
    "scanner_capabilities",
    "scanner_capability",
    "try_invoke_mcp_or_none",
    "use_mcp_real",
]
