"""ThreatAutoMapper REST endpoint (ADR-037 SAN-D MB-15.2).

POST /projects/{id}/threats/auto-map
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text as _sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db, set_tenant_context
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
    # FIX(RLS): resolve owner via SECURITY DEFINER + set tenant context before
    # the service touches RLS-protected tables (Project, magerit_assets).
    _owner = (
        await db.execute(
            _sa_text("SELECT get_project_owner(:pid)"),
            {"pid": str(project_id)},
        )
    ).scalar()
    if not _owner:
        raise HTTPException(status_code=404, detail="Project not found")
    await set_tenant_context(db, client_id=_owner, project_id=project_id)

    service = ThreatAutoMapper(db)
    result = await service.auto_map_threats_for_project(
        project_id=project_id,
        analysis_id=analysis_id,
    )
    # FIX(commit): get_db NO auto-commitea (database.py:30-35) y el service solo
    # hace flush() → sin este commit las filas MageritThreatAssessment se
    # revierten al cerrar la sesión (rollback). Espejo de los 15 commits de
    # m02_magerit/api.py.
    await db.commit()
    return result
