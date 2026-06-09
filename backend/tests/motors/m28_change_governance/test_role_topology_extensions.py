"""Tests M28 role-topology extensions + drift summary · SAN-E v3.MB-3.E."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from backend.tests.conftest import _admin_setup, setup_test_project


BASE = "/api/v1/projects"


async def _create_contact_for_project(client, project_id: str, db, full_name: str = "X Y") -> str:
    r = await client.post(
        f"{BASE}/{project_id}/contacts",
        json={
            "full_name": full_name,
            "email": f"{uuid.uuid4().hex[:6]}@cliente.com",
            "role_title": "Sponsor",
            "role_category": "sponsor",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


@pytest.mark.asyncio
async def test_assign_role_happy_path(async_client, db):
    _, project_id = await setup_test_project(db)
    contact_id = await _create_contact_for_project(async_client, project_id, db, "Alicia Sponsor")
    r = await async_client.post(
        f"{BASE}/{project_id}/role-topology/sponsor/assign",
        json={"contact_id": contact_id},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["role_code"] == "sponsor"
    assert body["contact_id"] == contact_id
    assert body["assigned_at"] is not None
    assert body["is_required"] is True
    assert body["is_cross_compliance"] is False


@pytest.mark.asyncio
async def test_assign_role_invalid_role_422(async_client, db):
    _, project_id = await setup_test_project(db)
    contact_id = await _create_contact_for_project(async_client, project_id, db)
    r = await async_client.post(
        f"{BASE}/{project_id}/role-topology/role_invalido/assign",
        json={"contact_id": contact_id},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_assign_role_unknown_contact_404(async_client, db):
    _, project_id = await setup_test_project(db)
    fake_id = str(uuid.uuid4())
    r = await async_client.post(
        f"{BASE}/{project_id}/role-topology/sponsor/assign",
        json={"contact_id": fake_id},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_assign_role_overwrite(async_client, db):
    _, project_id = await setup_test_project(db)
    c1 = await _create_contact_for_project(async_client, project_id, db, "C1")
    c2 = await _create_contact_for_project(async_client, project_id, db, "C2")
    r1 = await async_client.post(
        f"{BASE}/{project_id}/role-topology/sponsor/assign",
        json={"contact_id": c1},
    )
    r2 = await async_client.post(
        f"{BASE}/{project_id}/role-topology/sponsor/assign",
        json={"contact_id": c2},
    )
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r2.json()["contact_id"] == c2


@pytest.mark.asyncio
async def test_vacate_role(async_client, db):
    _, project_id = await setup_test_project(db)
    contact_id = await _create_contact_for_project(async_client, project_id, db)
    await async_client.post(
        f"{BASE}/{project_id}/role-topology/sponsor/assign",
        json={"contact_id": contact_id},
    )
    r = await async_client.post(
        f"{BASE}/{project_id}/role-topology/sponsor/vacate",
    )
    assert r.status_code == 200, r.text
    assert r.json()["vacated"] is True


@pytest.mark.asyncio
async def test_vacate_role_404_when_not_assigned(async_client, db):
    _, project_id = await setup_test_project(db)
    r = await async_client.post(
        f"{BASE}/{project_id}/role-topology/sponsor/vacate",
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_drift_summary_empty(async_client, db):
    _, project_id = await setup_test_project(db)
    r = await async_client.get(f"{BASE}/{project_id}/drift-summary")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["project_id"] == project_id
    assert body["items"] == []
    assert body["open_total"] == 0


@pytest.mark.asyncio
async def test_drift_summary_aggregates_events(async_client, db):
    """Inserta drift events directos · verifica MV agrega correctamente."""
    client_id, project_id = await setup_test_project(db)
    # Crear retainer_contract minimo necesario para FK
    contract_id = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO retainer_contracts "
            "(id, client_id, project_id, estado, perfil, created_at) "
            "VALUES (:id, :clid, :pid, 'active', 'R_STD', now())"
        ), {"id": str(contract_id), "clid": client_id, "pid": project_id})
        # 3 drifts: cifrado/CRITICA · cifrado/ALTA · backups/MEDIA
        await db.execute(text(
            "INSERT INTO retainer_drift_events "
            "(retainer_contract_id, project_id, dimension, descripcion, severidad, impacto, estado) "
            "VALUES (:cid, :pid, 'cifrado', 'Test 1', 'CRITICA', 'alto', 'open'), "
            "(:cid, :pid, 'cifrado', 'Test 2', 'ALTA', 'medio', 'open'), "
            "(:cid, :pid, 'backups', 'Test 3', 'MEDIA', 'bajo', 'open')"
        ), {"cid": str(contract_id), "pid": project_id})
    await db.commit()
    # Refresh MV via fulkro role (owner) · production lo hace job M28 jobs.py.
    async with _admin_setup(db):
        await db.execute(text("REFRESH MATERIALIZED VIEW mv_drift_summary_10x4"))

    r = await async_client.get(f"{BASE}/{project_id}/drift-summary")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["open_total"] == 3
    assert body["open_by_severity"]["CRITICA"] == 1
    assert body["open_by_severity"]["ALTA"] == 1
    assert body["open_by_severity"]["MEDIA"] == 1
    dims = {(it["dimension"], it["severidad"]) for it in body["items"]}
    assert ("cifrado", "CRITICA") in dims
    assert ("cifrado", "ALTA") in dims
    assert ("backups", "MEDIA") in dims
