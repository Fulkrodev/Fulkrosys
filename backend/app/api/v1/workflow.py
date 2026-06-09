"""API endpoints workflow guidance · FASE 8 (ADR-026).

5 endpoints expose 4 funciones derive_state ``backend/app/core/workflow_state.py``:

    GET /api/v1/workflow/current-phase/{project_id}        → WorkflowPhase
    GET /api/v1/workflow/next-actions/{project_id}?limit=5 → list[NextAction]
    GET /api/v1/workflow/phase-progress/{project_id}/{phase} → PhaseProgress
    GET /api/v1/workflow/phase-tasks/{project_id}/{phase}  → list[TaskItem]
    GET /api/v1/workflow/roadmap/{project_id}              → WorkflowRoadmap

RBAC: ``require_owner`` (Marcos · admin only). Cliente access vía endpoints
``/api/v1/portal/*`` queda fuera de scope FASE 8 (TODO-CLIENT-WORKFLOW-VIEW
post-deploy si requerido).

Pattern endpoints:
- Read-only (GET) · sin commit() necesario
- ``set_tenant_context`` aplicada vía global dep ``authenticate_request``
- Errores ValueError → 404 (proyecto no encontrado)
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.core.workflow_phase import WorkflowPhase
from backend.app.core.workflow_schemas import (
    NextAction,
    PhaseProgress,
    TaskItem,
    WorkflowRoadmap,
)
from backend.app.core.workflow_state import (
    get_current_phase,
    get_next_actions,
    get_phase_progress,
    get_phase_tasks,
    get_workflow_roadmap,
)
from backend.app.database import get_db, set_tenant_context
from sqlalchemy import text as _sa_text


router = APIRouter(prefix="/workflow", tags=["Workflow guidance (FASE 8)"])


async def _set_project_rls(project_id: uuid.UUID, db: AsyncSession) -> None:
    """HIGH #3 · fija el contexto RLS (la global dep NO lo hace para admin).

    Sin esto, los SELECT sobre projects bajo RLS (client_id=current_client_id())
    ocultan la fila → get_current_phase devuelve None → ValueError 'not found' →
    404 espurio aun con el project_id correcto. Patrón canónico (projects.py).
    """
    cid = (await db.execute(
        _sa_text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)},
    )).scalar()
    if not cid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found",
        )
    await set_tenant_context(db, client_id=cid, project_id=project_id)


@router.get("/current-phase/{project_id}", response_model=WorkflowPhase)
async def current_phase_endpoint(
    project_id: uuid.UUID,
    _user: object = Depends(require_owner),
    db: AsyncSession = Depends(get_db),
) -> WorkflowPhase:
    """Fase actual del proyecto (ADR-026 · projects.fase persistido)."""
    try:
        await _set_project_rls(project_id, db)
        return await get_current_phase(db, project_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc),
        ) from exc


@router.get("/next-actions/{project_id}", response_model=list[NextAction])
async def next_actions_endpoint(
    project_id: uuid.UUID,
    limit: int = 5,
    _user: object = Depends(require_owner),
    db: AsyncSession = Depends(get_db),
) -> list[NextAction]:
    """Acciones priorizadas pendientes para fase actual del proyecto."""
    try:
        await _set_project_rls(project_id, db)
        return await get_next_actions(db, project_id, limit=limit)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc),
        ) from exc


@router.get(
    "/phase-progress/{project_id}/{phase}",
    response_model=PhaseProgress,
)
async def phase_progress_endpoint(
    project_id: uuid.UUID,
    phase: WorkflowPhase,
    _user: object = Depends(require_owner),
    db: AsyncSession = Depends(get_db),
) -> PhaseProgress:
    """Métricas progreso fase específica del proyecto."""
    try:
        await _set_project_rls(project_id, db)
        return await get_phase_progress(db, project_id, phase)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc),
        ) from exc


@router.get(
    "/phase-tasks/{project_id}/{phase}",
    response_model=list[TaskItem],
)
async def phase_tasks_endpoint(
    project_id: uuid.UUID,
    phase: WorkflowPhase,
    _user: object = Depends(require_owner),
    db: AsyncSession = Depends(get_db),
) -> list[TaskItem]:
    """Tareas template fase con status derivado vs current_phase."""
    try:
        await _set_project_rls(project_id, db)
        return await get_phase_tasks(db, project_id, phase)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc),
        ) from exc


@router.get("/roadmap/{project_id}", response_model=WorkflowRoadmap)
async def roadmap_endpoint(
    project_id: uuid.UUID,
    _user: object = Depends(require_owner),
    db: AsyncSession = Depends(get_db),
) -> WorkflowRoadmap:
    """Roadmap completo proyecto · 8 fases con estados."""
    try:
        await _set_project_rls(project_id, db)
        return await get_workflow_roadmap(db, project_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc),
        ) from exc
