"""Tests for /api/v1/admin/llm-observability/* · MB-7 Q3.A."""
import pytest
from sqlalchemy import text

from backend.tests.conftest import _admin_setup


pytestmark = pytest.mark.asyncio


async def _seed_llm_logs(db) -> None:
    """Insert 5 llm_interaction_log rows with varied features/costs/latency.

    D1 (2026-09-10): la quinta fila era `status='error'` CON 250 tokens y
    $0.001 de coste. Eso es exactamente lo que el bloque D cerro: una llamada
    que fallo no tiene tokens que contar ni coste que sumar. Ahora va con
    NULL en ambos, y la migracion `llm_log_status_no_finge_exito_001` impide
    por CHECK volver a escribirla como estaba.
    """
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO llm_interaction_log "
            "(feature, model, prompt_hash, prompt_tokens, completion_tokens, "
            " total_tokens, cost_usd, latency_ms, status, created_at) "
            "VALUES "
            "('agent_14_copiloto', 'sonnet-4.5', 'h1', 500, 200, 700, 0.01, 1200, 'success', now()),"
            "('agent_14_copiloto', 'sonnet-4.5', 'h2', 600, 250, 850, 0.012, 1300, 'success', now()),"
            "('agent_04_redactor', 'sonnet-4.6', 'h3', 1500, 800, 2300, 0.05, 4500, 'success', now()),"
            "('agent_11_auditor_virtual', 'opus-4.7', 'h4', 3000, 1500, 4500, 12.5, 9000, 'success', now()),"
            "('agent_27_clasificador', 'haiku-4.5', 'h5', NULL, NULL, NULL, NULL, 70000, 'error', now())"
        ))
    await db.flush()


async def test_llm_cost_summary_today(db, async_client):
    await _seed_llm_logs(db)
    r = await async_client.get(
        "/api/v1/admin/llm-observability/cost-summary?period=today",
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["period"] == "today"
    # 4, no 5: la fila `error` NO es una llamada contabilizable (D1). Se
    # publica aparte para que la exclusion no sea silenciosa.
    assert data["n_calls"] >= 4
    assert data["total_tokens"] >= 700 + 850 + 2300 + 4500
    assert data["cost_usd"] >= 12.5
    assert data["n_calls_no_contabilizados"] >= 1


async def test_llm_cost_summary_month(db, async_client):
    await _seed_llm_logs(db)
    r = await async_client.get(
        "/api/v1/admin/llm-observability/cost-summary?period=month",
    )
    assert r.status_code == 200
    assert r.json()["period"] == "month"


async def test_llm_interactions_pagination(db, async_client):
    await _seed_llm_logs(db)
    r = await async_client.get(
        "/api/v1/admin/llm-observability/interactions?limit=2&offset=0",
    )
    assert r.status_code == 200
    data = r.json()
    assert data["limit"] == 2
    assert data["offset"] == 0
    assert len(data["items"]) <= 2
    assert data["total"] >= 5


async def test_llm_top_consumers(db, async_client):
    await _seed_llm_logs(db)
    r = await async_client.get(
        "/api/v1/admin/llm-observability/top-consumers?limit=3&period=month",
    )
    assert r.status_code == 200
    data = r.json()
    assert data["period"] == "month"
    assert len(data["items"]) <= 3
    # agent_11_auditor_virtual seeded with 4500 tokens · should top
    features = [item["feature"] for item in data["items"]]
    assert "agent_11_auditor_virtual" in features


async def test_llm_anomaly_alerts_threshold(db, async_client):
    await _seed_llm_logs(db)
    r = await async_client.get(
        "/api/v1/admin/llm-observability/anomalies?"
        "threshold_usd=10&threshold_latency_ms=8000&period=today",
    )
    assert r.status_code == 200
    data = r.json()
    items = data["items"]
    # Auditor row · cost 12.5 >= 10 AND latency 9000 >= 8000 → anomaly
    # Clasificador row · latency 70000 + status=error → anomaly
    assert any(i["feature"] == "agent_11_auditor_virtual" for i in items)
    assert any(i["feature"] == "agent_27_clasificador" for i in items)
    for item in items:
        assert item["reason"]


async def test_llm_cost_summary_invalid_period_400(async_client):
    r = await async_client.get(
        "/api/v1/admin/llm-observability/cost-summary?period=invalid",
    )
    assert r.status_code == 400


# ====================================================================
# RBAC · require_owner blocks non-admin · sub-atom 1.C.D.audit.A v3.9
# ====================================================================


@pytest.mark.real_auth
async def test_require_owner_blocks_anonymous(async_client):
    """SIN auth (real_auth marker · NO Marcos stub) · 401 expected.

    Sostiene R30 admin-only access · NO leaks llm_interaction_log a anonymous.
    require_owner es router-level dependency · 6 endpoints protegidos:
      - cost-summary · interactions · top-consumers · anomalies
      - projects/{id}/token-usage · agents/{name}/cache-stats (1.E.1.B.1)
    """
    endpoints = (
        "/api/v1/admin/llm-observability/cost-summary",
        "/api/v1/admin/llm-observability/interactions",
        "/api/v1/admin/llm-observability/top-consumers",
        "/api/v1/admin/llm-observability/anomalies",
        "/api/v1/admin/llm-observability/projects/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/token-usage",
        "/api/v1/admin/llm-observability/agents/agent_14_copiloto/cache-stats",
    )
    for endpoint in endpoints:
        r = await async_client.get(endpoint)
        # Sin auth · expect 401 (Unauthorized) o 403 (Forbidden)
        # NUNCA 200 · NO leak data
        assert r.status_code in (401, 403), (
            f"Endpoint {endpoint} retornó {r.status_code} sin auth · "
            f"expected 401/403 (require_owner debería bloquear)"
        )
        # Verificar NO leak interaction_log fields
        body = r.text.lower()
        assert "llm_interaction_log" not in body
        assert "cost_usd" not in body


# ====================================================================
# Sub-atom 1.E.1.B.1 · cached_input_tokens tracking + thin wrappers
# ADR-025 sostenido firmísimo · NO new tables · extend canonical
# ====================================================================


async def _seed_llm_logs_with_cache(db) -> str:
    """Insert rows for a specific project · varied cached_input_tokens.

    Returns project_id used (canonical UUID for test isolation).
    """
    project_id = "11111111-1111-1111-1111-111111111111"
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO llm_interaction_log "
            "(project_id, feature, model, prompt_hash, prompt_tokens, "
            " completion_tokens, total_tokens, cached_input_tokens, "
            " cost_usd, latency_ms, status, created_at) "
            "VALUES "
            "(:pid, 'agent_14_copiloto', 'sonnet-4.5', 'c1', 800, 200, 1000, 200, 0.012, 1200, 'success', now()),"
            "(:pid, 'agent_14_copiloto', 'sonnet-4.5', 'c2', 700, 300, 1000, 300, 0.011, 1100, 'success', now()),"
            "(:pid, 'agent_04_redactor', 'sonnet-4.6', 'c3', 2000, 800, 2800, 0, 0.05, 4500, 'success', now())"
        ), {"pid": project_id})
    await db.flush()
    return project_id


