"""Workflow blocking REST endpoint (ADR-036 SAN-D MB-17.5).

GET /projects/{id}/workflow/can-transition/{target_phase} expone si
proyecto puede transicionar · UI WorkflowBlockingAlert consume
respuesta · POST /transition deferrable (DEC-5 MB-18 hook
AutoBillingService).
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.core.workflow_blocking_service import (
    WorkflowBlockingResult,
    WorkflowBlockingService,
)
from backend.app.database import get_db

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
    service = WorkflowBlockingService(db)
    return await service.check_can_transition(project_id, target_phase)
