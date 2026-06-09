"""Smoke test endpoint /api/v1/mcps/status (Sub-bloque 9.B).

Sin DB, solo registry estatico + auth real (loginAsMarcos).
"""
from __future__ import annotations

import pytest

# Sub-fase 4.D ADR-021: opt-out del autouse override (validamos auth real).
pytestmark = pytest.mark.real_auth


async def _login_marcos(async_client) -> None:
    res = await async_client.post("/api/v1/_dev/login-as-marcos")
    assert res.status_code == 200, res.text


@pytest.mark.asyncio
async def test_mcps_status_returns_200_with_14_items(async_client):
    """GET /mcps/status -> 200 + shape esperado + 14 MCPs registrados."""
    await _login_marcos(async_client)

    res = await async_client.get("/api/v1/mcps/status")
    assert res.status_code == 200, res.text

    data = res.json()
    assert "total" in data
    assert "real_count" in data
    assert "available_count" in data
    assert "coming_soon_count" in data
    assert "blocked_count" in data
    assert "items" in data

    assert data["total"] == 14, f"Esperados 14 MCPs, devuelve {data['total']}"
    assert data["total"] == len(data["items"])

    # Sub-bloque 9.C: scope_enforcer + recon + webpentest en `real`
    # (M08 retest_runner usa MCP servers via JSON-RPC stdio con feature flag
    # USE_MCP_REAL; fallback subprocess transparente si falla la llamada).
    # Resto available -> TODO-FASE-13-MCPS-FULL-MIGRATION-001 (Tier 3).
    assert data["real_count"] == 3
    assert data["available_count"] == 11
    assert data["coming_soon_count"] == 0
    assert data["blocked_count"] == 0

    by_name = {m["name"]: m for m in data["items"]}
    assert by_name["scope_enforcer"]["state"] == "real"
    assert by_name["recon"]["state"] == "real"
    assert by_name["webpentest"]["state"] == "real"
    assert by_name["vulnscan"]["state"] == "available"

    # Comprobamos campos minimos del primer MCP.
    first = data["items"][0]
    for key in (
        "name", "label", "description", "category", "state",
        "version", "docker_image", "tools_count", "last_health_check",
    ):
        assert key in first, f"Falta campo {key} en MCPStatus"

    names = {m["name"] for m in data["items"]}
    expected = {
        "scope_enforcer", "recon", "vulnscan", "webpentest", "infra",
        "redteam", "cloud", "config", "phishing", "apisec", "mobile",
        "wireless", "cracking", "sast",
    }
    assert names == expected, f"Diferencia inventario: {names ^ expected}"
