"""AI Act art.50 transparency API · sub-atom 1.E.1.B.2.

3 endpoints REST:
  - GET /admin/projects/{project_id}/transparency/log · require_owner
  - GET /client-portal/transparency/log · require_client_user
    (cliente solo ve eventos de SU client_id · cross-project)
  - Internal helper service-to-service · NO HTTP endpoint (use
    log_transparency_event() helper directo desde agents)

R29 firmísimo cliente · friendly fields only mapped (NO leak technical
llm_provider/llm_model · NO leak metadata sensitive).
ADR-013 doble pool auth respected.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_client_user, require_owner
from backend.app.database import get_db
from backend.app.models.client_portal import ClientUser

from backend.app.motors.m_observability.transparency_service import (
    get_client_transparency_log,
    get_project_transparency_log,
)


# ============================================================
# Admin router · /admin/projects/{project_id}/transparency/*
# ============================================================


admin_router = APIRouter(
    prefix="/admin",
    tags=["admin - AI Act transparency (1.E.1.B.2)"],
    dependencies=[Depends(require_owner)],
)


@admin_router.get("/projects/{project_id}/transparency/log")
async def admin_project_transparency_log(
    project_id: uuid.UUID,
    days: int = Query(180, ge=1, le=730),
    limit: int = Query(200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Admin full view per project · all transparency events últimos N días.

    Includes technical fields (llm_provider · llm_model · metadata) para
    auditor ENAC forensic review. NO restricción cross-cliente para admin.
    """
    result = await get_project_transparency_log(
        db, project_id=project_id, days=days, limit=limit,
    )
    return {
        "project_id": str(project_id),
        "days": result.days,
        "total": result.total,
        "items": result.items,
    }


# ============================================================
# Client-portal router · /client-portal/transparency/*
# ============================================================


client_router = APIRouter(
    prefix="/client-portal",
    tags=["Client Portal · AI Act transparency (1.E.1.B.2)"],
    dependencies=[Depends(require_client_user)],
)


@client_router.get("/transparency/log")
async def client_transparency_log(
    days: int = Query(180, ge=1, le=730),
    limit: int = Query(200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(require_client_user),
) -> dict:
    """Cliente portal view · transparency events de SU client_id solamente.

    R29 firmísimo · friendly response (NO leak llm_provider/llm_model/metadata
    technical · purpose statement cliente-readable solo). Cliente NUNCA ve
    eventos de otros clientes (RLS + client_id filter enforced server-side).
    """
    if user.client_id is None:
        raise HTTPException(
            status_code=403,
            detail="Usuario portal sin client_id asignado",
        )
    result = await get_client_transparency_log(
        db, client_id=user.client_id, days=days, limit=limit,
    )
    return {
        "client_id": str(user.client_id),
        "days": result.days,
        "total": result.total,
        "items": result.items,
    }
