"""Tests M30 · Department assign/unassign/bulk + report (sub-atom 1.C.F.3.1).

Cubre:
- assign_contact happy path
- assign_contact cross-project rejected
- unassign (department_id=None) clears FK
- bulk_assign valida all contacts en project
- delete department setea contacts.department_id NULL (ON DELETE SET NULL)
- list_contacts_for_department · ordered
- report_per_area · counts + role_category breakdown + unassigned bucket
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from backend.app.motors.m30_client_contacts.department_schemas import (
    DepartmentCreate,
)
from backend.app.motors.m30_client_contacts.department_service import (
    ContactNotInProjectError,
    DepartmentNotFoundError,
    DepartmentService,
)
from backend.app.motors.m30_client_contacts.models import ClientContact
from backend.tests.conftest import _admin_setup, setup_test_project


async def _create_contact_for_project(
    db,
    project_id: str,
    client_id: str,
    *,
    full_name: str = "Empleado Test",
    email: str | None = None,
    role_category: str = "tecnico",
    has_portal_access: bool = False,
) -> uuid.UUID:
    """INSERT empleado project-scoped vía _admin_setup (bypass RLS)."""
    cid = uuid.uuid4()
    email = email or f"{cid.hex[:10]}@empresa.test"
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO client_contacts "
                "(id, client_id, project_id, full_name, email, "
                " role_title, role_category, has_portal_access, "
                " is_active, created_at) "
                "VALUES (:id, :cid, :pid, :name, :email, "
                " 'Cargo', :role_cat, :portal, true, now())"
            ),
            {
                "id": str(cid),
                "cid": client_id,
                "pid": project_id,
                "name": full_name,
                "email": email,
                "role_cat": role_category,
                "portal": has_portal_access,
            },
        )
    return cid


@pytest.mark.asyncio
async def test_assign_contact_to_department(db):
    client_id, project_id = await setup_test_project(db)
    pid = uuid.UUID(project_id)
    svc = DepartmentService(db)
    dept = await svc.create(pid, DepartmentCreate(code="TI", name="TI"))

    contact_id = await _create_contact_for_project(db, project_id, client_id)
    contact = await svc.assign_contact(pid, contact_id, dept.id)
    assert contact.department_id == dept.id


@pytest.mark.asyncio
async def test_unassign_contact_sets_null(db):
    client_id, project_id = await setup_test_project(db)
    pid = uuid.UUID(project_id)
    svc = DepartmentService(db)
    dept = await svc.create(pid, DepartmentCreate(code="TI", name="TI"))

    contact_id = await _create_contact_for_project(db, project_id, client_id)
    await svc.assign_contact(pid, contact_id, dept.id)
    contact = await svc.assign_contact(pid, contact_id, None)
    assert contact.department_id is None


@pytest.mark.asyncio
async def test_assign_contact_cross_project_rejected(db):
    """Contact en project A no puede asignarse a department de project B."""
    client_id_a, project_a = await setup_test_project(db)
    pid_a = uuid.UUID(project_a)

    # 2do project bajo mismo client · dept_b también via _admin_setup
    # porque RLS departments_project_isolation rechazaría INSERT bajo
    # tenant_context=project_a. Test valida guard service-layer (NO RLS).
    project_b = uuid.uuid4()
    dept_b_id = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO projects (id, client_id, nombre, created_at) "
                "VALUES (:id, :cid, 'Proyecto B', now())"
            ),
            {"id": str(project_b), "cid": client_id_a},
        )
        await db.execute(
            text(
                "INSERT INTO departments "
                "(id, project_id, code, name, created_at, updated_at) "
                "VALUES (:id, :pid, 'TI', 'TI B', now(), now())"
            ),
            {"id": str(dept_b_id), "pid": str(project_b)},
        )
    pid_b = project_b

    svc = DepartmentService(db)
    contact_id = await _create_contact_for_project(db, project_a, client_id_a)

    # Tenant context is project_a, dept_b lives in project_b.
    # Service-layer ContactNotInProjectError debe disparar antes de
    # cualquier query (contact.project_id != pid_b).
    with pytest.raises(ContactNotInProjectError):
        await svc.assign_contact(pid_b, contact_id, dept_b_id)


@pytest.mark.asyncio
async def test_assign_to_unknown_department_404(db):
    client_id, project_id = await setup_test_project(db)
    pid = uuid.UUID(project_id)
    svc = DepartmentService(db)
    contact_id = await _create_contact_for_project(db, project_id, client_id)

    with pytest.raises(DepartmentNotFoundError):
        await svc.assign_contact(pid, contact_id, uuid.uuid4())


@pytest.mark.asyncio
async def test_bulk_assign_contacts(db):
    client_id, project_id = await setup_test_project(db)
    pid = uuid.UUID(project_id)
    svc = DepartmentService(db)
    dept = await svc.create(pid, DepartmentCreate(code="TI", name="TI"))

    c1 = await _create_contact_for_project(db, project_id, client_id, full_name="A")
    c2 = await _create_contact_for_project(db, project_id, client_id, full_name="B")
    c3 = await _create_contact_for_project(db, project_id, client_id, full_name="C")

    updated = await svc.bulk_assign_contacts(pid, dept.id, [c1, c2, c3])
    assert len(updated) == 3
    assert all(c.department_id == dept.id for c in updated)


@pytest.mark.asyncio
async def test_delete_department_sets_contacts_null(db):
    """ON DELETE SET NULL · borrar área no borra empleados."""
    client_id, project_id = await setup_test_project(db)
    pid = uuid.UUID(project_id)
    svc = DepartmentService(db)
    dept = await svc.create(pid, DepartmentCreate(code="TI", name="TI"))

    contact_id = await _create_contact_for_project(db, project_id, client_id)
    await svc.assign_contact(pid, contact_id, dept.id)

    await svc.delete(pid, dept.id)

    refreshed = await db.get(ClientContact, contact_id)
    assert refreshed is not None
    assert refreshed.department_id is None


@pytest.mark.asyncio
async def test_list_contacts_for_department(db):
    client_id, project_id = await setup_test_project(db)
    pid = uuid.UUID(project_id)
    svc = DepartmentService(db)
    dept = await svc.create(pid, DepartmentCreate(code="TI", name="TI"))

    c1 = await _create_contact_for_project(
        db, project_id, client_id, full_name="Zoe", email="z@x.com",
    )
    c2 = await _create_contact_for_project(
        db, project_id, client_id, full_name="Ana", email="a@x.com",
    )
    await svc.bulk_assign_contacts(pid, dept.id, [c1, c2])

    contacts = await svc.list_contacts_for_department(pid, dept.id)
    # Ordered by full_name ASC
    assert [c.full_name for c in contacts] == ["Ana", "Zoe"]


@pytest.mark.asyncio
async def test_report_per_area_counts_and_breakdown(db):
    client_id, project_id = await setup_test_project(db)
    pid = uuid.UUID(project_id)
    svc = DepartmentService(db)
    dept_ti = await svc.create(pid, DepartmentCreate(code="TI", name="TI"))
    dept_comp = await svc.create(
        pid, DepartmentCreate(code="COMPLIANCE", name="Compliance"),
    )

    c_ti_1 = await _create_contact_for_project(
        db, project_id, client_id, role_category="tecnico",
    )
    c_ti_2 = await _create_contact_for_project(
        db, project_id, client_id, role_category="tecnico",
    )
    c_comp = await _create_contact_for_project(
        db, project_id, client_id, role_category="rseg",
    )
    c_unassigned = await _create_contact_for_project(
        db, project_id, client_id, role_category="legal",
    )

    await svc.bulk_assign_contacts(pid, dept_ti.id, [c_ti_1, c_ti_2])
    await svc.bulk_assign_contacts(pid, dept_comp.id, [c_comp])

    report = await svc.report_per_area(pid)
    assert report["total_employees"] == 4
    by_code = {d["code"]: d for d in report["departments"]}
    assert by_code["TI"]["total_contacts"] == 2
    assert by_code["TI"]["by_role_category"]["tecnico"] == 2
    assert by_code["COMPLIANCE"]["total_contacts"] == 1
    assert by_code["COMPLIANCE"]["by_role_category"]["rseg"] == 1
    assert report["unassigned"]["total_contacts"] == 1
    assert report["unassigned"]["by_role_category"]["legal"] == 1
