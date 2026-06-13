"""Tests API op.cont.3 · registro de pruebas de continuidad · feat/fulkro-100 Ola D."""
from __future__ import annotations

import uuid

import pytest

pytestmark = pytest.mark.real_auth

_BASE = "/api/v1/admin/projects"


async def _login_owner(async_client) -> str:
    res = await async_client.post("/api/v1/_dev/login-as-marcos")
    assert res.status_code == 200, res.text
    return async_client.cookies.get("fulkro_csrf") or ""


def _url(project_id: str, suffix: str = "") -> str:
    return f"{_BASE}/{project_id}/continuity-tests/executions{suffix}"


@pytest.mark.asyncio
async def test_requires_owner(async_client):
    res = await async_client.get(_url(str(uuid.uuid4())))
    assert res.status_code in (401, 403), res.text


@pytest.mark.asyncio
async def test_create_unknown_project_404(async_client):
    csrf = await _login_owner(async_client)
    res = await async_client.post(
        _url(str(uuid.uuid4())),
        json={
            "fecha_prueba": "2026-06-10T09:00:00Z",
            "escenario": "Restauración backup completo",
            "resultado": "pass",
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 404, res.text


@pytest.mark.asyncio
async def test_create_invalid_resultado_422(async_client, db):
    from backend.tests.conftest import setup_test_project

    _, project_id = await setup_test_project(db)
    csrf = await _login_owner(async_client)
    res = await async_client.post(
        _url(project_id),
        json={
            "fecha_prueba": "2026-06-10T09:00:00Z",
            "escenario": "X",
            "resultado": "exito",  # fuera de pass/parcial/fail
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 422, res.text


@pytest.mark.asyncio
async def test_create_and_list(async_client, db):
    from backend.tests.conftest import setup_test_project

    _, project_id = await setup_test_project(db)
    csrf = await _login_owner(async_client)

    res = await async_client.post(
        _url(project_id),
        json={
            "fecha_prueba": "2026-06-10T09:00:00Z",
            "escenario": "Failover datacenter secundario",
            "resultado": "parcial",
            "hallazgos": "DNS tardó 12 min en propagar",
            "proxima_prueba_due": "2026-12-10",
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 201, res.text
    created = res.json()
    assert created["resultado"] == "parcial"
    assert created["escenario"].startswith("Failover")

    res2 = await async_client.get(_url(project_id))
    assert res2.status_code == 200, res2.text
    rows = res2.json()
    assert len(rows) == 1
    assert rows[0]["id"] == created["id"]


@pytest.mark.asyncio
async def test_list_empty(async_client, db):
    from backend.tests.conftest import setup_test_project

    _, project_id = await setup_test_project(db)
    await _login_owner(async_client)
    res = await async_client.get(_url(project_id))
    assert res.status_code == 200, res.text
    assert res.json() == []


@pytest.mark.asyncio
async def test_update_and_history(async_client, db):
    from backend.tests.conftest import setup_test_project

    _, project_id = await setup_test_project(db)
    csrf = await _login_owner(async_client)

    # 2 pruebas: una pass, una fail.
    for resultado in ("pass", "fail"):
        r = await async_client.post(
            _url(project_id),
            json={
                "fecha_prueba": "2026-06-10T09:00:00Z",
                "escenario": f"escenario {resultado}",
                "resultado": resultado,
            },
            headers={"X-CSRF-Token": csrf},
        )
        assert r.status_code == 201, r.text
    last_id = r.json()["id"]

    # PATCH: corrige el resultado fail → parcial + añade hallazgos.
    patch = await async_client.patch(
        _url(project_id, f"/{last_id}"),
        json={"resultado": "parcial", "hallazgos": "Recuperado tras 2º intento"},
        headers={"X-CSRF-Token": csrf},
    )
    assert patch.status_code == 200, patch.text
    assert patch.json()["resultado"] == "parcial"

    # History: 2 pruebas · pass_rate 50% (1 pass de 2).
    hist = await async_client.get(
        f"{_BASE}/{project_id}/continuity-tests/history",
    )
    assert hist.status_code == 200, hist.text
    data = hist.json()
    assert data["total_pruebas"] == 2
    assert data["pass_rate"] == 50
