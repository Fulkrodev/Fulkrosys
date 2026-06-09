"""Motor 19 · Incidents portal cliente · SAN-E v3.MB-6 atom 3.

CCN-STIC 817 cliente review + close signoff workflow.
Cliente VE solo `resolved` + `closed` (Q4 cement).

Endpoints cliente-facing:
- GET   /portal/incidents/projects/{id}                          · list visible
- GET   /portal/incidents/{id}                                   · detail single
- POST  /portal/incidents/{id}/review                            · cliente review action
- GET   /portal/incidents/{id}/document-hash                     · SHA256 pre-firma close
- POST  /portal/incidents/{id}/finalize-close                    · link signing_intent close
"""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db, set_tenant_context
from backend.app.models.client_portal import ClientUser
from backend.app.motors.m05_signing.models import SigningIntent
from backend.app.motors.m19_risk.incident_workflow_service import (
    IncidentAlreadyClosedError,
    IncidentNotFoundError,
    IncidentWorkflowError,
    IncidentWorkflowService,
    InvalidReviewActionError,
)
from backend.app.motors.m21_portal_cliente.api import get_current_client_user


router = APIRouter(
    prefix="/portal/incidents",
    tags=["Motor 19 - Incidents cliente in-portal"],
)


# ════════════════════════════════════════════════════════════════════
# Schemas
# ════════════════════════════════════════════════════════════════════


