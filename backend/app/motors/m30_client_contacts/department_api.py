"""M30 · Department API (sub-atom 1.C.F.2.2 + 1.C.F.3.2).

11 endpoints REST project-scoped (admin-only · ``require_owner``):

  GET    /api/v1/projects/{pid}/departments                              list
  POST   /api/v1/projects/{pid}/departments                              create
  POST   /api/v1/projects/{pid}/departments/bulk                         bulk create
  GET    /api/v1/projects/{pid}/departments/suggestions                  suggestions per category
  GET    /api/v1/projects/{pid}/departments/report                       counts + breakdown
  GET    /api/v1/projects/{pid}/departments/{id}                         detail
  GET    /api/v1/projects/{pid}/departments/{id}/contacts                empleados asignados
  POST   /api/v1/projects/{pid}/departments/{id}/assign-contacts         bulk assign
  PATCH  /api/v1/projects/{pid}/departments/{id}                         update
  PATCH  /api/v1/projects/{pid}/contacts/{cid}/department                assign single (en this router)
  DELETE /api/v1/projects/{pid}/departments/{id}                         hard delete (FK ON DELETE SET NULL)

RLS enforced project_id via ``set_tenant_context`` antes de cualquier
query (pattern m_live_records).
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db, set_tenant_context
from backend.app.models.core import Project
from backend.app.motors.m30_client_contacts.department_schemas import (
    ContactAssignBody,
    ContactSummaryForDepartment,
    ContactsBulkAssignBody,
    DepartmentBulkCreateBody,
    DepartmentCreate,
    DepartmentRead,
    DepartmentReportResponse,
    DepartmentSuggestionsResponse,
    DepartmentUpdate,
)
from backend.app.motors.m30_client_contacts.department_service import (
    ContactNotInProjectError,
    DepartmentNotFoundError,
    DepartmentService,
    DuplicateDepartmentCodeError,
    suggest_departments_for_category,
)


router = APIRouter(
    prefix="/projects/{project_id}/departments",
    tags=["Motor 30 - Departments (1.C.F.2)"],
    dependencies=[Depends(require_owner)],
)


async def _set_project_context(
    db: AsyncSession, project_id: uuid.UUID,
) -> None:
    """Set app.current_project_id + verify project exists (404 if not)."""
    cid = (await db.execute(
        text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)},
    )).scalar()
    if not cid:
        raise HTTPException(status_code=404, detail="Project not found")
    await set_tenant_context(db, project_id=project_id)


@router.get("/suggestions", response_model=DepartmentSuggestionsResponse)
async def get_department_suggestions(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> DepartmentSuggestionsResponse:
    """Sugerencias per categoría ENS · ``[]`` si project sin categoría.

    Admin invoca al cargar page · banner muestra suggestions cuando
    ``existing_count == 0`` y categoría conocida.
    """
    await _set_project_context(db, project_id)
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    suggestions = suggest_departments_for_category(project.categoria_objetivo)
    svc = DepartmentService(db)
    existing = await svc.list_for_project(project_id)

    return DepartmentSuggestionsResponse(
        project_id=project_id,
        project_category=project.categoria_objetivo,
        suggestions=suggestions,
        existing_count=len(existing),
    )


@router.get("", response_model=list[DepartmentRead])
async def list_departments(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[DepartmentRead]:
    await _set_project_context(db, project_id)
    svc = DepartmentService(db)
    items = await svc.list_for_project(project_id)
    return [DepartmentRead.model_validate(i) for i in items]


@router.post("", response_model=DepartmentRead, status_code=201)
async def create_department(
    project_id: uuid.UUID,
    payload: DepartmentCreate,
    db: AsyncSession = Depends(get_db),
) -> DepartmentRead:
    await _set_project_context(db, project_id)
    svc = DepartmentService(db)
    try:
        dept = await svc.create(project_id, payload)
    except DuplicateDepartmentCodeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await db.commit()
    return DepartmentRead.model_validate(dept)


@router.post("/bulk", response_model=list[DepartmentRead], status_code=201)
async def bulk_create_departments(
    project_id: uuid.UUID,
    body: DepartmentBulkCreateBody,
    db: AsyncSession = Depends(get_db),
) -> list[DepartmentRead]:
    """Crea N departments · skipea códigos ya existentes (idempotente).

    Flow típico: admin acepta suggestions del banner (B=1, M=2, A=4) ·
    podrá re-clicar sin error.
    """
    await _set_project_context(db, project_id)
    svc = DepartmentService(db)
    created = await svc.bulk_create(project_id, body.items)
    await db.commit()
    return [DepartmentRead.model_validate(d) for d in created]


# ============================================================
# Static path /report ANTES de /{department_id} para evitar que
# FastAPI intente parsear "report" como UUID.
# ============================================================


@router.get("/report", response_model=DepartmentReportResponse)
async def get_department_report(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> DepartmentReportResponse:
    """Counts empleados per área + breakdown role_category + unassigned.

    Solo cuenta empleados (``has_portal_access=False``) · usuarios portal
    excluidos para mantener el reporte enfocado en estructura organizativa.
    """
    await _set_project_context(db, project_id)
    svc = DepartmentService(db)
    report = await svc.report_per_area(project_id)
    return DepartmentReportResponse.model_validate(report)


@router.get("/{department_id}", response_model=DepartmentRead)
async def get_department(
    project_id: uuid.UUID,
    department_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> DepartmentRead:
    await _set_project_context(db, project_id)
    svc = DepartmentService(db)
    try:
        dept = await svc.get_by_id(project_id, department_id)
    except DepartmentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return DepartmentRead.model_validate(dept)


@router.patch("/{department_id}", response_model=DepartmentRead)
async def update_department(
    project_id: uuid.UUID,
    department_id: uuid.UUID,
    payload: DepartmentUpdate,
    db: AsyncSession = Depends(get_db),
) -> DepartmentRead:
    await _set_project_context(db, project_id)
    svc = DepartmentService(db)
    try:
        dept = await svc.update(project_id, department_id, payload)
    except DepartmentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await db.commit()
    return DepartmentRead.model_validate(dept)


@router.delete("/{department_id}", status_code=204)
async def delete_department(
    project_id: uuid.UUID,
    department_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    await _set_project_context(db, project_id)
    svc = DepartmentService(db)
    try:
        await svc.delete(project_id, department_id)
    except DepartmentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await db.commit()


# ============================================================
# Sub-atom 1.C.F.3.2 · assign/bulk/list endpoints
# /report ya declarado arriba ANTES de /{department_id}.
# ============================================================


@router.get(
    "/{department_id}/contacts",
    response_model=list[ContactSummaryForDepartment],
)
async def list_contacts_for_department(
    project_id: uuid.UUID,
    department_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[ContactSummaryForDepartment]:
    """Empleados asignados a un department · ordered por ``full_name`` ASC."""
    await _set_project_context(db, project_id)
    svc = DepartmentService(db)
    try:
        contacts = await svc.list_contacts_for_department(
            project_id, department_id,
        )
    except DepartmentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [
        ContactSummaryForDepartment(
            id=c.id,
            full_name=c.full_name,
            email=c.email,
            role_title=c.role_title,
            role_category=c.role_category,
            has_portal_access=c.has_portal_access,
            department_id=c.department_id,
        )
        for c in contacts
    ]


@router.post(
    "/{department_id}/assign-contacts",
    response_model=list[ContactSummaryForDepartment],
)
async def bulk_assign_contacts(
    project_id: uuid.UUID,
    department_id: uuid.UUID,
    body: ContactsBulkAssignBody,
    db: AsyncSession = Depends(get_db),
) -> list[ContactSummaryForDepartment]:
    """Asigna múltiples empleados al mismo área · valida cross-project."""
    await _set_project_context(db, project_id)
    svc = DepartmentService(db)
    try:
        updated = await svc.bulk_assign_contacts(
            project_id, department_id, body.contact_ids,
        )
    except DepartmentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ContactNotInProjectError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await db.commit()
    return [
        ContactSummaryForDepartment(
            id=c.id,
            full_name=c.full_name,
            email=c.email,
            role_title=c.role_title,
            role_category=c.role_category,
            has_portal_access=c.has_portal_access,
            department_id=c.department_id,
        )
        for c in updated
    ]


# ============================================================
# PATCH /projects/{pid}/contacts/{cid}/department · single assign
# Distinct router (contacts prefix) registered en main.py.
# ============================================================


contacts_assign_router = APIRouter(
    prefix="/projects/{project_id}/contacts",
    tags=["Motor 30 - Departments (1.C.F.3)"],
    dependencies=[Depends(require_owner)],
)


@contacts_assign_router.patch(
    "/{contact_id}/department",
    response_model=ContactSummaryForDepartment,
)
async def assign_contact_to_department(
    project_id: uuid.UUID,
    contact_id: uuid.UUID,
    body: ContactAssignBody,
    db: AsyncSession = Depends(get_db),
) -> ContactSummaryForDepartment:
    """Asigna (o des-asigna si ``department_id=None``) un empleado a un área.

    Validaciones service-layer:
      - 404 si department_id no existe en project (cuando no None).
      - 400 si contact no pertenece al project (cross-project rejected).
    """
    await _set_project_context(db, project_id)
    svc = DepartmentService(db)
    try:
        contact = await svc.assign_contact(
            project_id, contact_id, body.department_id,
        )
    except DepartmentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ContactNotInProjectError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await db.commit()
    return ContactSummaryForDepartment(
        id=contact.id,
        full_name=contact.full_name,
        email=contact.email,
        role_title=contact.role_title,
        role_category=contact.role_category,
        has_portal_access=contact.has_portal_access,
        department_id=contact.department_id,
    )
