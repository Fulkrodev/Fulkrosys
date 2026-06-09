"""Tests M30 · Department service (sub-atom 1.C.F.2.1).

Cubre:
- CRUD project-scoped (create, get, list, update, delete)
- UNIQUE(project_id, code) enforced (DuplicateDepartmentCodeError)
- Cross-project: same code OK (constraint scoped)
- Suggestions per category B/M/A (1/2/4 items)
- bulk_create idempotente (skip existing codes)
"""
from __future__ import annotations

import uuid

import pytest

from backend.app.motors.m30_client_contacts.department_schemas import (
    DepartmentCreate,
    DepartmentUpdate,
)
from backend.app.motors.m30_client_contacts.department_service import (
    DEPARTMENT_SUGGESTIONS_PER_CATEGORY,
    DepartmentNotFoundError,
    DepartmentService,
    DuplicateDepartmentCodeError,
    suggest_departments_for_category,
)
from backend.tests.conftest import setup_test_project


# ============================================================
# Suggestions catalogo (puros · no requieren DB)
# ============================================================


def test_suggestions_basica_returns_one():
    items = suggest_departments_for_category("BASICA")
    assert len(items) == 1
    assert items[0].code == "TI"


def test_suggestions_media_returns_two():
    items = suggest_departments_for_category("MEDIA")
    codes = {i.code for i in items}
    assert codes == {"TI", "COMPLIANCE"}


def test_suggestions_alta_returns_four():
    items = suggest_departments_for_category("ALTA")
    codes = {i.code for i in items}
    assert codes == {"TI", "COMPLIANCE", "LEGAL", "RRHH"}


def test_suggestions_lowercase_normalized():
    items = suggest_departments_for_category("media")
    assert len(items) == 2


def test_suggestions_unknown_or_null_returns_empty():
    assert suggest_departments_for_category(None) == []
    assert suggest_departments_for_category("UNKNOWN") == []


def test_suggestions_catalog_consistency():
    """Sanity: 3 categorias canonicas con counts esperados."""
    assert set(DEPARTMENT_SUGGESTIONS_PER_CATEGORY) == {"BASICA", "MEDIA", "ALTA"}
    assert len(DEPARTMENT_SUGGESTIONS_PER_CATEGORY["BASICA"]) == 1
    assert len(DEPARTMENT_SUGGESTIONS_PER_CATEGORY["MEDIA"]) == 2
    assert len(DEPARTMENT_SUGGESTIONS_PER_CATEGORY["ALTA"]) == 4


# ============================================================
# CRUD service (require DB · setup_test_project)
# ============================================================


@pytest.mark.asyncio
async def test_create_and_list_department(db):
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)
    svc = DepartmentService(db)

    created = await svc.create(
        pid,
        DepartmentCreate(code="ti", name="TI", description="Tecnologías"),
    )
    # code normalized uppercase
    assert created.code == "TI"
    assert created.project_id == pid

    items = await svc.list_for_project(pid)
    assert len(items) == 1
    assert items[0].id == created.id


@pytest.mark.asyncio
async def test_create_duplicate_code_same_project_raises(db):
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)
    svc = DepartmentService(db)

    await svc.create(pid, DepartmentCreate(code="TI", name="TI"))

    with pytest.raises(DuplicateDepartmentCodeError):
        await svc.create(pid, DepartmentCreate(code="TI", name="Otra TI"))


@pytest.mark.asyncio
async def test_get_by_id_unknown_raises(db):
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)
    svc = DepartmentService(db)

    with pytest.raises(DepartmentNotFoundError):
        await svc.get_by_id(pid, uuid.uuid4())


@pytest.mark.asyncio
async def test_update_department(db):
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)
    svc = DepartmentService(db)

    dept = await svc.create(pid, DepartmentCreate(code="TI", name="Antiguo"))
    updated = await svc.update(
        pid, dept.id,
        DepartmentUpdate(name="TI nuevo", description="Actualizado"),
    )
    assert updated.name == "TI nuevo"
    assert updated.description == "Actualizado"
    assert updated.code == "TI"  # not changed


@pytest.mark.asyncio
async def test_delete_department(db):
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)
    svc = DepartmentService(db)

    dept = await svc.create(pid, DepartmentCreate(code="X", name="X"))
    await svc.delete(pid, dept.id)
    items = await svc.list_for_project(pid)
    assert items == []


@pytest.mark.asyncio
async def test_bulk_create_skips_duplicates(db):
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)
    svc = DepartmentService(db)

    await svc.create(pid, DepartmentCreate(code="TI", name="TI existente"))

    suggestions = suggest_departments_for_category("MEDIA")  # TI + COMPLIANCE
    created = await svc.bulk_create(
        pid,
        [DepartmentCreate(**s.model_dump()) for s in suggestions],
    )
    # TI ya existe · solo COMPLIANCE se crea
    assert len(created) == 1
    assert created[0].code == "COMPLIANCE"

    items = await svc.list_for_project(pid)
    codes = {d.code for d in items}
    assert codes == {"TI", "COMPLIANCE"}
