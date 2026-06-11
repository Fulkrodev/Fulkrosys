"""F-13-01 · rate-limit cliente wired en m11_copiloto/portal_api.py.

El router ``portal_api`` (consumido por ``frontend/lib/api/copiloto.ts``) carecía
de rate-limit, dejando los caps token/coste/mes (CLIENTE_CAPS, 100 msgs/día)
evadibles por esa vía mientras los stubs sí lo aplicaban. Aquí verificamos:

  - Superado el cap diario → 429 en superficies LLM (/chat, /chat/stream, /coach)
    y en /quick-actions (defense-in-depth · UX coherente).
  - Bajo el cap → 200 normal.

Caps derivados on-query de ``llm_interaction_log`` (ADR-025 · sin tablas nuevas).
Mirror del patrón de ``api/v1/client_copilot_stub.py``.
"""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.tests.conftest import _admin_setup


@pytest.fixture
async def authed_client_user(async_client: AsyncClient, db: AsyncSession):
    from backend.app.main import app
    from backend.app.motors.m21_portal_cliente.api import get_current_client_user
    from backend.tests.conftest import setup_test_project

    # R09: el cap del cliente es POR PROYECTO · el stub necesita un proyecto real
    # en BD para que el endpoint lo resuelva server-side y aplique el cap.
    client_id, project_id = await setup_test_project(db)

    class _StubClienteUser:
        id = uuid.UUID("00000000-0000-0000-0000-0000000000a1")
        email = "cliente.ratelimit@example.test"

    stub = _StubClienteUser()
    stub.client_id = client_id
    stub.project_id = uuid.UUID(str(project_id))

    async def _override():
        return stub

    app.dependency_overrides[get_current_client_user] = _override
    yield async_client, stub
    app.dependency_overrides.pop(get_current_client_user, None)


async def _seed_cliente_llm_interactions(
    db: AsyncSession, count: int, project_id,
) -> None:
    """Inserta ``count`` interacciones copiloto_cliente hoy (UTC), vinculadas al
    ``project_id`` del cliente, para empujar el contador diario por-tenant por
    encima del cap (CLIENTE_CAPS=100)."""
    async with _admin_setup(db):
        await db.execute(
            text(
                """
                INSERT INTO llm_interaction_log
                    (feature, model, prompt_hash, prompt_tokens,
                     completion_tokens, total_tokens, latency_ms,
                     cost_usd, project_id, created_at)
                SELECT 'copilot_cliente_1d_b_1', 'haiku-4.5',
                       'h' || g::text, 1, 1, 2, 10, 0.0, :pid, now()
                FROM generate_series(1, :n) AS g
                """
            ),
            {"n": count, "pid": str(project_id)},
        )


# ════════════════════════════════════════════════════════════════════
# Hard-block (cap superado) → 429
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_quick_actions_hard_blocked_returns_429(
    authed_client_user, db: AsyncSession,
) -> None:
    cli, _stub = authed_client_user
    await _seed_cliente_llm_interactions(db, 120, _stub.project_id)  # > 100 cap diario

    resp = await cli.get("/api/v1/client-portal/copiloto/quick-actions")
    assert resp.status_code == 429
    assert "límite" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_chat_hard_blocked_returns_429_before_llm(
    authed_client_user, db: AsyncSession,
) -> None:
    cli, _stub = authed_client_user
    await _seed_cliente_llm_interactions(db, 120, _stub.project_id)

    # enforce ocurre antes de resolver proyecto / llamar LLM → 429 directo
    resp = await cli.post(
        "/api/v1/client-portal/copiloto/chat",
        json={"question": "hola, ¿qué hago ahora?"},
    )
    assert resp.status_code == 429


@pytest.mark.asyncio
async def test_coach_hard_blocked_returns_429(
    authed_client_user, db: AsyncSession,
) -> None:
    cli, _stub = authed_client_user
    await _seed_cliente_llm_interactions(db, 120, _stub.project_id)

    resp = await cli.post(
        "/api/v1/client-portal/copiloto/coach",
        json={"question": "¿cuál es mi siguiente paso?"},
    )
    assert resp.status_code == 429


# ════════════════════════════════════════════════════════════════════
# Bajo el cap → 200 normal
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_quick_actions_under_cap_returns_200(
    authed_client_user, db: AsyncSession,
) -> None:
    cli, _stub = authed_client_user
    # sin interacciones sembradas → messages_today = 0

    resp = await cli.get("/api/v1/client-portal/copiloto/quick-actions")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
