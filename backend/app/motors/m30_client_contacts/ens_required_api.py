"""M30 Client Contacts · ENS_REQUIRED admin status API · SAN-E v3.MB-5.0.bis.

3 endpoints admin (sub-atom 1.C.F.4 v3.10 expand):
  GET    /admin/projects/{pid}/ens-required-roles                    status + priority per category
  PATCH  /admin/projects/{pid}/ens-required-roles/{role}             assign contact to role
  DELETE /admin/projects/{pid}/ens-required-roles/{role}             vacate role

ADR-020 v5 Q5.3 (Marcos 2026-05-10): roles ENS_REQUIRED son M30 contactos
INVISIBLE al cliente · admin-managed. Endpoint dashboard widget admin ·
"Stakeholders ENS · X/6 asignados".

RBAC: ``Depends(require_owner)`` · admin-only.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db, set_tenant_context
from backend.app.motors.m30_client_contacts.ens_required import (
    ENS_REQUIRED_ROLES,
    get_priority_for_category,
)
from backend.app.motors.m30_client_contacts.service import (
    RolEnsYaAsignadoError,
    ClientContactService,
    ContactNotFoundError,
)


router = APIRouter(
    prefix="/admin/projects/{project_id}/ens-required-roles",
    tags=["Motor 30 - ENS_REQUIRED stakeholders"],
    dependencies=[Depends(require_owner)],
)


async def _set_project_rls(db: AsyncSession, project_id: uuid.UUID) -> None:
    """FIX(RLS): projects es RLS fail-closed bajo fulkro_app · resolver owner via
    get_project_owner() SECURITY DEFINER + fijar tenant context antes de las
    lecturas crudas de projects (si no, devuelven None → 404 en proyecto válido).
    client_contacts tiene policy permisiva admin_all, no necesita más."""
    owner = (
        await db.execute(
            sa_text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)}
        )
    ).scalar()
    if not owner:
        raise HTTPException(status_code=404, detail="Project not found")
    await set_tenant_context(db, client_id=owner, project_id=project_id)


class AssignRoleBody(BaseModel):
    """Body PATCH assign contact to ENS role."""

    contact_id: uuid.UUID
    notes: str | None = Field(None, max_length=2000)
    # P3 · el rol ENS es una columna escalar del contacto: asignar uno nuevo
    # borra el que tuviera. Antes eso pasaba en silencio con un 200. Ahora la
    # operacion se niega con 409 salvo que quien la pide confirme aqui que
    # quiere reemplazar la designacion anterior.
    reemplazar_rol_actual: bool = Field(
        False,
        description=(
            "Confirma que se quiere retirar al contacto el rol ENS que ya "
            "tenga. Sin esto, asignar un segundo rol devuelve 409."
        ),
    )


async def _get_project_category(
    db: AsyncSession, project_id: uuid.UUID,
) -> str | None:
    row = await db.execute(
        sa_text(
            "SELECT categoria_objetivo FROM projects WHERE id = :pid"
        ),
        {"pid": str(project_id)},
    )
    hit = row.first()
    if hit is None:
        return None
    return hit[0]


@router.get("", response_model=dict)
async def get_ens_required_roles_status(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Status overview ENS_REQUIRED roles per project · admin widget.

    Sub-atom 1.C.F.4 v3.10 expand: incluye ``project_category`` + ``priority``
    mapping per role (critical/recommended/optional) según categoría ENS.

    Returns:
        ``{
            'project_id': UUID,
            'client_id': UUID,
            'project_category': 'BASICA'|'MEDIA'|'ALTA'|None,
            'priority': {role: 'critical'|'recommended'|'optional'},
            'roles': {role: { contact_id, full_name, ... } | None},
            'all_assigned': bool,
            'missing': list[str],
            'critical_missing': list[str],
            'total_assigned': int,
            'total_required': 6
        }``
    """
    await _set_project_rls(db, project_id)
    service = ClientContactService(db)
    try:
        status = await service.get_ens_required_roles_status(project_id)
    except ContactNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    category = await _get_project_category(db, project_id)
    priority = get_priority_for_category(category)
    critical_missing = [
        role for role in status["missing"]
        if priority.get(role) == "critical"
    ]
    status["project_category"] = category
    status["priority"] = priority
    status["critical_missing"] = critical_missing
    return status


@router.patch("/{role}", response_model=dict)
async def assign_contact_to_ens_role(
    project_id: uuid.UUID,
    role: str,
    body: AssignRoleBody,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Asigna un contact a un rol ENS_REQUIRED · admin operation.

    Vacates any existing assignment of the same role within the client
    (1 contact per role · m30 existing logic).
    """
    if role not in ENS_REQUIRED_ROLES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Role '{role}' no es un rol ENS_REQUIRED válido. "
                f"Válidos: {list(ENS_REQUIRED_ROLES)}"
            ),
        )

    # Verify project exists (404 if not) + fija tenant context RLS.
    await _set_project_rls(db, project_id)

    service = ClientContactService(db)
    try:
        contact, desplazados = await service.assign_ens_required_role(
            contact_id=body.contact_id,
            role=role,
            notes=body.notes,
            reemplazar_rol_actual=body.reemplazar_rol_actual,
        )
    except ContactNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RolEnsYaAsignadoError as exc:
        # 409 y no 400: la peticion es valida, lo que pasa es que choca con un
        # estado que hay que resolver a proposito.
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await db.commit()
    return {
        "role": role,
        "contact_id": str(contact.id),
        "full_name": contact.full_name,
        "email": contact.email,
        "role_title": contact.role_title,
        # P3 · lo que la operacion se llevo por delante viaja en la respuesta.
        # Antes desaparecia sin que nadie lo supiera.
        "desplazados": desplazados,
    }


@router.delete("/{role}", status_code=204)
async def vacate_ens_role(
    project_id: uuid.UUID,
    role: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Vacate un rol ENS · busca el contact actualmente asignado en el client
    del proyecto y lo des-asigna.
    """
    if role not in ENS_REQUIRED_ROLES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Role '{role}' no es un rol ENS_REQUIRED válido. "
                f"Válidos: {list(ENS_REQUIRED_ROLES)}"
            ),
        )

    await _set_project_rls(db, project_id)
    service = ClientContactService(db)
    try:
        status = await service.get_ens_required_roles_status(project_id)
    except ContactNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    assignment = status["roles"].get(role)
    if assignment is None:
        # Already vacated · idempotente.
        return None

    try:
        await service.vacate_ens_required_role(
            contact_id=uuid.UUID(assignment["contact_id"]),
        )
    except ContactNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    await db.commit()
    return None
