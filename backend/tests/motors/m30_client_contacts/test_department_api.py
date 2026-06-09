"""Tests M30 · Department API endpoints (sub-atom 1.C.F.2.2)."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from backend.tests.conftest import setup_test_project, _admin_setup


BASE = "/api/v1/projects"


async def _set_project_category(db, project_id_str: str, category: str) -> None:
    """Promueve categoria_objetivo del project (RLS bypass via admin setup)."""
    async with _admin_setup(db):
        await db.execute(
            text(
                "UPDATE projects SET categoria_objetivo = :cat WHERE id = :pid"
            ),
            {"cat": category, "pid": project_id_str},
        )


@pytest.mark.asyncio
async def test_list_departments_empty(async_client, db):
    _, project_id = await setup_test_project(db)
    r = await async_client.get(f"{BASE}/{project_id}/departments")
    assert r.status_code == 200, r.text
    assert r.json() == []


@pytest.mark.asyncio
async def test_create_and_list_department(async_client, db):
    _, project_id = await setup_test_project(db)

    r = await async_client.post(
        f"{BASE}/{project_id}/departments",
        json={
            "code": "ti",
            "name": "TI",
            "description": "Tecnologías de la Información",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["code"] == "TI"  # normalized
    assert body["project_id"] == project_id

    listing = await async_client.get(f"{BASE}/{project_id}/departments")
    assert listing.status_code == 200
    items = listing.json()
    assert len(items) == 1
    assert items[0]["code"] == "TI"


@pytest.mark.asyncio
async def test_create_duplicate_code_409(async_client, db):
    _, project_id = await setup_test_project(db)
    await async_client.post(
        f"{BASE}/{project_id}/departments",
        json={"code": "TI", "name": "TI"},
    )
    r = await async_client.post(
        f"{BASE}/{project_id}/departments",
        json={"code": "TI", "name": "Otra TI"},
    )
    assert r.status_code == 409, r.text


@pytest.mark.asyncio
async def test_suggestions_for_media_category(async_client, db):
    _, project_id = await setup_test_project(db)
    await _set_project_category(db, project_id, "MEDIA")

    r = await async_client.get(
        f"{BASE}/{project_id}/departments/suggestions",
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["project_category"] == "MEDIA"
    assert body["existing_count"] == 0
    codes = {s["code"] for s in body["suggestions"]}
    assert codes == {"TI", "COMPLIANCE"}


@pytest.mark.asyncio
async def test_suggestions_for_alta_category(async_client, db):
    _, project_id = await setup_test_project(db)
    await _set_project_category(db, project_id, "ALTA")

    r = await async_client.get(
        f"{BASE}/{project_id}/departments/suggestions",
    )
    assert r.status_code == 200
    codes = {s["code"] for s in r.json()["suggestions"]}
    assert codes == {"TI", "COMPLIANCE", "LEGAL", "RRHH"}


@pytest.mark.asyncio
async def test_bulk_create_skips_duplicates(async_client, db):
    _, project_id = await setup_test_project(db)
    await _set_project_category(db, project_id, "MEDIA")

    # Pre-existing TI
    await async_client.post(
        f"{BASE}/{project_id}/departments",
        json={"code": "TI", "name": "TI pre-existente"},
    )

    r = await async_client.post(
        f"{BASE}/{project_id}/departments/bulk",
        json={
            "items": [
                {"code": "TI", "name": "TI duplicado"},
                {"code": "COMPLIANCE", "name": "Compliance"},
            ],
        },
    )
    assert r.status_code == 201, r.text
    created = r.json()
    assert len(created) == 1
    assert created[0]["code"] == "COMPLIANCE"


@pytest.mark.asyncio
async def test_update_department(async_client, db):
    _, project_id = await setup_test_project(db)
    create = await async_client.post(
        f"{BASE}/{project_id}/departments",
        json={"code": "TI", "name": "Old name"},
    )
    dept_id = create.json()["id"]

    r = await async_client.patch(
        f"{BASE}/{project_id}/departments/{dept_id}",
        json={"name": "New name", "description": "Updated"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["name"] == "New name"
    assert body["description"] == "Updated"


@pytest.mark.asyncio
async def test_delete_department(async_client, db):
    _, project_id = await setup_test_project(db)
    create = await async_client.post(
        f"{BASE}/{project_id}/departments",
        json={"code": "TI", "name": "TI"},
    )
    dept_id = create.json()["id"]

    r = await async_client.delete(
        f"{BASE}/{project_id}/departments/{dept_id}",
    )
    assert r.status_code == 204

    listing = await async_client.get(f"{BASE}/{project_id}/departments")
    assert listing.json() == []


@pytest.mark.asyncio
async def test_unknown_project_404(async_client):
    fake = uuid.uuid4()
    r = await async_client.get(f"{BASE}/{fake}/departments")
    assert r.status_code == 404


# ============================================================
# Sub-atom 1.C.F.3.2 · assign/bulk/list/report endpoints
# ============================================================


async def _create_employee(async_client, project_id: str, full_name: str) -> str:
    """Helper: crea empleado (has_portal_access=false) via API project-scoped."""
    r = await async_client.post(
        f"{BASE}/{project_id}/contacts",
        json={
            "full_name": full_name,
            "email": f"{uuid.uuid4().hex[:8]}@empresa.com",
            "role_title": "Técnico",
            "role_category": "tecnico",
            "has_portal_access": False,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _create_dept(async_client, project_id: str, code: str) -> str:
    r = await async_client.post(
        f"{BASE}/{project_id}/departments",
        json={"code": code, "name": code.title()},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


@pytest.mark.asyncio
async def test_patch_contact_department_assigns(async_client, db):
    _, project_id = await setup_test_project(db)
    dept_id = await _create_dept(async_client, project_id, "TI")
    contact_id = await _create_employee(async_client, project_id, "Empleado A")

    r = await async_client.patch(
        f"{BASE}/{project_id}/contacts/{contact_id}/department",
        json={"department_id": dept_id},
    )
    assert r.status_code == 200, r.text
    assert r.json()["department_id"] == dept_id


@pytest.mark.asyncio
async def test_patch_contact_department_unassigns(async_client, db):
    _, project_id = await setup_test_project(db)
    dept_id = await _create_dept(async_client, project_id, "TI")
    contact_id = await _create_employee(async_client, project_id, "Empleado A")

    await async_client.patch(
        f"{BASE}/{project_id}/contacts/{contact_id}/department",
        json={"department_id": dept_id},
    )
    r = await async_client.patch(
        f"{BASE}/{project_id}/contacts/{contact_id}/department",
        json={"department_id": None},
    )
    assert r.status_code == 200, r.text
    assert r.json()["department_id"] is None


@pytest.mark.asyncio
async def test_bulk_assign_endpoint(async_client, db):
    _, project_id = await setup_test_project(db)
    dept_id = await _create_dept(async_client, project_id, "TI")
    c1 = await _create_employee(async_client, project_id, "A")
    c2 = await _create_employee(async_client, project_id, "B")

    r = await async_client.post(
        f"{BASE}/{project_id}/departments/{dept_id}/assign-contacts",
        json={"contact_ids": [c1, c2]},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert {c["id"] for c in body} == {c1, c2}
    assert all(c["department_id"] == dept_id for c in body)


@pytest.mark.asyncio
async def test_list_contacts_for_department_ordered(async_client, db):
    _, project_id = await setup_test_project(db)
    dept_id = await _create_dept(async_client, project_id, "TI")
    cz = await _create_employee(async_client, project_id, "Zoe")
    ca = await _create_employee(async_client, project_id, "Ana")
    await async_client.post(
        f"{BASE}/{project_id}/departments/{dept_id}/assign-contacts",
        json={"contact_ids": [cz, ca]},
    )

    r = await async_client.get(
        f"{BASE}/{project_id}/departments/{dept_id}/contacts",
    )
    assert r.status_code == 200, r.text
    names = [c["full_name"] for c in r.json()]
    assert names == ["Ana", "Zoe"]


@pytest.mark.asyncio
async def test_report_per_area_endpoint(async_client, db):
    _, project_id = await setup_test_project(db)
    dept_ti = await _create_dept(async_client, project_id, "TI")
    await _create_dept(async_client, project_id, "COMPLIANCE")
    c_ti = await _create_employee(async_client, project_id, "Tech 1")
    await _create_employee(async_client, project_id, "Unassigned 1")

    await async_client.patch(
        f"{BASE}/{project_id}/contacts/{c_ti}/department",
        json={"department_id": dept_ti},
    )

    r = await async_client.get(f"{BASE}/{project_id}/departments/report")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total_employees"] == 2
    by_code = {d["code"]: d for d in body["departments"]}
    assert by_code["TI"]["total_contacts"] == 1
    assert by_code["COMPLIANCE"]["total_contacts"] == 0
    assert body["unassigned"]["total_contacts"] == 1


@pytest.mark.asyncio
async def test_patch_contact_unknown_department_404(async_client, db):
    _, project_id = await setup_test_project(db)
    contact_id = await _create_employee(async_client, project_id, "A")

    r = await async_client.patch(
        f"{BASE}/{project_id}/contacts/{contact_id}/department",
        json={"department_id": str(uuid.uuid4())},
    )
    assert r.status_code == 404
