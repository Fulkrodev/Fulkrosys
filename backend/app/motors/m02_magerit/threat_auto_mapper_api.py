"""ThreatAutoMapper REST endpoint (ADR-037 SAN-D MB-15.2).

POST /projects/{id}/threats/auto-map
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db
from backend.app.motors.m02_magerit.threat_auto_mapper import (
    ThreatAutoMapper,
)

router = APIRouter(tags=["MB-15 - Magerit Threat Auto-Mapper"])


@router.post("/projects/{project_id}/threats/auto-map")
async def trigger_auto_map(
    project_id: UUID,
    analysis_id: UUID | None = Query(
        default=None,
        description=(
            "Análisis específico target · si None usa último análisis del "
            "proyecto · si no existe crea uno lightweight"
        ),
    ),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_owner),
) -> dict:
    """Auto-mapea amenazas Libro II per asset del proyecto.

    Returns:
        dict con `created`, `skipped`, `analysis_id`, `assets_processed`.
    """
    service = ThreatAutoMapper(db)
    return await service.auto_map_threats_for_project(
        project_id=project_id,
        analysis_id=analysis_id,
    )
