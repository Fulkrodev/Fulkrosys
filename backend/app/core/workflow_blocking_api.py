"""Workflow blocking REST endpoint (ADR-036 SAN-D MB-17.5).

GET /projects/{id}/workflow/can-transition/{target_phase} expone si
proyecto puede transicionar · UI WorkflowBlockingAlert consume
respuesta · POST /transition deferrable (DEC-5 MB-18 hook
AutoBillingService).
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.core.workflow_blocking_service import (
    WorkflowBlockingResult,
    WorkflowBlockingService,
)
from backend.app.database import get_db, set_tenant_context

router = APIRouter(tags=["MB-17 - Workflow blocking rules"])


@router.get(
    "/projects/{project_id}/workflow/can-transition/{target_phase}",
    response_model=WorkflowBlockingResult,
)
async def check_can_transition(
    project_id: UUID,
    target_phase: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_owner),
) -> WorkflowBlockingResult:
    """Validar si proyecto puede transitionar a target phase (1-indexed)."""
    if target_phase < 1 or target_phase > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="target_phase debe estar en rango [1, 10]",
        )
    # FIX(RLS): resolve owner via SECURITY DEFINER + set tenant context before
    # the service runs select(Project) under the RLS-enforced fulkro_app role
    # (sin esto el SELECT devuelve None y bloquea toda transición).
    _owner = (
        await db.execute(
            sa_text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)},
        )
    ).scalar()
    if not _owner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found",
        )
    await set_tenant_context(db, client_id=_owner, project_id=project_id)
    service = WorkflowBlockingService(db)
    return await service.check_can_transition(project_id, target_phase)
