"""Tests BIA service + API · SAN-C MB-11.5."""
from __future__ import annotations

from decimal import Decimal

import pytest

from backend.app.motors.m19_risk.bia_service import (
    aggregate_bia_summary,
    create_bia_entry,
    list_bia_entries,
)


@pytest.mark.asyncio
async def test_create_and_list_bia_entries(db):
    from backend.tests.conftest import setup_test_project

    _, project_id_str = await setup_test_project(db)
    import uuid

    project_id = uuid.UUID(project_id_str)

    e1 = await create_bia_entry(
        db,
        project_id=project_id,
        service_name="Portal cliente",
        rto_hours=4,
        rpo_hours=1,
        daily_impact_eur=Decimal("5000.00"),
        stakeholders=["clientes"],
    )
    e2 = await create_bia_entry(
        db,
        project_id=project_id,
        service_name="API pública",
        rto_hours=2,
        rpo_hours=1,
    )
    await db.commit()

    entries = await list_bia_entries(db, project_id)
    assert len(entries) == 2
    names = sorted(e.service_name for e in entries)
    assert names == ["API pública", "Portal cliente"]


@pytest.mark.asyncio
async def test_aggregate_summary_max_and_total(db):
    from backend.tests.conftest import setup_test_project

    _, project_id_str = await setup_test_project(db)
    import uuid

    project_id = uuid.UUID(project_id_str)

    await create_bia_entry(
        db, project_id=project_id, service_name="A",
        rto_hours=8, rpo_hours=2, daily_impact_eur=Decimal("1000"),
    )
    await create_bia_entry(
        db, project_id=project_id, service_name="B",
        rto_hours=4, rpo_hours=4, daily_impact_eur=Decimal("3000"),
    )
    await db.commit()

    summary = await aggregate_bia_summary(db, project_id)
    assert summary["services_count"] == 2
    assert summary["max_rto_hours"] == 8
    assert summary["max_rpo_hours"] == 4
    assert summary["total_daily_impact_eur"] == Decimal("4000")


@pytest.mark.asyncio
async def test_summary_empty_project_returns_nones(db):
    from backend.tests.conftest import setup_test_project

    _, project_id_str = await setup_test_project(db)
    import uuid

    summary = await aggregate_bia_summary(db, uuid.UUID(project_id_str))
    assert summary == {
        "services_count": 0,
        "max_rto_hours": None,
        "max_rpo_hours": None,
        "total_daily_impact_eur": None,
    }


async def _login_owner(async_client) -> str:
    """Login owner real · devuelve el CSRF token (triple-binding POST)."""
    res = await async_client.post("/api/v1/_dev/login-as-marcos")
    assert res.status_code == 200, res.text
    return async_client.cookies.get("fulkro_csrf") or ""


@pytest.mark.real_auth
@pytest.mark.asyncio
async def test_bia_endpoint_requires_owner(async_client):
    """Ola A · sin login owner → 401/403 (cierre hueco auth bia_api · IDOR)."""
    response = await async_client.get(
        "/api/v1/projects/11111111-2222-3333-4444-555555555555/bia/summary",
    )
    assert response.status_code in (401, 403), response.text


@pytest.mark.real_auth
@pytest.mark.asyncio
async def test_post_bia_entry_endpoint_returns_201(async_client, db):
    from backend.tests.conftest import setup_test_project

    _, project_id = await setup_test_project(db)
    csrf = await _login_owner(async_client)
    response = await async_client.post(
        f"/api/v1/projects/{project_id}/bia/analyses",
        json={
            "service_name": "Servicio A",
            "rto_hours": 4,
            "rpo_hours": 1,
            "daily_impact_eur": "2500.00",
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["service_name"] == "Servicio A"


@pytest.mark.real_auth
@pytest.mark.asyncio
async def test_get_bia_summary_endpoint(async_client, db):
    from backend.tests.conftest import setup_test_project

    _, project_id = await setup_test_project(db)
    csrf = await _login_owner(async_client)
    await async_client.post(
        f"/api/v1/projects/{project_id}/bia/analyses",
        json={"service_name": "S", "rto_hours": 6, "rpo_hours": 2},
        headers={"X-CSRF-Token": csrf},
    )
    response = await async_client.get(f"/api/v1/projects/{project_id}/bia/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["services_count"] == 1
    assert data["max_rto_hours"] == 6


@pytest.mark.real_auth
@pytest.mark.asyncio
async def test_bia_unknown_project_returns_404(async_client):
    await _login_owner(async_client)
    response = await async_client.get(
        "/api/v1/projects/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/bia/summary",
    )
    assert response.status_code == 404
