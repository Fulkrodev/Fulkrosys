"""ClientTask REST endpoints (ADR-038 SAN-D MB-14.3).

Cliente:
- GET  /client-portal/tasks                · lista tareas current project
- POST /client-portal/tasks/{id}/start
- POST /client-portal/tasks/{id}/complete
- POST /client-portal/tasks/{id}/block

Admin:
- POST /admin/projects/{id}/tasks/regenerate
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db
from backend.app.models.client_portal import ClientUser
from backend.app.motors.m21_portal_cliente.api import get_current_client_user
from backend.app.motors.m21_portal_cliente.task_service import (
    ClientTaskService,
    TaskError,
)


client_tasks_router = APIRouter(
    tags=["MB-14 - Client Tasks (workspace continuo)"],
)
admin_tasks_router = APIRouter(
    tags=["MB-14 - Admin Tasks Regenerate"],
)


class BlockBody(BaseModel):
    reason: str


def _serialize(task) -> dict:
    # HIGH #6 · marca si la tarea la gestiona Fulkro (primary_actor != cliente) ·
    # el front oculta los botones de acción y la muestra read-only (cliente-mínimo).
    from backend.app.motors.m21_portal_cliente.task_templates_loader import (
        get_template_by_id,
        resolve_primary_actor,
    )
    _tmpl = get_template_by_id(task.template_id)
    managed_by_fulkro = bool(_tmpl) and resolve_primary_actor(_tmpl) != "cliente"
    return {
        "id": str(task.id),
        "project_id": str(task.project_id),
        "template_id": task.template_id,
        "managed_by_fulkro": managed_by_fulkro,
        "phase": task.phase,
        "title": task.title,
        "description": task.description,
        "cta_label": task.cta_label,
        "cta_url": task.cta_url,
        "expected_evidence_type": task.expected_evidence_type,
        "expected_evidence_count": task.expected_evidence_count,
        "priority": task.priority,
        "status": task.status,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "started_at": (
            task.started_at.isoformat() if task.started_at else None
        ),
        "completed_at": (
            task.completed_at.isoformat() if task.completed_at else None
        ),
        "blocked_reason": task.blocked_reason,
    }


async def _resolve_project_id(db: AsyncSession, client_user: ClientUser) -> UUID:
    """Resolve project_id activo del cliente (latest non-deleted)."""
    result = await db.execute(
        text(
            "SELECT id FROM projects WHERE client_id = :cid "
            "AND deleted_at IS NULL "
            "ORDER BY created_at DESC LIMIT 1"
        ),
        {"cid": str(client_user.client_id)},
    )
    project_id = result.scalar_one_or_none()
    if not project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sin proyecto activo",
        )
    # Set tenant context for RLS
    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": str(project_id)},
    )
    await db.execute(
        text("SELECT set_config('app.current_client_id', :cid, true)"),
        {"cid": str(client_user.client_id)},
    )
    return project_id


@client_tasks_router.get("/client-portal/tasks")
async def list_my_tasks(
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> list[dict]:
    """Cliente lista sus tareas del proyecto activo."""
    project_id = await _resolve_project_id(db, user)
    service = ClientTaskService(db)
    tasks = await service.list_tasks(project_id, status=status_filter)
    return [_serialize(t) for t in tasks]


@client_tasks_router.post("/client-portal/tasks/{task_id}/start")
async def start_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> dict:
    pid = await _resolve_project_id(db, user)
    service = ClientTaskService(db)
    try:
        task = await service.transition(
            task_id, "in_progress", client_initiated=True, expected_project_id=pid,
        )
    except TaskError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc),
        )
    await db.commit()  # get_db() no auto-commitea: persistir la transición
    return _serialize(task)


@client_tasks_router.post("/client-portal/tasks/{task_id}/complete")
async def complete_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> dict:
    pid = await _resolve_project_id(db, user)
    service = ClientTaskService(db)
    try:
        task = await service.transition(
            task_id, "done", client_initiated=True, expected_project_id=pid,
        )
    except TaskError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc),
        )
    # commit DESPUÉS de transition() (que propaga el desbloqueo de dependientes)
    await db.commit()  # get_db() no auto-commitea
    return _serialize(task)


@client_tasks_router.post("/client-portal/tasks/{task_id}/approve-plan")
async def approve_plan_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> dict:
    """#27 Ola 6 · el cliente aprueba el Plan de Adecuación (acción discreta).

    Aprobación trazable (audit_log R6 plan.approved + estado done + SSE) · NO
    es firma criptográfica. Doble pool: get_current_client_user + RLS context.
    """
    pid = await _resolve_project_id(db, user)
    service = ClientTaskService(db)
    try:
        task = await service.approve_plan(
            task_id, client_user_id=user.id, client_id=user.client_id,
            expected_project_id=pid,
        )
    except TaskError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc),
        )
    # get_db NO auto-commit · persistir tarea done + audit_log explícitamente.
    await db.commit()
    return _serialize(task)


@client_tasks_router.post("/client-portal/tasks/{task_id}/block")
async def block_task(
    task_id: UUID,
    body: BlockBody,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> dict:
    pid = await _resolve_project_id(db, user)
    service = ClientTaskService(db)
    try:
        task = await service.transition(
            task_id, "blocked", blocked_reason=body.reason,
            client_initiated=True, expected_project_id=pid,
        )
    except TaskError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc),
        )
    await db.commit()  # get_db() no auto-commitea: persistir el bloqueo
    return _serialize(task)


@admin_tasks_router.post("/projects/{project_id}/tasks/regenerate")
async def admin_regenerate_tasks(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_owner),
) -> dict:
    """Admin force regenerate tasks aplicables fase actual proyecto."""
    service = ClientTaskService(db)
    return await service.regenerate_for_project(project_id)