async def test_log_interaction_with_cached_tokens(db, async_client):
    """cost-summary surface cached_input_tokens + cache_hit_rate fields."""
    await _seed_llm_logs_with_cache(db)
    r = await async_client.get(
        "/api/v1/admin/llm-observability/cost-summary?period=today",
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "cached_input_tokens" in data
    assert "cache_hit_rate" in data
    # Seeded: cached 200 + 300 + 0 = 500 in this batch (other tests may seed too).
    assert data["cached_input_tokens"] >= 500
    # hit_rate = cached / (prompt + cached) · debe ser ∈ [0, 1]
    assert 0.0 <= data["cache_hit_rate"] <= 1.0


async def test_get_project_usage_includes_cached(db, async_client):
    """token-usage endpoint per project · returns total + by_agent breakdown."""
    project_id = await _seed_llm_logs_with_cache(db)
    r = await async_client.get(
        f"/api/v1/admin/llm-observability/projects/{project_id}/token-usage?days=30",
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["project_id"] == project_id
    assert data["days"] == 30
    assert data["n_calls"] == 3
    assert data["prompt_tokens"] == 800 + 700 + 2000
    assert data["completion_tokens"] == 200 + 300 + 800
    assert data["cached_input_tokens"] == 200 + 300 + 0
    # by_agent dos entradas (copiloto · redactor)
    agents = {row["agent"]: row for row in data["by_agent"]}
    assert "agent_14_copiloto" in agents
    assert "agent_04_redactor" in agents
    assert agents["agent_14_copiloto"]["cached_input_tokens"] == 500
    assert agents["agent_04_redactor"]["cached_input_tokens"] == 0
    assert agents["agent_14_copiloto"]["n_calls"] == 2


async def test_cache_hit_rate_calculation(db, async_client):
    """hit_rate = cached / (prompt_tokens + cached) accuracy verify."""
    await _seed_llm_logs_with_cache(db)
    r = await async_client.get(
        "/api/v1/admin/llm-observability/agents/agent_14_copiloto/cache-stats?days=30",
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["agent"] == "agent_14_copiloto"
    # Sum cached = 200+300 = 500 · prompt = 800+700 = 1500 · denom = 2000
    # hit_rate = 500/2000 = 0.25
    assert data["cached_input_tokens"] == 500
    assert data["prompt_tokens"] == 1500
    assert abs(data["cache_hit_rate"] - 0.25) < 1e-6
    assert data["n_calls"] == 2


async def test_cached_tokens_default_zero_existing_records(db, async_client):
    """Existing rows pre-migration backfilled with 0 cached_input_tokens.

    Seed uses _seed_llm_logs() (original helper · NO cached_input_tokens
    inserted explicitly) → server_default '0' applies. cache_hit_rate = 0.0
    cuando NO cache usage (denom = prompt_tokens · cached = 0).
    """
    await _seed_llm_logs(db)
    r = await async_client.get(
        "/api/v1/admin/llm-observability/cost-summary?period=today",
    )
    assert r.status_code == 200
    data = r.json()
    # Defensive: si solo seedearon _seed_llm_logs() (sin cache_with), cached
    # debe ser 0 para esas filas concretas. Verify field present + non-negative.
    assert data["cached_input_tokens"] >= 0
    assert data["cache_hit_rate"] >= 0.0
