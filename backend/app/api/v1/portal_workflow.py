"""API endpoints workflow guidance · portal cliente (FASE 8 · ADR-026).

4 endpoints variant subset de ``/api/v1/workflow/*`` con RBAC
``require_client_user`` + filter `project.client_id == client_user.client_id`.

    GET /api/v1/portal/workflow/current-phase/{project_id} → WorkflowPhase
    GET /api/v1/portal/workflow/next-actions/{project_id}?limit=5 → list[NextAction]
    GET /api/v1/portal/workflow/roadmap/{project_id}              → WorkflowRoadmap
    GET /api/v1/portal/workflow/phase-tasks/{project_id}/{phase}  → list[TaskItem]
      ↑ añadido sub-bloque W4 (8.WORKFLOW.CALIBRATE) coherente W2:
        cliente ve detalle completion real per task (incl. manual_tracking).

Excluidos vs admin (Marcos only):
- ``/phase-progress/{phase}`` detalle métricas (cliente ve roadmap overview)
- ``/my-day-actions`` cross-projects (concepto admin)

Pattern endpoint: 403 si project.client_id ≠ client_user.client_id (cross-tenant
guard) · 404 si proyecto no existe.

Closes: TODO-CLIENT-WORKFLOW-VIEW-001 (formalizado durante 8.A · resuelto 8.B.1).
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_client_user
from backend.app.core.workflow_schemas import NextAction, TaskItem, WorkflowRoadmap
from backend.app.core.workflow_phase import WorkflowPhase
from backend.app.core.workflow_state import (
    get_current_phase,
    get_next_actions,
    get_phase_tasks,
    get_workflow_roadmap,
    verify_client_owns_project,
)
from backend.app.database import get_db


router = APIRouter(
    prefix="/portal/workflow",
    tags=["Portal cliente - Workflow guidance (FASE 8)"],
)


def _client_id_from_request(request: Request) -> uuid.UUID:
    """Extract ClientUser.client_id desde auth subject (post require_client_user)."""
    subject = request.state.auth_subject
    return subject.user.client_id


async def _ensure_owned(
    db: AsyncSession,
    project_id: uuid.UUID,
    client_id: uuid.UUID,
) -> None:
    """Raise 403 si proyecto no pertenece al cliente."""
    if not await verify_client_owns_project(db, project_id, client_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a este proyecto",
        )


@router.get("/current-phase/{project_id}", response_model=WorkflowPhase)
async def portal_current_phase(
    project_id: uuid.UUID,
    request: Request,
    _user: object = Depends(require_client_user),
    db: AsyncSession = Depends(get_db),
) -> WorkflowPhase:
    """Fase actual del proyecto del cliente."""
    await _ensure_owned(db, project_id, _client_id_from_request(request))
    try:
        return await get_current_phase(db, project_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc),
        ) from exc


@router.get("/next-actions/{project_id}", response_model=list[NextAction])
async def portal_next_actions(
    project_id: uuid.UUID,
    request: Request,
    limit: int = 5,
    _user: object = Depends(require_client_user),
    db: AsyncSession = Depends(get_db),
) -> list[NextAction]:
    """Acciones priorizadas pendientes para fase actual del cliente."""
    await _ensure_owned(db, project_id, _client_id_from_request(request))
    try:
        return await get_next_actions(db, project_id, limit=limit)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc),
        ) from exc


@router.get("/roadmap/{project_id}", response_model=WorkflowRoadmap)
async def portal_roadmap(
    project_id: uuid.UUID,
    request: Request,
    _user: object = Depends(require_client_user),
    db: AsyncSession = Depends(get_db),
) -> WorkflowRoadmap:
    """Roadmap completo del proyecto del cliente · 8 fases."""
    await _ensure_owned(db, project_id, _client_id_from_request(request))
    try:
        return await get_workflow_roadmap(db, project_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc),
        ) from exc


@router.get(
    "/phase-tasks/{project_id}/{phase}",
    response_model=list[TaskItem],
)
async def portal_phase_tasks(
    project_id: uuid.UUID,
    phase: WorkflowPhase,
    request: Request,
    _user: object = Depends(require_client_user),
    db: AsyncSession = Depends(get_db),
) -> list[TaskItem]:
    """Tasks template fase con status real per cliente (W4 calibracion).

    Coherente con W2 (queries motor reales + manual_tracking). Cliente ve
    completion honesta per task: 'completed' / 'pending' / 'manual_tracking'
    (esta ultima depende confirmacion Marcos · UI mostrara icono distinto).
    """
    await _ensure_owned(db, project_id, _client_id_from_request(request))
    try:
        return await get_phase_tasks(db, project_id, phase)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc),
        ) from exc
