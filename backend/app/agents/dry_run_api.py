"""AuditDryRun REST endpoints (ADR-037 SAN-D MB-15.1).

Routes:
- POST /projects/{id}/audit-dry-run/execute    · trigger orchestrator
- GET  /projects/{id}/audit-dry-run/summary    · resumen + histórico
- GET  /projects/{id}/audit-dry-run/results/{result_id}  · detalle
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agents.schemas.dry_run import DryRunResult, DryRunSummary
from backend.app.agents.services.audit_dry_run_service import (
    AuditDryRunService,
)
from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db

router = APIRouter(tags=["MB-15 - Audit Dry-Run (A11+M10)"])


@router.post(
    "/projects/{project_id}/audit-dry-run/execute",
    response_model=DryRunResult,
)
async def execute_dry_run(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_owner),
) -> DryRunResult:
    """Trigger AuditDryRunService orchestrator M10+A11."""
    service = AuditDryRunService(db)
    try:
        return await service.execute_dry_run(
            project_id=project_id, executor_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc),
        )


@router.get(
    "/projects/{project_id}/audit-dry-run/summary",
    response_model=DryRunSummary,
)
async def get_dry_run_summary(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_owner),
) -> DryRunSummary:
    service = AuditDryRunService(db)
    return await service.get_summary(project_id)


@router.get(
    "/projects/{project_id}/audit-dry-run/results/{result_id}",
    response_model=DryRunResult,
)
async def get_dry_run_result(
    project_id: UUID,
    result_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_owner),
) -> DryRunResult:
    service = AuditDryRunService(db)
    result = await service.get_result(project_id, result_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dry-run result not found",
        )
    return result
