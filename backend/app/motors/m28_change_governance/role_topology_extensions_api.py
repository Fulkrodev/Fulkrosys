"""M28 Role Topology + Drift Summary extensions · SAN-E v3.MB-3.E.

4 endpoints:
    GET  /api/v1/projects/{id}/role-topology              · MB-3.5 frontend wired
    POST /api/v1/projects/{id}/role-topology/{role_code}/assign
    POST /api/v1/projects/{id}/role-topology/{role_code}/vacate
    GET  /api/v1/projects/{id}/drift-summary
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import CurrentUser, require_owner
from backend.app.database import get_db, set_tenant_context
from backend.app.models.m28_role_assignment import (
    ALL_ROLE_CODES,
    CROSS_COMPLIANCE_ROLES,
    ENS_REQUIRED_ROLES,
    ProjectRoleAssignment,
)
from backend.app.motors.m30_client_contacts.models import ClientContact


router = APIRouter(
    prefix="/projects/{project_id}",
    tags=["Motor 28 - Role Topology + Drift"],
    dependencies=[Depends(require_owner)],
)


async def _set_project_rls(project_id: uuid.UUID, db: AsyncSession) -> None:
    client_id = (await db.execute(
        text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)}
    )).scalar()
    if not client_id:
        raise HTTPException(status_code=404, detail="Project not found")
    await set_tenant_context(db, client_id=client_id, project_id=project_id)


async def _get_or_create_assignment(
    project_id: uuid.UUID, role_code: str, db: AsyncSession,
) -> ProjectRoleAssignment:
    if role_code not in ALL_ROLE_CODES:
        raise HTTPException(
            status_code=422,
            detail=f"role_code invalido. Valores permitidos: {ALL_ROLE_CODES}",
        )
    row = (await db.execute(
        select(ProjectRoleAssignment).where(
            ProjectRoleAssignment.project_id == project_id,
            ProjectRoleAssignment.role_code == role_code,
            ProjectRoleAssignment.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if row is not None:
        return row
    row = ProjectRoleAssignment(
        project_id=project_id,
        role_code=role_code,
        is_required=role_code in ENS_REQUIRED_ROLES,
        is_cross_compliance=role_code in CROSS_COMPLIANCE_ROLES,
    )
    db.add(row)
    await db.flush()
    return row


class AssignRoleBody(BaseModel):
    contact_id: uuid.UUID
    notes: str | None = Field(None, max_length=2000)


@router.get("/role-topology")
async def list_role_topology(
    project_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Lista assignments de los roles ENS_REQUIRED + CROSS_COMPLIANCE para el proyecto.

    Para cada role_code:
    - Si existe ProjectRoleAssignment row, devuelve su data + contact info join
    - Si NO existe, devuelve placeholder con assignment=None (rol vacante)
    """
    await _set_project_rls(project_id, db)

    rows = (await db.execute(
        select(ProjectRoleAssignment).where(
            ProjectRoleAssignment.project_id == project_id,
            ProjectRoleAssignment.deleted_at.is_(None),
        )
    )).scalars().all()
    by_code = {r.role_code: r for r in rows}

    contact_ids = {r.contact_id for r in rows if r.contact_id is not None}
    contacts: dict[uuid.UUID, ClientContact] = {}
    if contact_ids:
        contact_rows = (await db.execute(
            select(ClientContact).where(
                ClientContact.id.in_(contact_ids),
                ClientContact.deleted_at.is_(None),
            )
        )).scalars().all()
        contacts = {c.id: c for c in contact_rows}

    def _serialize(role_code: str) -> dict[str, Any]:
        is_required = role_code in ENS_REQUIRED_ROLES
        is_cross_compliance = role_code in CROSS_COMPLIANCE_ROLES
        row = by_code.get(role_code)
        if row is None or row.contact_id is None:
            return {
                "role_code": role_code,
                "is_required": is_required,
                "is_cross_compliance": is_cross_compliance,
                "assignment_id": str(row.id) if row else None,
                "contact_id": None,
                "contact": None,
                "assigned_at": None,
                "assigned_by": None,
                "notes": row.notes if row else None,
            }
        contact = contacts.get(row.contact_id)
        return {
            "role_code": role_code,
            "is_required": is_required,
            "is_cross_compliance": is_cross_compliance,
            "assignment_id": str(row.id),
            "contact_id": str(row.contact_id),
            "contact": (
                {
                    "id": str(contact.id),
                    "full_name": contact.full_name,
                    "email": contact.email,
                    "phone": contact.phone,
                    "role_title": contact.role_title,
                    "has_portal_access": contact.has_portal_access,
                }
                if contact else None
            ),
            "assigned_at": row.assigned_at.isoformat() if row.assigned_at else None,
            "assigned_by": row.assigned_by,
            "notes": row.notes,
        }

    required_assignments = [_serialize(rc) for rc in ENS_REQUIRED_ROLES]
    cross_assignments = [_serialize(rc) for rc in CROSS_COMPLIANCE_ROLES]

    assigned_required = sum(1 for a in required_assignments if a["contact_id"])
    blockers = [
        a["role_code"] for a in required_assignments if not a["contact_id"]
    ]
    coverage_pct = round(
        100 * assigned_required / len(ENS_REQUIRED_ROLES), 1
    ) if ENS_REQUIRED_ROLES else 0.0

    return {
        "project_id": str(project_id),
        "roles_required": required_assignments,
        "cross_compliance_extras": cross_assignments,
        "coverage_pct": coverage_pct,
        "assigned_required": assigned_required,
        "total_required": len(ENS_REQUIRED_ROLES),
        "blockers": blockers,
    }


