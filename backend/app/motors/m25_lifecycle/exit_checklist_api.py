"""M25 Exit Checklist · REST API endpoints (ADR-046 v3 SAN-E.MB-3.A).

4 endpoints scope project:
    GET   /projects/{project_id}/exit-checklist
    POST  /projects/{project_id}/exit-checklist/{item_id}/complete
    POST  /projects/{project_id}/exit-checklist/{item_id}/uncomplete
    POST  /projects/{project_id}/exit-checklist/check-readiness

RBAC: require_owner (admin Marcos-only · pattern canonico M25 lifecycle).
RLS: project_isolation policy aplica · _set_project_rls activa contexto.
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import CurrentUser, require_owner
from backend.app.database import get_db, set_tenant_context
from backend.app.motors.m25_lifecycle.exit_checklist_service import (
    ExitChecklistError,
    M25ExitService,
)


router = APIRouter(
    prefix="/projects/{project_id}/exit-checklist",
    tags=["Motor 25 - Exit Checklist"],
    dependencies=[Depends(require_owner)],
)


async def _set_project_rls(project_id: uuid.UUID, db: AsyncSession) -> None:
    client_id = (await db.execute(
        text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)}
    )).scalar()
    if not client_id:
        raise HTTPException(status_code=404, detail="Project not found")
    await set_tenant_context(db, client_id=client_id, project_id=project_id)


class CompleteBody(BaseModel):
    evidence_id: uuid.UUID | None = None
    note: str | None = Field(default=None, max_length=2000)


class UncompleteBody(BaseModel):
    note: str | None = Field(default=None, max_length=2000)


class SetStatusBody(BaseModel):
    status: str = Field(..., pattern="^(pendiente|completado|bloqueado|no_aplica)$")
    note: str | None = Field(default=None, max_length=2000)


@router.get("")
async def list_exit_checklist(
    project_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _set_project_rls(project_id, db)
    data = await M25ExitService(db).list_items(project_id)
    return {
        "project_id": str(project_id),
        "items": [
            {
                "id": str(i.id),
                "item_code": i.item_code,
                "label": i.label,
                "category": i.category,
                "status": i.status,
                "evidence_id": str(i.evidence_id) if i.evidence_id else None,
                "completed_at": i.completed_at.isoformat() if i.completed_at else None,
                "completed_by": i.completed_by,
                "note": i.note,
            }
            for i in data.items
        ],
        "progress": data.progress,
    }


@router.post("/{item_id}/complete")
async def complete_item(
    project_id: uuid.UUID,
    item_id: uuid.UUID,
    body: CompleteBody,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _set_project_rls(project_id, db)
    try:
        item = await M25ExitService(db).complete_item(
            project_id=project_id,
            item_id=item_id,
            evidence_id=body.evidence_id,
            note=body.note,
            user_id=str(user.id) if user else None,
        )
    except ExitChecklistError as e:
        raise HTTPException(status_code=404, detail=str(e))
    await db.commit()
    return {
        "id": str(item.id),
        "item_code": item.item_code,
        "status": item.status,
        "completed_at": item.completed_at.isoformat() if item.completed_at else None,
    }


@router.post("/{item_id}/uncomplete")
async def uncomplete_item(
    project_id: uuid.UUID,
    item_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _set_project_rls(project_id, db)
    try:
        item = await M25ExitService(db).uncomplete_item(
            project_id=project_id,
            item_id=item_id,
            user_id=str(user.id) if user else None,
        )
    except ExitChecklistError as e:
        raise HTTPException(status_code=404, detail=str(e))
    await db.commit()
    return {
        "id": str(item.id),
        "item_code": item.item_code,
        "status": item.status,
    }


@router.post("/{item_id}/set-status")
async def set_status_item(
    project_id: uuid.UUID,
    item_id: uuid.UUID,
    body: SetStatusBody,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Endpoint conveniencia · permite marcar bloqueado/no_aplica directamente."""
    await _set_project_rls(project_id, db)
    try:
        item = await M25ExitService(db).set_status(
            project_id=project_id,
            item_id=item_id,
            status=body.status,
            note=body.note,
            user_id=str(user.id) if user else None,
        )
    except ExitChecklistError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await db.commit()
    return {
        "id": str(item.id),
        "item_code": item.item_code,
        "status": item.status,
        "completed_at": item.completed_at.isoformat() if item.completed_at else None,
    }


@router.post("/check-readiness")
async def check_readiness(
    project_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _set_project_rls(project_id, db)
    readiness = await M25ExitService(db).check_readiness(project_id)
    return {
        "ready_to_close": readiness.ready_to_close,
        "total": readiness.total,
        "completed": readiness.completed,
        "blockers": readiness.blockers,
        "warnings": readiness.warnings,
    }
