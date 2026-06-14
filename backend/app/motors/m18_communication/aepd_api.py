"""AEPD API · SAN-C MB-11.2.

Endpoints
---------
- POST /api/v1/projects/{id}/aepd/evaluate
  Evalúa árbol decisión + persiste AepdNotification (si requires_notification)
  + retorna payload pre-filled portal AEPD.
- GET  /api/v1/projects/{id}/aepd/notifications
  Lista notificaciones AEPD del proyecto con countdown deadline restante.

Wire-up frontend (ADR-034): frontend/lib/admin-aepd/api.ts + AepdPanel.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy import text as _sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db, set_tenant_context
from backend.app.models.aepd import AepdNotification
from backend.app.models.core import Client, Project
from backend.app.motors.m18_communication.aepd_connector import (
    prepare_aepd_payload,
)
from backend.app.motors.m18_communication.aepd_decision_tree import (
    IncidentInput,
    evaluate_decision_tree,
)

# ADR-013: gestión de brechas AEPD (op.exp.7) es operación admin. require_owner
# cierra el IDOR (antes el router no tenía dependencia de auth).
router = APIRouter(
    prefix="/projects",
    tags=["M18 - AEPD (MB-11.2)"],
    dependencies=[Depends(require_owner)],
)


async def _set_project_rls(project_id: uuid.UUID, db: AsyncSession) -> None:
    """FIX(RLS): projects + aepd_notifications son RLS fail-closed bajo fulkro_app.
    Sin contexto, db.get(Project) → None → 404 y el INSERT viola WITH CHECK."""
    owner = (
        await db.execute(
            _sa_text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)}
        )
    ).scalar()
    if not owner:
        raise HTTPException(404, "Project not found")
    await set_tenant_context(db, client_id=owner, project_id=project_id)


class AepdEvaluateRequest(BaseModel):
    affects_personal_data: bool
    risk_to_rights: str = Field(..., pattern="^(low|medium|high)$")
    severity: str = Field("medium", pattern="^(low|medium|high|critical)$")
    incident_id: Optional[uuid.UUID] = None
    detected_at: Optional[datetime] = None
    description: Optional[str] = None
    data_categories: Optional[list[str]] = None
    consequences: Optional[str] = None
    measures_taken: Optional[str] = None


class AepdEvaluateResponse(BaseModel):
    requires_notification: bool
    notify_subjects: bool
    deadline_hours: Optional[int]
    register_only: bool
    decision_path: list[str]
    notification_id: Optional[uuid.UUID] = None
    prefilled_payload: Optional[dict] = None
    submission_url: Optional[str] = None


class AepdNotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    project_id: uuid.UUID
    incident_id: Optional[uuid.UUID]
    severity: str
    requires_notification: bool
    notify_subjects: bool
    deadline_hours: Optional[int]
    decision_tree_path: Optional[list[str]]
    notification_status: str
    detected_at: Optional[datetime]
    created_at: datetime
    deadline_hours_remaining: Optional[float] = None


@router.post(
    "/{project_id}/aepd/evaluate",
    response_model=AepdEvaluateResponse,
)
async def post_evaluate_aepd(
    project_id: uuid.UUID,
    body: AepdEvaluateRequest,
    db: AsyncSession = Depends(get_db),
) -> AepdEvaluateResponse:
    await _set_project_rls(project_id, db)
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(404, "Project not found")

    decision = evaluate_decision_tree(
        IncidentInput(
            affects_personal_data=body.affects_personal_data,
            risk_to_rights=body.risk_to_rights,
            affected_categories=body.data_categories,
            description=body.description,
        )
    )

    notification: Optional[AepdNotification] = None
    payload: Optional[dict] = None
    submission_url: Optional[str] = None

    if decision.notify or decision.register_only:
        notification = AepdNotification(
            project_id=project_id,
            incident_id=body.incident_id,
            severity=body.severity,
            requires_notification=decision.notify,
            notify_subjects=decision.notify_subjects,
            deadline_hours=decision.deadline_hours,
            decision_tree_path=decision.path,
            notification_status="pending" if decision.notify else "register_only",
            detected_at=body.detected_at or datetime.now(timezone.utc),
        )
        db.add(notification)
        await db.flush()

    if decision.notify:
        client = await db.get(Client, project.client_id)
        if client is None:
            raise HTTPException(404, "Client not found")
        payload = prepare_aepd_payload(
            responsable_nombre=client.nombre,
            responsable_cif=client.cif,
            detected_at=body.detected_at,
            description=body.description,
            data_categories=body.data_categories,
            consequences=body.consequences,
            measures_taken=body.measures_taken,
        )
        submission_url = payload["portal_url"]

    await db.commit()

    return AepdEvaluateResponse(
        requires_notification=decision.notify,
        notify_subjects=decision.notify_subjects,
        deadline_hours=decision.deadline_hours,
        register_only=decision.register_only,
        decision_path=decision.path,
        notification_id=notification.id if notification else None,
        prefilled_payload=payload,
        submission_url=submission_url,
    )


@router.get(
    "/{project_id}/aepd/notifications",
    response_model=list[AepdNotificationResponse],
)
async def get_aepd_notifications(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[AepdNotificationResponse]:
    await _set_project_rls(project_id, db)
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(404, "Project not found")

    result = await db.execute(
        select(AepdNotification)
        .where(AepdNotification.project_id == project_id)
        .order_by(AepdNotification.created_at.desc())
    )
    notifications = list(result.scalars().all())

    now = datetime.now(timezone.utc)
    out: list[AepdNotificationResponse] = []
    for n in notifications:
        remaining: Optional[float] = None
        if n.deadline_hours and n.detected_at:
            elapsed = (now - n.detected_at).total_seconds() / 3600.0
            remaining = round(n.deadline_hours - elapsed, 2)
        item = AepdNotificationResponse.model_validate(n)
        out.append(item.model_copy(update={"deadline_hours_remaining": remaining}))
    return out
