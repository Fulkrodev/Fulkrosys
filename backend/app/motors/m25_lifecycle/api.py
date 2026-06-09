"""Motor 25 - Lifecycle API."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db, set_tenant_context
from backend.app.auth.dependencies import require_owner

from .lifecycle_service import (
    ALL_STATES,
    DEFAULT_RETENTION_YEARS,
    VALID_TRANSITIONS,
    LifecycleError,
    LifecycleService,
)


router = APIRouter(
    prefix="/lifecycle", tags=["Motor 25 - Lifecycle"],
    # TODO-RBAC-PER-ENDPOINT-001 Cat A: Marcos-only.
    dependencies=[Depends(require_owner)],
)


async def _set_project_rls(project_id: uuid.UUID, db: AsyncSession):
    client_id = (await db.execute(
        text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)}
    )).scalar()
    if not client_id:
        raise HTTPException(status_code=404, detail="Project not found")
    await set_tenant_context(db, client_id=client_id, project_id=project_id)


# ─────────── Schemas ───────────

class TransitionBody(BaseModel):
    to_state: str = Field(..., min_length=2, max_length=30)
    reason: Optional[str] = None
    triggered_by: str = Field("marcos", max_length=100)
    metadata: Optional[dict] = None


class ArchiveBody(BaseModel):
    retention_years: int = Field(DEFAULT_RETENTION_YEARS, ge=1, le=50)


# ─────────── State machine (catálogo sin RLS) ───────────

@router.get("/states")
async def list_states():
    return {
        "states": ALL_STATES,
        "transitions": VALID_TRANSITIONS,
        "count": len(ALL_STATES),
    }


@router.get("/states/{state}/transitions")
async def state_transitions(state: str):
    if state not in VALID_TRANSITIONS:
        raise HTTPException(status_code=404, detail=f"State {state} no existe")
    return {
        "state": state,
        "allowed_transitions": VALID_TRANSITIONS[state],
    }


# ─────────── Dashboard global (sin RLS) ───────────

@router.get("/summary")
async def lifecycle_summary(db: AsyncSession = Depends(get_db)):
    return await LifecycleService().get_lifecycle_summary(db)


@router.get("/pending-archive")
async def pending_archive(db: AsyncSession = Depends(get_db)):
    summary = await LifecycleService().get_lifecycle_summary(db)
    return {
        "pending_archive": summary["pending_archive"],
        "count": summary["pending_archive_count"],
    }


@router.get("/pending-purge")
async def pending_purge(db: AsyncSession = Depends(get_db)):
    summary = await LifecycleService().get_lifecycle_summary(db)
    return {
        "pending_purge": summary["pending_purge"],
        "count": summary["pending_purge_count"],
    }


# ─────────── Project-scoped (RLS) ───────────

@router.post("/projects/{project_id}/lifecycle/transition")
async def transition(
    project_id: uuid.UUID,
    body: TransitionBody,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    try:
        event = await LifecycleService().transition(
            db, project_id=project_id,
            to_state=body.to_state,
            reason=body.reason,
            triggered_by=body.triggered_by,
            metadata=body.metadata,
        )
    except LifecycleError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return _serialize_event(event)


@router.get("/projects/{project_id}/lifecycle/state")
async def get_state(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    try:
        current = await LifecycleService().get_current_state(db, project_id)
    except LifecycleError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    allowed = await LifecycleService().get_available_transitions(db, project_id)
    return {
        "project_id": str(project_id),
        "current_state": current,
        "available_transitions": allowed,
    }


@router.get("/projects/{project_id}/lifecycle/available-transitions")
async def available_transitions(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    try:
        allowed = await LifecycleService().get_available_transitions(db, project_id)
    except LifecycleError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"transitions": allowed}


@router.get("/projects/{project_id}/lifecycle/history")
async def get_history(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    history = await LifecycleService().get_history(db, project_id)
    return {"history": [_serialize_event(e) for e in history]}


@router.post(
    "/projects/{project_id}/lifecycle/archive",
    status_code=status.HTTP_201_CREATED,
)
async def archive(
    project_id: uuid.UUID,
    body: ArchiveBody,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    try:
        pkg = await LifecycleService().archive_project(
            db, project_id=project_id,
            retention_years=body.retention_years,
        )
    except LifecycleError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return _serialize_archive(pkg)


@router.get("/projects/{project_id}/lifecycle/archive")
async def get_archive(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    pkg = await LifecycleService().get_archive(db, project_id)
    if not pkg:
        raise HTTPException(status_code=404, detail="Archive not found")
    return _serialize_archive(pkg)


@router.post("/projects/{project_id}/lifecycle/purge")
async def purge(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    try:
        pkg = await LifecycleService().purge_project(db, project_id)
    except LifecycleError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return _serialize_archive(pkg)


# ─────────── Serializers ───────────

def _serialize_event(e):
    return {
        "id": str(e.id),
        "project_id": str(e.project_id),
        "state": e.state,
        "previous_state": e.previous_state,
        "entered_at": e.entered_at.isoformat() if e.entered_at else None,
        "entered_by": e.entered_by,
        "reason": e.reason,
        "metadata": e.metadata_extra,
    }


def _serialize_archive(a):
    return {
        "id": str(a.id),
        "project_id": str(a.project_id),
        "client_id": str(a.client_id) if a.client_id else None,
        "project_name": a.project_name,
        "client_name": a.client_name,
        "archive_zip_path": a.archive_zip_path,
        "archive_zip_hash_sha256": a.archive_zip_hash_sha256,
        "archive_zip_size_bytes": a.archive_zip_size_bytes,
        "signature_ed25519": a.signature_ed25519,
        "retention_years": a.retention_years,
        "retention_until": a.retention_until.isoformat() if a.retention_until else None,
        "documents_count": a.documents_count,
        "evidence_count": a.evidence_count,
        "estado": a.estado,
        "archive_completed_at": a.archive_completed_at.isoformat() if a.archive_completed_at else None,
        "purged_at": a.purged_at.isoformat() if a.purged_at else None,
    }