class IncidentClientOut(BaseModel):
    """Vista cliente single incident · workflow_state IN (resolved, closed)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    fecha: datetime | None
    severidad: str | None
    descripcion: str | None
    resolucion: str | None
    workflow_state: str | None
    client_review_status: str | None
    client_review_note: str | None
    client_reviewed_at: datetime | None
    client_signing_intent_id: uuid.UUID | None
    ccn_cert_routing: dict | None
    reported_to_ccn_cert_at: datetime | None
    manual_notification_doc_id: uuid.UUID | None
    lucia_submission_id: uuid.UUID | None
    notificado_lucia: bool | None
    created_at: datetime


class IncidentReviewRequest(BaseModel):
    action: str = Field(..., description="revisada_ok / con_pregunta / suggest_change")
    note: str | None = Field(None, max_length=4000)


class IncidentDocumentHashOut(BaseModel):
    incident_id: uuid.UUID
    workflow_state: str
    canonical_length: int
    document_hash_sha256: str
    ready_for_signing: bool


class IncidentFinalizeCloseRequest(BaseModel):
    signing_intent_id: uuid.UUID


class IncidentFinalizeCloseOut(BaseModel):
    incident_id: uuid.UUID
    signing_intent_id: uuid.UUID
    workflow_state: str


# ════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════


def _service(db: AsyncSession) -> IncidentWorkflowService:
    return IncidentWorkflowService(db)


async def _ensure_project_belongs_to_client(
    db: AsyncSession, project_id: uuid.UUID, user: ClientUser,
) -> None:
    from sqlalchemy import text as sa_text
    row = await db.execute(
        sa_text("SELECT client_id FROM projects WHERE id = :pid"),
        {"pid": str(project_id)},
    )
    hit = row.first()
    if hit is None:
        raise HTTPException(status_code=404, detail="Project no existe")
    if hit[0] != user.client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Project no pertenece al cliente del usuario",
        )
    await set_tenant_context(db, client_id=user.client_id, project_id=project_id)


async def _get_incident_project(
    db: AsyncSession, incident_id: uuid.UUID,
) -> uuid.UUID:
    from sqlalchemy import text as sa_text
    row = await db.execute(
        sa_text("SELECT project_id FROM incidents WHERE id = :iid"),
        {"iid": str(incident_id)},
    )
    hit = row.first()
    if hit is None:
        raise HTTPException(status_code=404, detail="Incident no existe")
    return hit[0]


def _handle_service_error(exc: Exception) -> HTTPException:
    if isinstance(exc, IncidentNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, InvalidReviewActionError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, IncidentAlreadyClosedError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, IncidentWorkflowError):
        return HTTPException(status_code=409, detail=str(exc))
    return HTTPException(status_code=500, detail=str(exc))


def _view_to_out(view) -> IncidentClientOut:
    return IncidentClientOut(
        id=view.id,
        project_id=view.project_id,
        fecha=view.fecha,
        severidad=view.severidad,
        descripcion=view.descripcion,
        resolucion=view.resolucion,
        workflow_state=view.workflow_state,
        client_review_status=view.client_review_status,
        client_review_note=view.client_review_note,
        client_reviewed_at=view.client_reviewed_at,
        client_signing_intent_id=view.client_signing_intent_id,
        ccn_cert_routing=view.ccn_cert_routing,
        reported_to_ccn_cert_at=view.reported_to_ccn_cert_at,
        manual_notification_doc_id=view.manual_notification_doc_id,
        lucia_submission_id=view.lucia_submission_id,
        notificado_lucia=view.notificado_lucia,
        created_at=view.created_at,
    )


# ════════════════════════════════════════════════════════════════════
# Endpoints
# ════════════════════════════════════════════════════════════════════


@router.get(
    "/projects/{project_id}",
    response_model=list[IncidentClientOut],
)
async def list_client_incidents(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> list[IncidentClientOut]:
    """Lista incidents cliente-visible · workflow_state IN (resolved, closed)."""
    await _ensure_project_belongs_to_client(db, project_id, user)
    views = await _service(db).get_client_visible_incidents(project_id)
    return [_view_to_out(v) for v in views]


@router.get(
    "/{incident_id}",
    response_model=IncidentClientOut,
)
async def get_client_incident_detail(
    incident_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> IncidentClientOut:
    """Detail single incident · enforce cliente-visible state."""
    project_id = await _get_incident_project(db, incident_id)
    await _ensure_project_belongs_to_client(db, project_id, user)
    try:
        view = await _service(db).get_client_visible_incident(incident_id)
    except IncidentNotFoundError as exc:
        raise _handle_service_error(exc) from exc
    return _view_to_out(view)


@router.post(
    "/{incident_id}/review",
    response_model=IncidentClientOut,
)
async def review_incident(
    incident_id: uuid.UUID,
    body: IncidentReviewRequest,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> IncidentClientOut:
    """Cliente review action incident."""
    project_id = await _get_incident_project(db, incident_id)
    await _ensure_project_belongs_to_client(db, project_id, user)

    try:
        await _service(db).mark_client_review(
            incident_id=incident_id,
            action=body.action,
            note=body.note,
            user_id=user.id,
        )
    except (
        InvalidReviewActionError,
        IncidentNotFoundError,
        IncidentWorkflowError,
    ) as exc:
        raise _handle_service_error(exc) from exc

    await db.commit()

    view = await _service(db).get_client_visible_incident(incident_id)
    return _view_to_out(view)


@router.get(
    "/{incident_id}/document-hash",
    response_model=IncidentDocumentHashOut,
)
async def get_incident_close_hash(
    incident_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> IncidentDocumentHashOut:
    """SHA256 canonical incident_close state · pre-firma."""
    project_id = await _get_incident_project(db, incident_id)
    await _ensure_project_belongs_to_client(db, project_id, user)

    try:
        doc_hash, canonical_length = await _service(db).compute_incident_close_hash(
            incident_id,
        )
    except (IncidentNotFoundError, IncidentWorkflowError) as exc:
        raise _handle_service_error(exc) from exc

    from backend.app.models.operations import Incident
    incident = await db.get(Incident, incident_id)
    assert incident is not None
    ready = (
        incident.workflow_state == "resolved"
        and incident.client_reviewed_at is not None
    )

    return IncidentDocumentHashOut(
        incident_id=incident_id,
        workflow_state=incident.workflow_state or "",
        canonical_length=canonical_length,
        document_hash_sha256=doc_hash,
        ready_for_signing=ready,
    )


@router.post(
    "/{incident_id}/finalize-close",
    response_model=IncidentFinalizeCloseOut,
)
async def finalize_incident_close(
    incident_id: uuid.UUID,
    body: IncidentFinalizeCloseRequest,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> IncidentFinalizeCloseOut:
    """Post-firma incident_close · workflow_state → closed + link signing_intent."""
    project_id = await _get_incident_project(db, incident_id)
    await _ensure_project_belongs_to_client(db, project_id, user)

    intent = await db.get(SigningIntent, body.signing_intent_id)
    if intent is None:
        raise HTTPException(status_code=404, detail="SigningIntent no existe")
    if intent.project_id != project_id:
        raise HTTPException(
            status_code=400,
            detail="SigningIntent no pertenece al project",
        )
    if intent.signable_type != "incident_close":
        raise HTTPException(
            status_code=400,
            detail=(
                f"SigningIntent.signable_type='{intent.signable_type}' "
                f"esperado 'incident_close'"
            ),
        )
    if intent.status != "signed":
        raise HTTPException(
            status_code=409,
            detail=f"SigningIntent status='{intent.status}' · esperado 'signed'",
        )

    try:
        incident = await _service(db).process_incident_close_signoff(
            incident_id=incident_id,
            signing_intent_id=body.signing_intent_id,
        )
    except (IncidentNotFoundError, IncidentWorkflowError) as exc:
        raise _handle_service_error(exc) from exc

    await db.commit()

    return IncidentFinalizeCloseOut(
        incident_id=incident.id,
        signing_intent_id=body.signing_intent_id,
        workflow_state=incident.workflow_state or "closed",
    )
