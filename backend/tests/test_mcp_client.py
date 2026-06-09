"""Tests MCP client base — Sub-bloque 9.C."""
from __future__ import annotations

import os

import pytest

from backend.app.mcp_client import (
    MCPInvocation,
    MCPInvocationError,
    invoke_mcp,
    use_mcp_real,
)


@pytest.mark.asyncio
async def test_invoke_mcp_returns_fallback_when_flag_disabled(monkeypatch):
    """USE_MCP_REAL=false (default) -> devuelve _fallback dict, no spawnea proceso."""
    monkeypatch.delenv("USE_MCP_REAL", raising=False)
    assert use_mcp_real() is False

    inv = MCPInvocation(server="recon", tool="nmap_scan", args={"target": "127.0.0.1"})
    result = await invoke_mcp(inv)

    assert result["_fallback"] is True
    assert result["server"] == "recon"
    assert result["tool"] == "nmap_scan"
    assert "USE_MCP_REAL" in result["reason"]


@pytest.mark.asyncio
async def test_invoke_mcp_returns_fallback_when_flag_false_explicit(monkeypatch):
    """USE_MCP_REAL=false explicito -> mismo fallback dict."""
    monkeypatch.setenv("USE_MCP_REAL", "false")
    assert use_mcp_real() is False

    inv = MCPInvocation(server="webpentest", tool="zap_spider_scan", args={"url": "http://example.com"})
    result = await invoke_mcp(inv)

    assert result["_fallback"] is True
    assert result["server"] == "webpentest"


@pytest.mark.asyncio
async def test_invoke_mcp_unknown_server_raises_when_real(monkeypatch):
    """USE_MCP_REAL=true + server desconocido -> MCPInvocationError."""
    monkeypatch.setenv("USE_MCP_REAL", "true")
    assert use_mcp_real() is True

    inv = MCPInvocation(server="not_a_real_server", tool="whatever", args={})
    with pytest.raises(MCPInvocationError, match="desconocido"):
        await invoke_mcp(inv)


def test_use_mcp_real_truthy_values(monkeypatch):
    """use_mcp_real lee env var con varios valores truthy."""
    for truthy in ("true", "True", "TRUE", "1", "yes", "YES"):
        monkeypatch.setenv("USE_MCP_REAL", truthy)
        assert use_mcp_real() is True, f"falla para {truthy!r}"

    for falsy in ("false", "0", "no", "", "anything_else"):
        monkeypatch.setenv("USE_MCP_REAL", falsy)
        assert use_mcp_real() is False, f"falla para {falsy!r}"


def test_mcp_invocation_pydantic_validation():
    """MCPInvocation valida timeout_seconds en rango [1, 3600]."""
    inv = MCPInvocation(server="recon", tool="nmap_scan", args={"target": "x"})
    assert inv.timeout_seconds == 600  # default
    assert inv.args == {"target": "x"}

    inv2 = MCPInvocation(server="recon", tool="nmap_scan", args={}, timeout_seconds=1800)
    assert inv2.timeout_seconds == 1800

    with pytest.raises(Exception):  # pydantic ValidationError
        MCPInvocation(server="recon", tool="nmap_scan", timeout_seconds=99999)


# ════════════════════════════════════════════════════════════════════
# SAN-B.MB-7.1 · try_invoke_mcp_or_none helper + 4 wrappers nuevos
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_try_invoke_mcp_or_none_returns_none_when_flag_off(monkeypatch):
    """USE_MCP_REAL=false → helper retorna None (caller usa runner directo)."""
    from backend.app.mcp_client import try_invoke_mcp_or_none

    monkeypatch.setenv("USE_MCP_REAL", "false")
    result = await try_invoke_mcp_or_none(
        server="infra", tool="lynis_audit", args={"target": "localhost"},
    )
    assert result is None


@pytest.mark.asyncio
async def test_try_invoke_mcp_or_none_returns_none_when_fallback(monkeypatch):
    """USE_MCP_REAL=true pero invoke_mcp retorna _fallback → None."""
    from backend.app.mcp_client import try_invoke_mcp_or_none

    # Mock invoke_mcp para devolver fallback (simula MCP unavailable runtime)
    async def fake_invoke(_inv):
        return {"_fallback": True, "reason": "mocked"}

    monkeypatch.setenv("USE_MCP_REAL", "true")
    monkeypatch.setattr("backend.app.mcp_client.invoke_mcp", fake_invoke)

    result = await try_invoke_mcp_or_none(
        server="infra", tool="lynis_audit", args={"target": "localhost"},
    )
    assert result is None


@pytest.mark.asyncio
async def test_try_invoke_mcp_or_none_returns_response_when_success(monkeypatch):
    """USE_MCP_REAL=true + invoke_mcp success → retorna dict response."""
    from backend.app.mcp_client import try_invoke_mcp_or_none

    fake_response = {
        "_fallback": False,
        "server": "infra",
        "tool": "lynis_audit",
        "data": {"findings": [{"name": "test", "severity": "high"}]},
        "meta": {},
    }

    async def fake_invoke(_inv):
        return fake_response

    monkeypatch.setenv("USE_MCP_REAL", "true")
    monkeypatch.setattr("backend.app.mcp_client.invoke_mcp", fake_invoke)

    result = await try_invoke_mcp_or_none(
        server="infra", tool="lynis_audit", args={"target": "localhost"},
    )
    assert result == fake_response


@pytest.mark.asyncio
async def test_try_invoke_mcp_or_none_swallows_invocation_error(monkeypatch):
    """MCPInvocationError caught por helper → None (caller fallback)."""
    from backend.app.mcp_client import (
        MCPInvocationError, try_invoke_mcp_or_none,
    )

    async def fake_invoke(_inv):
        raise MCPInvocationError("simulated server crash")

    monkeypatch.setenv("USE_MCP_REAL", "true")
    monkeypatch.setattr("backend.app.mcp_client.invoke_mcp", fake_invoke)

    result = await try_invoke_mcp_or_none(
        server="infra", tool="lynis_audit", args={"target": "localhost"},
    )
    assert result is None


def test_4_new_wrappers_known_servers_present():
    """SAN-B.MB-7.1: 4 nuevos tools registrables en KNOWN_SERVERS infra/webpentest/recon/cracking."""
    from backend.app.mcp_client import _KNOWN_SERVERS

    # Los 4 servers target deben existir en la lista
    for server_name in ("infra", "webpentest", "recon", "cracking"):
        assert server_name in _KNOWN_SERVERS, f"{server_name} no en KNOWN_SERVERS"


def test_4_new_tool_files_exist_on_disk():
    """SAN-B.MB-7.1: verifica los 4 wrappers creados existen en filesystem."""
    from pathlib import Path

    base = Path(__file__).resolve().parents[1] / "mcp_servers"
    expected = [
        base / "infra" / "tools" / "lynis_tool.py",
        base / "webpentest" / "tools" / "testssl_tool.py",
        base / "recon" / "tools" / "dns_checker_tool.py",
        base / "cracking" / "tools" / "ad_password_check_tool.py",
    ]
    missing = [str(p) for p in expected if not p.exists()]
    assert not missing, f"Wrappers faltantes: {missing}"