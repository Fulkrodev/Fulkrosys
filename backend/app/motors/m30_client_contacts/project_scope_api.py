"""M30 Client Contacts · project-scoped REST API · ADR-046 v3 SAN-E.MB-3.C.

EXTENSION del M30 client_contacts existing (FASE 5.5.C). Anade dimension
proyecto sin duplicar tabla.

4 endpoints scope project (NO duplicar los 11 endpoints client-scoped):
    GET    /api/v1/projects/{project_id}/contacts
    POST   /api/v1/projects/{project_id}/contacts
    PATCH  /api/v1/projects/{project_id}/contacts/{contact_id}
    DELETE /api/v1/projects/{project_id}/contacts/{contact_id}

Constraint v3: 1 contacto con has_portal_access=true por project_id.
Implementacion DB: partial UNIQUE WHERE has_portal_access=true AND
project_id IS NOT NULL AND deleted_at IS NULL. Service-layer raise 409
para mensaje de error friendly antes de hit DB.

RBAC: require_owner (admin Marcos-only · pattern canonico M30).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import CurrentUser, require_owner
from backend.app.database import get_db, set_tenant_context
from backend.app.motors.m30_client_contacts.models import ClientContact


router = APIRouter(
    prefix="/projects/{project_id}/contacts",
    tags=["Motor 30 - Project-scoped Contacts"],
    dependencies=[Depends(require_owner)],
)


class ProjectContactCreate(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    phone: str | None = Field(None, max_length=50)
    linkedin_url: str | None = Field(None, max_length=500)
    role_title: str = Field(..., min_length=1, max_length=150)
    role_category: str = Field(..., min_length=1, max_length=50)
    has_portal_access: bool = False
    notes_marcos: str | None = None
    is_primary: bool = False
    is_signatory: bool = False


class ProjectContactUpdate(BaseModel):
    full_name: str | None = Field(None, min_length=1, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=50)
    linkedin_url: str | None = Field(None, max_length=500)
    role_title: str | None = Field(None, min_length=1, max_length=150)
    role_category: str | None = Field(None, min_length=1, max_length=50)
    has_portal_access: bool | None = None
    notes_marcos: str | None = None
    is_primary: bool | None = None
    is_signatory: bool | None = None


def _row_to_dict(row: ClientContact) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "client_id": str(row.client_id),
        "project_id": str(row.project_id) if row.project_id else None,
        "full_name": row.full_name,
        "email": row.email,
        "phone": row.phone,
        "linkedin_url": row.linkedin_url,
        "role_title": row.role_title,
        "role_category": row.role_category,
        "is_primary": row.is_primary,
        "is_signatory": row.is_signatory,
        "has_portal_access": row.has_portal_access,
        "notes_marcos": row.notes_marcos,
        "is_active": row.is_active,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        # Sub-atom 1.C.F.3 · FK department (NULL si sin asignar)
        "department_id": (
            str(row.department_id) if row.department_id else None
        ),
    }


async def _get_client_id_for_project(project_id: uuid.UUID, db: AsyncSession) -> uuid.UUID:
    """Resolve client_id (owner) para project_id via funcion BD existente."""
    from sqlalchemy import text
    cid = (await db.execute(
        text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)}
    )).scalar()
    if not cid:
        raise HTTPException(status_code=404, detail="Project not found")
    return cid if isinstance(cid, uuid.UUID) else uuid.UUID(str(cid))


async def _set_project_rls(project_id: uuid.UUID, db: AsyncSession) -> uuid.UUID:
    """Resuelve owner (get_project_owner SECURITY DEFINER) y fija el tenant
    context. Sin esto, las queries por project_id corrian bajo fulkro_app SIN
    contexto → la RLS por client_id de client_contacts devolvia [] (lista vacia
    espuria en prod) y los INSERT podian fallar. Aislamiento por proyecto."""
    client_id = await _get_client_id_for_project(project_id, db)
    await set_tenant_context(db, client_id=client_id, project_id=project_id)
    return client_id


async def _check_portal_constraint_v3(
    project_id: uuid.UUID,
    db: AsyncSession,
    exclude_contact_id: uuid.UUID | None = None,
) -> None:
    """Service-layer guard: raise 409 si ya existe contacto con portal en project."""
    stmt = select(ClientContact).where(
        ClientContact.project_id == project_id,
        ClientContact.has_portal_access.is_(True),
        ClientContact.deleted_at.is_(None),
    )
    if exclude_contact_id is not None:
        stmt = stmt.where(ClientContact.id != exclude_contact_id)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                "Constraint v3 violado: ya existe un contacto con portal_access "
                f"en este proyecto ({existing.full_name} · {existing.email}). "
                "Solo 1 contacto por proyecto puede tener cuenta portal cliente."
            ),
        )


@router.get("")
async def list_project_contacts(
    project_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _set_project_rls(project_id, db)
    rows = (await db.execute(
        select(ClientContact)
        .where(
            ClientContact.project_id == project_id,
            ClientContact.deleted_at.is_(None),
        )
        .order_by(ClientContact.is_primary.desc(), ClientContact.full_name)
    )).scalars().all()
    return {
        "project_id": str(project_id),
        "contacts": [_row_to_dict(r) for r in rows],
        "total": len(rows),
        "with_portal_access": sum(1 for r in rows if r.has_portal_access),
    }


@router.post("", status_code=201)
async def create_project_contact(
    project_id: uuid.UUID,
    body: ProjectContactCreate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    client_id = await _set_project_rls(project_id, db)
    if body.has_portal_access:
        await _check_portal_constraint_v3(project_id, db)
    contact = ClientContact(
        client_id=client_id,
        project_id=project_id,
        full_name=body.full_name,
        email=body.email,
        phone=body.phone,
        linkedin_url=body.linkedin_url,
        role_title=body.role_title,
        role_category=body.role_category,
        has_portal_access=body.has_portal_access,
        notes_marcos=body.notes_marcos,
        is_primary=body.is_primary,
        is_signatory=body.is_signatory,
    )
    db.add(contact)
    await db.flush()
    await db.commit()
    return _row_to_dict(contact)


@router.patch("/{contact_id}")
async def update_project_contact(
    project_id: uuid.UUID,
    contact_id: uuid.UUID,
    body: ProjectContactUpdate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _set_project_rls(project_id, db)
    contact = (await db.execute(
        select(ClientContact).where(
            ClientContact.id == contact_id,
            ClientContact.project_id == project_id,
            ClientContact.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if contact is None:
        raise HTTPException(status_code=404, detail="Contact not found en project")

    payload = body.model_dump(exclude_unset=True)
    if payload.get("has_portal_access") is True:
        await _check_portal_constraint_v3(project_id, db, exclude_contact_id=contact_id)
    for k, v in payload.items():
        setattr(contact, k, v)
    await db.flush()
    await db.commit()
    return _row_to_dict(contact)


@router.delete("/{contact_id}", status_code=204)
async def delete_project_contact(
    project_id: uuid.UUID,
    contact_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    await _set_project_rls(project_id, db)
    contact = (await db.execute(
        select(ClientContact).where(
            ClientContact.id == contact_id,
            ClientContact.project_id == project_id,
            ClientContact.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if contact is None:
        raise HTTPException(status_code=404, detail="Contact not found en project")
    contact.deleted_at = datetime.now(timezone.utc)
    contact.is_active = False
    await db.flush()
    await db.commit()
