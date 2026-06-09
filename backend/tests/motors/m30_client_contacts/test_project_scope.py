"""Tests M30 Project-scoped Contacts · ADR-046 v3 SAN-E.MB-3.C.

Cubre:
- CRUD project-scoped (list, create, patch, delete soft)
- Constraint v3: 1 contacto con portal_access por project (409 conflict)
- Backward compat: contactos client-scoped (project_id NULL) intactos
- Cross-project: portal_access en proyectos distintos OK (constraint scoped)
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from backend.tests.conftest import _admin_setup, setup_test_project


BASE = "/api/v1/projects"


async def _setup_second_project(db, client_id: str) -> str:
    """Crea segundo proyecto para tests cross-project."""
    project_id = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO projects (id, client_id, nombre, created_at) "
            "VALUES (:id, :cid, 'Test Project 2', now())"
        ), {"id": str(project_id), "cid": client_id})
    return str(project_id)


@pytest.mark.asyncio
async def test_list_project_contacts_empty(async_client, db):
    _, project_id = await setup_test_project(db)
    r = await async_client.get(f"{BASE}/{project_id}/contacts")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["contacts"] == []
    assert body["total"] == 0


@pytest.mark.asyncio
async def test_create_project_contact_basic(async_client, db):
    _, project_id = await setup_test_project(db)
    r = await async_client.post(
        f"{BASE}/{project_id}/contacts",
        json={
            "full_name": "Alicia Munoz",
            "email": "alicia@cliente.com",
            "role_title": "Sponsor",
            "role_category": "sponsor",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["full_name"] == "Alicia Munoz"
    assert body["project_id"] == project_id
    assert body["has_portal_access"] is False


@pytest.mark.asyncio
async def test_create_with_portal_access_first_succeeds(async_client, db):
    _, project_id = await setup_test_project(db)
    r = await async_client.post(
        f"{BASE}/{project_id}/contacts",
        json={
            "full_name": "Bea Ortiz",
            "email": "bea@cliente.com",
            "role_title": "RSEG",
            "role_category": "rseg",
            "has_portal_access": True,
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["has_portal_access"] is True


@pytest.mark.asyncio
async def test_create_with_portal_access_second_409(async_client, db):
    """Constraint v3: segundo contacto con portal_access en mismo proyecto debe rechazar."""
    _, project_id = await setup_test_project(db)
    await async_client.post(
        f"{BASE}/{project_id}/contacts",
        json={
            "full_name": "Bea Ortiz",
            "email": "bea@cliente.com",
            "role_title": "RSEG",
            "role_category": "rseg",
            "has_portal_access": True,
        },
    )
    r = await async_client.post(
        f"{BASE}/{project_id}/contacts",
        json={
            "full_name": "Carlos Lopez",
            "email": "carlos@cliente.com",
            "role_title": "CTO",
            "role_category": "cto",
            "has_portal_access": True,
        },
    )
    assert r.status_code == 409, r.text
    assert "Constraint v3" in r.json()["detail"]


@pytest.mark.asyncio
async def test_create_two_no_portal_no_conflict(async_client, db):
    """Sin portal_access NO aplica constraint · 2 contactos OK."""
    _, project_id = await setup_test_project(db)
    r1 = await async_client.post(
        f"{BASE}/{project_id}/contacts",
        json={
            "full_name": "Bea", "email": "bea@x.com",
            "role_title": "RSEG", "role_category": "rseg",
        },
    )
    r2 = await async_client.post(
        f"{BASE}/{project_id}/contacts",
        json={
            "full_name": "Carlos", "email": "carlos@x.com",
            "role_title": "CTO", "role_category": "cto",
        },
    )
    assert r1.status_code == 201
    assert r2.status_code == 201
    listing = await async_client.get(f"{BASE}/{project_id}/contacts")
    assert listing.json()["total"] == 2


@pytest.mark.asyncio
async def test_patch_toggle_portal_access_validates_constraint(async_client, db):
    """Si ya hay 1 con portal · PATCH otro a portal=True debe rechazar."""
    _, project_id = await setup_test_project(db)
    create_a = await async_client.post(
        f"{BASE}/{project_id}/contacts",
        json={
            "full_name": "A", "email": "a@x.com",
            "role_title": "RSEG", "role_category": "rseg",
            "has_portal_access": True,
        },
    )
    create_b = await async_client.post(
        f"{BASE}/{project_id}/contacts",
        json={
            "full_name": "B", "email": "b@x.com",
            "role_title": "CTO", "role_category": "cto",
        },
    )
    cid_b = create_b.json()["id"]
    r = await async_client.patch(
        f"{BASE}/{project_id}/contacts/{cid_b}",
        json={"has_portal_access": True},
    )
    assert r.status_code == 409, r.text


@pytest.mark.asyncio
async def test_delete_soft_excludes_from_list(async_client, db):
    _, project_id = await setup_test_project(db)
    create = await async_client.post(
        f"{BASE}/{project_id}/contacts",
        json={
            "full_name": "X", "email": "x@x.com",
            "role_title": "Y", "role_category": "tecnico",
        },
    )
    cid = create.json()["id"]
    r = await async_client.delete(f"{BASE}/{project_id}/contacts/{cid}")
    assert r.status_code == 204
    listing = await async_client.get(f"{BASE}/{project_id}/contacts")
    assert listing.json()["total"] == 0


@pytest.mark.asyncio
async def test_cross_project_portal_access_independent(async_client, db):
    """portal_access en project A no afecta project B (constraint scoped)."""
    client_id, project_id = await setup_test_project(db)
    project_id_2 = await _setup_second_project(db, client_id)
    # Project A: portal_access=true
    r1 = await async_client.post(
        f"{BASE}/{project_id}/contacts",
        json={
            "full_name": "A", "email": "a@x.com",
            "role_title": "RSEG", "role_category": "rseg",
            "has_portal_access": True,
        },
    )
    assert r1.status_code == 201
    # Project B: portal_access=true OK (proyecto diferente)
    r2 = await async_client.post(
        f"{BASE}/{project_id_2}/contacts",
        json={
            "full_name": "B", "email": "b@x.com",
            "role_title": "CISO", "role_category": "ciso",
            "has_portal_access": True,
        },
    )
    assert r2.status_code == 201, r2.text


@pytest.mark.asyncio
async def test_backward_compat_client_scoped_unchanged(async_client, db):
    """Contactos client-scoped (project_id NULL) NO aparecen en listado project."""
    client_id, project_id = await setup_test_project(db)
    # Crear contacto client-scoped via insert directo (simulando flow M30 existing)
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO client_contacts "
            "(client_id, full_name, email, role_title, role_category, project_id) "
            "VALUES (:cid, 'Legacy Contact', 'legacy@x.com', 'Operaciones', 'operaciones', NULL)"
        ), {"cid": client_id})
    await db.flush()
    # Listar project-scoped: NO debe aparecer
    listing = await async_client.get(f"{BASE}/{project_id}/contacts")
    assert listing.status_code == 200
    assert listing.json()["total"] == 0
