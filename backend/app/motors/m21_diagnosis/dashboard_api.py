"""Endpoint REST dashboard admin agregado (MB-13.1 · ADR-035).

GET /api/v1/projects/{project_id}/dashboard
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db
from backend.app.motors.m21_diagnosis.dashboard_schemas import DashboardData
from backend.app.motors.m21_diagnosis.dashboard_service import (
    ProjectDashboardService,
)

router = APIRouter()


@router.get(
    "/projects/{project_id}/dashboard",
    response_model=DashboardData,
    summary="Vista agregada home admin proyecto (MB-13.1)",
)
async def get_project_dashboard(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_owner),
) -> DashboardData:
    """Aglutinador info home admin proyecto.

    Combina next-actions priorizadas + readiness score (último run M09) +
    fase actual con label legible + estimación días hasta certificación
    (lookup table per categoría + ajuste por readiness) + bloqueantes
    extraídos del checklist de auditoría.

    ``active_alerts`` se puebla desde m18 alert_queue (AlertService · S26).

    Consumido por ``frontend/components/dashboard/NextActionCard`` y otros
    components home admin (MB-13.5 rediseño completo).
    """
    service = ProjectDashboardService(db)
    try:
        return await service.get_dashboard(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
