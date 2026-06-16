"""M19 incident admin endpoints LIGHT · SAN-E v3.MB-6 atom 3.bis.

2 admin endpoints workflow management:
- POST   /admin/incidents/{id}/transition    · workflow_state advance manual
- PATCH  /admin/incidents/{id}/classify      · severidad + categorizacion

Auth: require_owner (admin Marcos). Pattern atomic m07_antivirus_admin_api atom 6.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db, set_tenant_context
from backend.app.models.auth import User
from backend.app.motors.m19_risk.incident_workflow_service import (
    IncidentAlreadyClosedError,
    IncidentNotFoundError,
    IncidentWorkflowService,
    InvalidSeverityError,
    InvalidWorkflowTransitionError,
)


router = APIRouter(
    prefix="/admin/incidents",
    tags=["Motor 19 - Incidents admin (workflow + classify)"],
    dependencies=[Depends(require_owner)],
)


# ════════════════════════════════════════════════════════════════════
# Constants
# ════════════════════════════════════════════════════════════════════

# Ejecutable 8 OLA 0 (#3): estados ALINEADOS con la máquina canónica CCN-STIC 817
# (incident_workflow_service.WORKFLOW_STATES). Antes este módulo declaraba estados
# DIVERGENTES (detected/investigating/contained): todo incidente creado por el
# servicio nacía en 'created' y quedaba ATRAPADO (409, porque 'created' no estaba
# en la máquina local). La validación de transición delega ahora en
# IncidentWorkflowService.transition_workflow_state (única fuente de verdad).
INCIDENT_STATES: tuple[str, ...] = (
    "created", "triaged", "investigated", "mitigated", "resolved", "closed",
)


# Severidades canónicas del servicio (inglés · CCN-STIC 845 las mapea en LUCIA).
SEVERIDADES: tuple[str, ...] = ("critical", "high", "medium", "low")


# El endpoint /classify acepta severidad en español (UX admin) pero el resto del
# sistema (decision tree CCN-CERT · IncidentWorkflowService · LUCIA) opera con la
# vocabulario canónico INGLÉS. Sin esta normalización, un incidente clasificado a
# 'critica' se persistía literalmente y NO casaba con _SEVERITIES_REQUIRING_ROUTING
# ({'critical','high'}) → el routing CCN-CERT podía omitir un incidente crítico.
_SEVERIDAD_ES_TO_EN: dict[str, str] = {
    "critica": "critical",
    "alta": "high",
    "media": "medium",
    "baja": "low",
}


# ════════════════════════════════════════════════════════════════════
# Schemas
# ════════════════════════════════════════════════════════════════════


class TransitionRequest(BaseModel):
    target_state: Literal[
        "triaged", "investigated", "mitigated", "resolved", "closed",
    ] = Field(..., description="Estado destino · forward-only (CCN-STIC 817)")
    note: str | None = Field(None, max_length=2000)


class TransitionResponse(BaseModel):
    incident_id: uuid.UUID
    from_state: str
    to_state: str
    transitioned_at: datetime
    admin_user_id: uuid.UUID


class ClassifyRequest(BaseModel):
    # NOTA: la tabla `incidents` NO tiene columna `tipo` (ver models/operations.py ·
    # solo severidad/descripcion/resolucion). El campo `tipo` previo del schema +
    # SQL provocaba un 500 (UndefinedColumnError) en CADA llamada al endpoint. Se
    # retira para que /classify funcione realmente (audit §2.2/226).
    severidad: Literal["baja", "media", "alta", "critica"] | None = Field(None)
    descripcion: str | None = Field(None, max_length=4000)


class ClassifyResponse(BaseModel):
    incident_id: uuid.UUID
    severidad: str | None
    admin_user_id: uuid.UUID


# ════════════════════════════════════════════════════════════════════
# Endpoints
# ════════════════════════════════════════════════════════════════════


@router.post(
    "/{incident_id}/transition",
    response_model=TransitionResponse,
)
async def transition_incident(
    incident_id: uuid.UUID,
    body: TransitionRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_owner),
) -> TransitionResponse:
    """Admin transition workflow_state · forward-only validation.

    Disparado por Marcos durante investigacion incident · pasa detected →
    investigating → contained → resolved. Cierre 'closed' es post-cliente
    firma (via incident_portal_api.process_signoff endpoint cliente).
    """
    # Estado actual (para la respuesta from_state).
    row = await db.execute(text(
        "SELECT workflow_state FROM incidents "
        "WHERE id = :iid AND deleted_at IS NULL"
    ), {"iid": str(incident_id)})
    hit = row.first()
    if hit is None:
        raise HTTPException(status_code=404, detail="Incident no encontrado")
    current_state = hit[0] or "created"

    # Validación + transición vía la máquina canónica CCN-STIC 817 (DRY · OPS-026).
    service = IncidentWorkflowService(db)
    try:
        await service.transition_workflow_state(incident_id, body.target_state)
    except IncidentNotFoundError:
        raise HTTPException(status_code=404, detail="Incident no encontrado")
    except (InvalidWorkflowTransitionError, IncidentAlreadyClosedError) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc),
        )

    transitioned_at = datetime.now(UTC)
    await db.commit()

    return TransitionResponse(
        incident_id=incident_id,
        from_state=current_state,
        to_state=body.target_state,
        transitioned_at=transitioned_at,
        admin_user_id=user.id,
    )


@router.patch(
    "/{incident_id}/classify",
    response_model=ClassifyResponse,
)
async def classify_incident(
    incident_id: uuid.UUID,
    body: ClassifyRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_owner),
) -> ClassifyResponse:
    """Admin classify incident · severidad + descripcion enriquecida.

    Pattern PATCH (NULL fields preservan valor existing). La severidad española
    de entrada se normaliza a la vocabulario canónica inglesa antes de persistir.
    """
    row = await db.execute(text(
        "SELECT id, severidad, descripcion FROM incidents "
        "WHERE id = :iid AND deleted_at IS NULL"
    ), {"iid": str(incident_id)})
    hit = row.first()
    if hit is None:
        raise HTTPException(status_code=404, detail="Incident no encontrado")

    # Normaliza la severidad española de entrada a la vocabulario canónica inglesa
    # ANTES de persistir, para que el decision tree CCN-CERT y LUCIA la reconozcan.
    if body.severidad is not None:
        new_severidad = _SEVERIDAD_ES_TO_EN.get(body.severidad, body.severidad)
    else:
        new_severidad = hit[1]
    new_descripcion = body.descripcion if body.descripcion is not None else hit[2]

    await db.execute(text(
        "UPDATE incidents SET "
        "severidad = :sev, descripcion = :desc, "
        "updated_at = now() WHERE id = :iid"
    ), {
        "sev": new_severidad,
        "desc": new_descripcion,
        "iid": str(incident_id),
    })
    await db.commit()

    return ClassifyResponse(
        incident_id=incident_id,
        severidad=new_severidad,
        admin_user_id=user.id,
    )


# ════════════════════════════════════════════════════════════════════
# #32 · Report endpoint · alta de incidente (decision tree + LUCIA + audit_log)
# ════════════════════════════════════════════════════════════════════


class ReportIncidentRequest(BaseModel):
    severidad: Literal["critical", "high", "medium", "low"] = Field(
        ..., description="Severidad canónica (CCN-STIC 845)",
    )
    descripcion: str = Field(..., min_length=1, max_length=4000)
    fecha: datetime | None = Field(
        None, description="Fecha de detección (default: ahora UTC)",
    )


class ReportIncidentResponse(BaseModel):
    incident_id: uuid.UUID
    project_id: uuid.UUID
    workflow_state: str
    severidad: str | None
    notificado_lucia: bool | None
    lucia_submission_id: uuid.UUID | None
    ccn_cert_routing: dict | None


@router.post("/{project_id}/report", response_model=ReportIncidentResponse)
async def report_incident(
    project_id: uuid.UUID,
    body: ReportIncidentRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_owner),
) -> ReportIncidentResponse:
    """Alta de incidente (Marcos admin · art. 33 RD 311/2022).

    Antes la cadena de incidentes era INALCANZABLE por API: create_incident
    (decision tree CCN-CERT + auto-notificación LUCIA/INCIBE-CERT + audit_log R6)
    existía pero NINGÚN endpoint de producción lo invocaba. Este endpoint la
    cablea: el alta nace en 'created' y, si severidad + lucia_enabled lo exigen,
    notifica automáticamente a LUCIA dejando rastro inmutable en audit_log.
    """
    # FIX(RLS): create_incident hace SELECT ... FROM projects WHERE id (RLS-filtered →
    # 404 con fulkro_app). Resolver el owner vía SECURITY DEFINER + fijar contexto
    # tenant ANTES de la primera query a tabla protegida por RLS.
    _owner = (await db.execute(
        text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)}
    )).scalar()
    if not _owner:
        raise HTTPException(status_code=404, detail="Project no encontrado")
    await set_tenant_context(db, client_id=_owner, project_id=project_id)

    service = IncidentWorkflowService(db)
    try:
        incident = await service.create_incident(
            project_id=project_id,
            severidad=body.severidad,
            descripcion=body.descripcion,
            fecha=body.fecha,
        )
    except IncidentNotFoundError:
        raise HTTPException(status_code=404, detail="Project no encontrado")
    except InvalidSeverityError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    await db.commit()

    return ReportIncidentResponse(
        incident_id=incident.id,
        project_id=incident.project_id,
        workflow_state=incident.workflow_state or "created",
        severidad=incident.severidad,
        notificado_lucia=incident.notificado_lucia,
        lucia_submission_id=incident.lucia_submission_id,
        ccn_cert_routing=incident.ccn_cert_routing_decision,
    )
