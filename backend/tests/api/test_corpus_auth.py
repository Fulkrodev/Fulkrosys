"""Corpus endpoints require_owner · audit-roundup-W3 §1.4 (clase w2p).

backend/app/api/v1/corpus.py se montaba SIN require_owner → cualquier sesión
autenticada (incluido el pool cliente) podía llamar GET /api/v1/corpus/search
y /stats. Igual que mcps.py/projects.py, ahora exige owner.

Verifica:
1. Una sesión del pool CLIENTE es rechazada (NO 200) en search + stats.
2. La sesión Marcos/owner (override autouse) sigue alcanzando el endpoint
   (no es rechazada por auth · 200 con el corpus vacío de test).
"""
from __future__ import annotations

import uuid

import pytest


class _StubClientUser:
    """Stub ClientUser (pool cliente) para forzar role_pool='cliente'."""

    email = "cliente@example.com"
    role = "client_user"
    id = uuid.uuid4()
    client_id = uuid.uuid4()
    is_active = True


@pytest.fixture
async def client_pool_session(async_client):
    """Override authenticate_request con un subject del pool CLIENTE.

    Reemplaza el override Marcos por defecto (autouse) para este test.
    """
    from backend.app.main import app
    from backend.app.auth.global_dep import AuthSubject, authenticate_request

    async def _override(request):
        subject = AuthSubject(user=_StubClientUser(), role_pool="cliente")
        request.state.auth_subject = subject
        request.state.auth_payload = {"sub": str(_StubClientUser.id), "jti": "x"}
        return subject

    app.dependency_overrides[authenticate_request] = _override
    yield async_client
    app.dependency_overrides.pop(authenticate_request, None)


@pytest.mark.asyncio
async def test_corpus_search_rejects_client_pool_session(client_pool_session):
    """Sesión cliente NO puede listar el corpus (require_owner)."""
    resp = await client_pool_session.get("/api/v1/corpus/search?q=esquema")
    assert resp.status_code in (401, 403), resp.text
    assert resp.status_code != 200


@pytest.mark.asyncio
async def test_corpus_stats_rejects_client_pool_session(client_pool_session):
    """Sesión cliente NO puede ver stats del corpus (require_owner)."""
    resp = await client_pool_session.get("/api/v1/corpus/stats")
    assert resp.status_code in (401, 403), resp.text
    assert resp.status_code != 200


@pytest.mark.asyncio
async def test_corpus_stats_allows_owner_session(async_client):
    """Sesión Marcos/owner (override autouse) alcanza el endpoint (no rechazada)."""
    resp = await async_client.get("/api/v1/corpus/stats")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "documents" in data
    assert "chunks" in data
