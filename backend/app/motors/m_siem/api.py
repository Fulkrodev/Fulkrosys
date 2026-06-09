"""SIEM API · consola admin de eventos de seguridad (FRENTE N).

Top-level admin cross-cliente legítimo (R23 · como /operations · /compliance) ·
require_owner (ADR-013 · solo Marcos) · read-only (ADR-014). Cross-tenant ⇒
SET LOCAL ROLE fulkro_app_bypassrls (patrón operations/cross-project). Filtro opcional por
project_id para vista project-scoped.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db
from backend.app.motors.m_siem.service import (
    aggregate_security_events,
    compute_correlations,
    siem_overview,
)

router = APIRouter(prefix="/admin/siem", tags=["SIEM (FRENTE N)"])


@router.get("/overview")
async def get_siem_overview(
    project_id: Optional[uuid.UUID] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_owner),
) -> dict:
    """Resumen SIEM · conteos por severidad/fuente + correlaciones + eventos
    recientes (op.mon.2 sistema de métricas). Foco pentest/incidentes."""
    await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
    return await siem_overview(db, project_id=project_id, limit=limit)


@router.get("/events")
async def get_siem_events(
    project_id: Optional[uuid.UUID] = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_owner),
) -> dict:
    """Timeline de eventos de seguridad agregados + correlaciones deterministas."""
    await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
    events = await aggregate_security_events(db, project_id=project_id, limit=limit)
    return {
        "events": [e.to_dict() for e in events],
        "correlations": [c.to_dict() for c in compute_correlations(events)],
    }