@router.post("/role-topology/{role_code}/assign")
async def assign_role(
    project_id: uuid.UUID,
    role_code: str,
    body: AssignRoleBody,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _set_project_rls(project_id, db)
    # Validar contact existe en proyecto (project_id O client-scoped del mismo cliente)
    contact = (await db.execute(
        select(ClientContact).where(
            ClientContact.id == body.contact_id,
            ClientContact.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    if contact.project_id is not None and contact.project_id != project_id:
        raise HTTPException(
            status_code=422,
            detail="Contact pertenece a otro project (scope conflict)",
        )

    assignment = await _get_or_create_assignment(project_id, role_code, db)
    assignment.contact_id = body.contact_id
    assignment.assigned_at = datetime.now(timezone.utc)
    assignment.assigned_by = str(user.id) if user else None
    if body.notes is not None:
        assignment.notes = body.notes
    await db.flush()
    await db.commit()
    return {
        "id": str(assignment.id),
        "project_id": str(project_id),
        "role_code": role_code,
        "contact_id": str(body.contact_id),
        "contact_name": contact.full_name,
        "assigned_at": assignment.assigned_at.isoformat(),
        "is_required": assignment.is_required,
        "is_cross_compliance": assignment.is_cross_compliance,
    }


@router.post("/role-topology/{role_code}/vacate")
async def vacate_role(
    project_id: uuid.UUID,
    role_code: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _set_project_rls(project_id, db)
    if role_code not in ALL_ROLE_CODES:
        raise HTTPException(status_code=422, detail="role_code invalido")
    assignment = (await db.execute(
        select(ProjectRoleAssignment).where(
            ProjectRoleAssignment.project_id == project_id,
            ProjectRoleAssignment.role_code == role_code,
            ProjectRoleAssignment.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if assignment is None or assignment.contact_id is None:
        raise HTTPException(status_code=404, detail="Role no asignado en este proyecto")
    assignment.contact_id = None
    assignment.assigned_at = None
    assignment.assigned_by = None
    await db.flush()
    await db.commit()
    return {
        "id": str(assignment.id),
        "project_id": str(project_id),
        "role_code": role_code,
        "vacated": True,
    }


@router.get("/drift-summary")
async def get_drift_summary(
    project_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retorna matrix 10 dimensiones x 4 severidades.

    Nota: la vista materializada `mv_drift_summary_10x4` se refresca via
    job programado (M28 jobs.py). Endpoint NO ejecuta REFRESH en transaction
    (PostgreSQL aborta la session si REFRESH falla bajo algunas variantes).
    """
    await _set_project_rls(project_id, db)
    rows = (await db.execute(
        text(
            "SELECT dimension, severidad, open_count, closed_count, "
            "total_count, last_detected "
            "FROM mv_drift_summary_10x4 "
            "WHERE project_id = :pid "
            "ORDER BY dimension, severidad"
        ),
        {"pid": str(project_id)},
    )).fetchall()
    items = [
        {
            "dimension": r[0],
            "severidad": r[1],
            "open_count": r[2],
            "closed_count": r[3],
            "total_count": r[4],
            "last_detected": r[5].isoformat() if r[5] else None,
        }
        for r in rows
    ]
    by_severity: dict[str, int] = {}
    for it in items:
        by_severity[it["severidad"]] = by_severity.get(it["severidad"], 0) + it["open_count"]
    return {
        "project_id": str(project_id),
        "items": items,
        "open_total": sum(by_severity.values()),
        "open_by_severity": by_severity,
    }
