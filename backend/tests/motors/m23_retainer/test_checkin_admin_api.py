"""Retainer check-in ADMIN curación API · feat/fulkro-100 Ola 3.

Cierra el P0: la curación/envío del check-in trimestral ya NO es solo accesible
por tests/Celery — Marcos tiene endpoints admin (list/get/generate/curate/send).
La lógica del ciclo draft→curated→sent está cubierta por los tests del servicio;
aquí se valida el wiring del API + auth (require_owner) + manejo de errores.
"""
from __future__ import annotations

import uuid

import pytest

pytestmark = pytest.mark.real_auth

_ADMIN = "/api/v1/admin/retainer-checkin"


async def _login(async_client) -> str:
    """Login owner real · devuelve el CSRF token (triple-binding POST)."""
    res = await async_client.post("/api/v1/_dev/login-as-marcos")
    assert res.status_code == 200, res.text
    return async_client.cookies.get("fulkro_csrf") or ""


@pytest.mark.asyncio
async def test_requires_owner_auth(async_client):
    """Sin login owner → 401/403 (ADR-013 require_owner a nivel de router)."""
    res = await async_client.get(f"{_ADMIN}/reports/{uuid.uuid4()}")
    assert res.status_code in (401, 403), res.text


@pytest.mark.asyncio
async def test_list_empty_project_returns_empty(async_client, db):
    # FIX(audit 2026-06-13): tras el fix RLS (get_project_owner+set_tenant_context)
    # un project_id inexistente devuelve 404 (correcto · coherente con el resto de
    # endpoints scopeados). El caso "proyecto SIN reports → lista vacía" se prueba
    # con un proyecto REAL.
    from backend.tests.conftest import setup_test_project
    await _login(async_client)
    _, project_id = await setup_test_project(db)
    await db.commit()
    res = await async_client.get(
        f"{_ADMIN}/projects/{project_id}/reports",
    )
    assert res.status_code == 200, res.text
    assert res.json() == []


@pytest.mark.asyncio
async def test_generate_without_active_retainer_400(async_client, db):
    from backend.tests.conftest import setup_test_project
    csrf = await _login(async_client)
    _, project_id = await setup_test_project(db)
    await db.commit()
    res = await async_client.post(
        f"{_ADMIN}/projects/{project_id}/reports/generate",
        json={},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 400, res.text


@pytest.mark.asyncio
async def test_curate_nonexistent_report_404(async_client):
    csrf = await _login(async_client)
    res = await async_client.post(
        f"{_ADMIN}/reports/{uuid.uuid4()}/curate", json={},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 404, res.text


@pytest.mark.asyncio
async def test_send_nonexistent_report_404(async_client):
    csrf = await _login(async_client)
    res = await async_client.post(
        f"{_ADMIN}/reports/{uuid.uuid4()}/send",
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 404, res.text
