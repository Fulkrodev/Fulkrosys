"""Golden eval runs admin API · sub-atom 1.E.1.B.3.E.

4 endpoints REST `/admin/observability/golden-eval/*` admin-only require_owner:
  - GET    /datasets            · list available datasets per filesystem
  - POST   /run                 · trigger eval run sync (returns run_id)
  - GET    /runs                · historical runs list
  - GET    /runs/{run_id}       · drill-down run detail
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db

from backend.app.motors.m_observability.golden_eval_runs_service import (
    execute_eval_run_sync,
    get_run,
    list_available_datasets,
    list_runs,
    trigger_eval_run,
)


router = APIRouter(
    prefix="/admin/observability/golden-eval",
    tags=["admin - Golden eval runs (1.E.1.B.3.E)"],
    dependencies=[Depends(require_owner)],
)


class TriggerEvalRunRequest(BaseModel):
    agent_name: str = Field(..., min_length=1, max_length=64)
    version: str = Field("v1", min_length=1, max_length=32)
    sync_execute: bool = Field(
        True,
        description=(
            "If True · ejecuta run síncronamente en mismo request (skeleton "
            "phase · entries skipped si capability pending build). If False "
            "· deja queued · futuro Celery beat OR manual sync trigger."
        ),
    )


@router.get("/datasets")
async def admin_list_datasets() -> dict:
    """Returns datasets disponibles para trigger eval."""
    return {"items": list_available_datasets()}


@router.post("/run")
async def admin_trigger_run(
    payload: TriggerEvalRunRequest = Body(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Trigger eval run · status queued → running → completed/failed.

    sync_execute=True (default): ejecuta inmediatamente en mismo request ·
    apropiado para skeleton phase donde entries skipped (NO LLM latency).
    sync_execute=False: deja queued (futuro Celery worker procesa).
    """
    run = await trigger_eval_run(
        db,
        agent_name=payload.agent_name,
        version=payload.version,
    )
    if payload.sync_execute:
        await execute_eval_run_sync(
            db,
            run_id=run.id,
            agent_name=payload.agent_name,
            version=payload.version,
        )
        # Refresh
        detail = await get_run(db, run_id=run.id)
        if detail is None:
            raise HTTPException(status_code=500, detail="run no persistido")
        return detail
    return {"id": str(run.id), "status": run.status}


@router.get("/runs")
async def admin_list_runs(
    agent_name: str | None = Query(None),
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Historical runs list · filtered per agent y days."""
    items = await list_runs(
        db, agent_name=agent_name, days=days, limit=limit,
    )
    return {"days": days, "total": len(items), "items": items}


@router.get("/runs/{run_id}")
async def admin_get_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Drill-down detail per run."""
    detail = await get_run(db, run_id=run_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="run no existe")
    return detail
