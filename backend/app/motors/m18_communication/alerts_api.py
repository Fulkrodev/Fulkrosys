"""Endpoints REST alertas proactivas (MB-13.4 · ADR-035).

GET    /api/v1/alerts/active                       lista global admin
GET    /api/v1/projects/{project_id}/alerts        lista per proyecto
POST   /api/v1/alerts/{alert_id}/acknowledge       marcar como leida
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text as _sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db, set_tenant_context
from backend.app.models.auth import User
from backend.app.motors.m18_communication.alert_schemas import AlertResponse
from backend.app.motors.m18_communication.alert_service import AlertService

router = APIRouter()


@router.get(
    "/alerts/active",
    response_model=list[AlertResponse],
    summary="Lista alertas activas globales admin (MB-13.4)",
)
async def list_active_alerts_global(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_owner),
) -> list[AlertResponse]:
    service = AlertService(db)
    alerts = await service.list_active_global()
    return [AlertResponse.model_validate(a) for a in alerts]


@router.get(
    "/projects/{project_id}/alerts",
    response_model=list[AlertResponse],
    summary="Alertas activas per proyecto (MB-13.4)",
)
async def list_project_alerts(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_owner),
) -> list[AlertResponse]:
    # FIX(RLS): resolve owner via SECURITY DEFINER + set tenant context before RLS query
    _owner = (
        await db.execute(_sa_text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)})
    ).scalar()
    if not _owner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    await set_tenant_context(db, client_id=_owner, project_id=project_id)
    service = AlertService(db)
    alerts = await service.list_active_alerts(project_id)
    return [AlertResponse.model_validate(a) for a in alerts]


@router.post(
    "/alerts/{alert_id}/acknowledge",
    summary="Marca alerta como acknowledged (MB-13.4)",
)
async def acknowledge_alert(
    alert_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_owner),
) -> dict:
    service = AlertService(db)
    success = await service.acknowledge(alert_id, user_id=user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found or already acknowledged",
        )
    await db.commit()
    return {"acknowledged": True}
