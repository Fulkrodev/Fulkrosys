"""Motor 13 - Commercial API.

Propuestas + catálogo pricing models.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db, set_tenant_context
from backend.app.auth.dependencies import require_owner

from .pricing_service import PricingModelNotFoundError, PricingService
from .proposal_service import ProposalError, ProposalService


router = APIRouter(
    prefix="/commercial", tags=["Motor 13 - Commercial"],
    # TODO-RBAC-PER-ENDPOINT-001 Cat A: Marcos-only.
    dependencies=[Depends(require_owner)],
)


async def _set_project_rls(project_id: uuid.UUID, db: AsyncSession):
    client_id = (await db.execute(
        text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)}
    )).scalar()
    if not client_id:
        raise HTTPException(status_code=404, detail="Project not found")
    await set_tenant_context(db, client_id=client_id, project_id=project_id)


# ---------------------- Schemas ----------------------

class GenerateProposalBody(BaseModel):
    lead_id: uuid.UUID
    pricing_model_id: str = Field(..., min_length=1, max_length=50)
    categoria: str = Field(..., min_length=1, max_length=10)
    empleados: int = Field(0, ge=0)
    sistemas: int = Field(0, ge=0)
    ubicaciones: int = Field(1, ge=1)
    sector_regulado: bool = False
    cpds: int = Field(0, ge=0)
    client_size: str = Field("mediana", max_length=20)
    complexity: str = Field("media", max_length=20)
    importe_override: Optional[float] = Field(None, ge=0)
    duracion_semanas_override: Optional[int] = Field(None, ge=1, le=200)
    notas_marcos: Optional[str] = None
    validez_dias: int = Field(30, ge=1, le=180)


class UpdateStatusBody(BaseModel):
    estado: str = Field(..., min_length=1, max_length=50)


class CreateVersionBody(BaseModel):
    alcance: Optional[dict] = None
    importe_total: Optional[float] = None
    duracion_semanas: Optional[int] = None
    hitos_pago: Optional[dict] = None
    notas_marcos: Optional[str] = None


class CalculatePriceBody(BaseModel):
    empleados: int = Field(0, ge=0)
    sistemas: int = Field(0, ge=0)
    ubicaciones: int = Field(1, ge=1)
    sector_regulado: bool = False
    cpds: int = Field(0, ge=0)
    meses_retainer: int = Field(1, ge=1, le=60)
    pentest_continuo: bool = False
    iva_percent: float = Field(21.0, ge=0, le=100)


class GenerateLLMBody(BaseModel):
    lead_id: uuid.UUID
    categoria: str = Field(..., min_length=1, max_length=10)
    sector: Optional[str] = Field(None, max_length=64)
    sistemas_en_alcance: int = Field(1, ge=1, le=500)
    sedes: int = Field(1, ge=1, le=500)
    madurez_pct: Optional[int] = Field(None, ge=0, le=100)
    dias_hasta_plazo: Optional[int] = Field(None, ge=1, le=720)
    retainer_tier: Optional[str] = Field(None, max_length=16)
    use_llm: bool = True
    regenerate: bool = False
    notas_marcos: Optional[str] = None
    validez_dias: int = Field(30, ge=1, le=180)


# ---------------------- Endpoints pricing (sin RLS) ----------------------

@router.get("/pricing-models")
async def list_pricing_models(categoria: Optional[str] = None):
    svc = PricingService()
    if categoria:
        return {"models": svc.get_models_for_categoria(categoria)}
    return {"models": svc.list_all()}


@router.get("/pricing-models/{model_id}")
async def get_pricing_model(model_id: str):
    try:
        return PricingService().get_model(model_id)
    except PricingModelNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/pricing-models/{model_id}/calculate")
async def calculate_price(model_id: str, body: CalculatePriceBody):
    try:
        return PricingService().calculate_price(
            model_id=model_id,
            empleados=body.empleados,
            sistemas=body.sistemas,
            ubicaciones=body.ubicaciones,
            sector_regulado=body.sector_regulado,
            cpds=body.cpds,
            meses_retainer=body.meses_retainer,
            pentest_continuo=body.pentest_continuo,
            iva_percent=body.iva_percent,
        )
    except PricingModelNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ---------------------- Endpoints proposals ----------------------

@router.post("/projects/{project_id}/proposals/generate", status_code=status.HTTP_201_CREATED)
async def generate_proposal(
    project_id: uuid.UUID,
    body: GenerateProposalBody,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    try:
        p = await ProposalService().generate_proposal(
            db,
            lead_id=body.lead_id,
            pricing_model_id=body.pricing_model_id,
            categoria=body.categoria,
            project_id=project_id,
            empleados=body.empleados,
            sistemas=body.sistemas,
            ubicaciones=body.ubicaciones,
            sector_regulado=body.sector_regulado,
            cpds=body.cpds,
            client_size=body.client_size,
            complexity=body.complexity,
            importe_override=body.importe_override,
            duracion_semanas_override=body.duracion_semanas_override,
            notas_marcos=body.notas_marcos,
            validez_dias=body.validez_dias,
        )
    except PricingModelNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return _serialize(p)


@router.get("/projects/{project_id}/proposals")
async def list_proposals(
    project_id: uuid.UUID,
    lead_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    rows = await ProposalService().list_proposals(db, project_id=project_id, lead_id=lead_id)
    return {"proposals": [_serialize(r) for r in rows]}


@router.get("/projects/{project_id}/proposals/{proposal_id}")
async def get_proposal(
    project_id: uuid.UUID,
    proposal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    p = await ProposalService().get_proposal(db, proposal_id)
    if not p:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return _serialize(p)


@router.patch("/projects/{project_id}/proposals/{proposal_id}")
async def update_status(
    project_id: uuid.UUID,
    proposal_id: uuid.UUID,
    body: UpdateStatusBody,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    try:
        p = await ProposalService().update_status(db, proposal_id, body.estado)
    except ProposalError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return _serialize(p)


@router.post("/projects/{project_id}/proposals/{proposal_id}/send")
async def send_proposal(
    project_id: uuid.UUID,
    proposal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    try:
        p = await ProposalService().send_proposal(db, proposal_id)
    except ProposalError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return _serialize(p)


@router.post("/projects/{project_id}/proposals/{proposal_id}/version")
async def create_version(
    project_id: uuid.UUID,
    proposal_id: uuid.UUID,
    body: CreateVersionBody,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    try:
        p = await ProposalService().create_version(
            db, proposal_id, body.model_dump(exclude_none=True)
        )
    except ProposalError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return _serialize(p)


@router.post(
    "/projects/{project_id}/proposals/generate-llm",
    status_code=status.HTTP_201_CREATED,
)
async def generate_proposal_llm(
    project_id: uuid.UUID,
    body: GenerateLLMBody,
    db: AsyncSession = Depends(get_db),
):
    """Genera P-001 con narrativa LLM (Agente 19 Opus 4.7) si use_llm=true.

    - Crea una Proposal nueva via ``generate_proposal_apendice_m`` con el
      pricing deterministico Apendice M v2.2.
    - Si ``use_llm=true``, invoca al Agente 19 para rellenar las 10 secciones
      narrativas. El agente valida que no haya numeros alucinados (max 2
      reintentos), y si no encuentra texto valido cae a fallback determinista.
    - Si ``use_llm=false``, solo crea la Proposal sin narrativa LLM.

    ``regenerate=true`` fuerza una nueva generacion incluso si ya existe una
    propuesta draft para el proyecto (crea una nueva version en lugar de
    reutilizar la anterior).
    """
    await _set_project_rls(project_id, db)

    # Si regenerate=false y ya hay una draft, la reutilizamos
    existing = None
    if not body.regenerate:
        existing_rows = await ProposalService().list_proposals(
            db, project_id=project_id
        )
        for row in existing_rows:
            if row.estado == "draft" and row.categoria_objetivo == body.categoria.upper():
                existing = row
                break

    if existing is not None and not body.regenerate:
        return {
            "proposal": _serialize(existing),
            "narrative_mode": (
                "llm-cached"
                if (existing.importe_desglose or {}).get("llm_narrative")
                else "deterministic-cached"
            ),
            "agent_19_result": (existing.importe_desglose or {}).get("llm_narrative"),
        }

    narrative_mode = "llm" if body.use_llm else "deterministic"
    try:
        proposal = await ProposalService().generate_proposal_apendice_m(
            db,
            lead_id=body.lead_id,
            categoria=body.categoria,
            sector=body.sector,
            sistemas_en_alcance=body.sistemas_en_alcance,
            sedes=body.sedes,
            madurez_pct=body.madurez_pct,
            dias_hasta_plazo=body.dias_hasta_plazo,
            project_id=project_id,
            notas_marcos=body.notas_marcos,
            validez_dias=body.validez_dias,
            narrative_mode=narrative_mode,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Error generando propuesta: {exc}")
    await db.commit()
    return {
        "proposal": _serialize(proposal),
        "narrative_mode": narrative_mode,
        "agent_19_result": (proposal.importe_desglose or {}).get("llm_narrative"),
    }


@router.get("/projects/{project_id}/proposals/{proposal_id}/docx")
async def download_docx(
    project_id: uuid.UUID,
    proposal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    try:
        content = await ProposalService().generate_docx(db, proposal_id)
    except ProposalError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="propuesta_{proposal_id}.docx"'
        },
    )


# ---------------------- Helpers ----------------------

def _serialize(p):
    return {
        "id": str(p.id),
        "lead_id": str(p.lead_id),
        "project_id": str(p.project_id) if p.project_id else None,
        "version": p.version,
        "pricing_model_id": p.pricing_model_id,
        "categoria_objetivo": p.categoria_objetivo,
        "alcance": p.alcance,
        "duracion_semanas": p.duracion_semanas,
        "effort_marcos_horas": p.effort_marcos_horas,
        "importe_total": float(p.importe_total) if p.importe_total is not None else None,
        "importe_desglose": p.importe_desglose,
        "hitos_pago": p.hitos_pago,
        "validez_hasta": p.validez_hasta.isoformat() if p.validez_hasta else None,
        "estado": p.estado,
        "enviado_at": p.enviado_at.isoformat() if p.enviado_at else None,
        "notas_marcos": p.notas_marcos,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


# ══════════════════════════════════════════════════════════════════
# SAN-D MB-19.5 · CRM Lead pipeline endpoints (ADR-041)
# ══════════════════════════════════════════════════════════════════

# Mapping bidireccional estado_contacto backend (espanol hispano v2 FASE 8.5
# C2) ↔ frontend stage (ingles UI compat existing PipelineKanban).
#
# Espanol → Inglés (GET response): split semantico
#   nuevo               → new
#   enviado             → qualifying
#   respondio           → qualifying    (split bucket · Marcos puede
#                                        diferenciar via notas)
#   reunion_agendada    → meeting_exploratory
#   propuesta_enviada   → proposal_sent
#   ganado              → won
#   descartado          → lost
#   no_interesa         → lost          (split bucket · razon_perdida
#                                        diferencia)
#
# Inglés → Espanol (PATCH request): default per stage
#   new                 → nuevo
#   qualifying          → enviado       (default · transition manual)
#   meeting_exploratory → reunion_agendada
#   proposal_sent       → propuesta_enviada
#   negotiation         → propuesta_enviada (back-and-forth · backend NO
#                                        tiene estado distinto)
#   won                 → ganado
#   lost                → descartado    (default · razon_perdida vacio)
#   paused              → enviado       (placeholder · Marcos puede
#                                        re-clasificar luego)

ESTADO_CONTACTO_TO_STAGE = {
    "nuevo": "new",
    "enviado": "qualifying",
    "respondio": "qualifying",
    "reunion_agendada": "meeting_exploratory",
    "propuesta_enviada": "proposal_sent",
    "ganado": "won",
    "descartado": "lost",
    "no_interesa": "lost",
}

STAGE_TO_ESTADO_CONTACTO = {
    "new": "nuevo",
    "qualifying": "enviado",
    "meeting_exploratory": "reunion_agendada",
    "proposal_sent": "propuesta_enviada",
    "negotiation": "propuesta_enviada",
    "won": "ganado",
    "lost": "descartado",
    "paused": "enviado",
}


def _serialize_lead_for_crm(lead) -> dict:
    """Serialize Lead M13 a formato compatible PipelineKanban frontend."""
    estado_contacto = lead.estado_contacto or "nuevo"
    return {
        "id": str(lead.id),
        # Frontend campos UI (mapping espanol → ingles UI legacy compat)
        "empresa": lead.empresa_nombre,
        "cif": lead.empresa_cif,
        "sector": lead.sector,
        "score": float(lead.lead_score) if lead.lead_score is not None else 50,
        "rag": (
            "green" if (lead.lead_score or 0) >= 70
            else "amber" if (lead.lead_score or 0) >= 40
            else "red"
        ),
        "value_eur": 0,  # Se calcula desde Proposal active si existe
        "stage": ESTADO_CONTACTO_TO_STAGE.get(estado_contacto, "new"),
        "contact_name": lead.notas[:80] if lead.notas else None,
        "contact_email": lead.contacto_email,
        "contact_phone": lead.contacto_telefono,
        "source": lead.origen,
        "pliego_attached": False,
        "last_touched_at": (
            lead.fecha_ultima_actualizacion.isoformat()
            if lead.fecha_ultima_actualizacion
            else (
                lead.created_at.isoformat()
                if lead.created_at else ""
            )
        ),
        "lost_reason": lead.razon_perdida,
        "notes": lead.notas,
        # Campos backend espanol hispano expuestos para UI avanzada
        "estado_contacto": estado_contacto,
        "temperature_level": lead.temperature_level,
        "categoria_objetivo_ens": lead.categoria_objetivo_ens,
        "archetype_ens": lead.archetype_ens,
        "fecha_perdida": (
            lead.fecha_perdida.isoformat() if lead.fecha_perdida else None
        ),
        "fecha_conversion": (
            lead.fecha_conversion.isoformat()
            if lead.fecha_conversion else None
        ),
        "convertido_a_proyecto_id": (
            str(lead.convertido_a_proyecto_id)
            if lead.convertido_a_proyecto_id else None
        ),
        "primer_contacto_at": (
            lead.primer_contacto_at.isoformat()
            if lead.primer_contacto_at else None
        ),
    }


class LeadListResponse(BaseModel):
    items: list[dict]
    total: int


class UpdateLeadStageBody(BaseModel):
    stage: str = Field(..., min_length=1, max_length=50)
    notes: Optional[str] = None


class UpdateLeadEstadoContactoBody(BaseModel):
    """Update directo en español hispano (admin avanzado · UI futura)."""
    estado_contacto: str = Field(..., min_length=1, max_length=50)
    notes: Optional[str] = None


@router.get("/leads")
async def list_leads_pipeline(
    estado_contacto: Optional[str] = None,
    origen: Optional[str] = None,
    asignado_a: Optional[str] = None,
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
):
    """List leads pipeline · campos en formato compat PipelineKanban frontend.

    Query params:
    - estado_contacto: filter por estado_contacto español (nuevo · enviado
      · respondio · reunion_agendada · propuesta_enviada · ganado ·
      descartado · no_interesa).
    - origen: filter por origen (manual · referral · etc).
    - asignado_a: filter por asignado_a string.
    - limit: max items (default 200).

    Returns:
        {"items": list[LeadCRM], "total": int}
    """
    from backend.app.motors.m13_commercial.services.lead_service import (
        LeadService,
    )
    service = LeadService(db)
    leads = await service.list_pipeline(
        estado_contacto=estado_contacto,
        origen=origen,
        asignado_a=asignado_a,
        limit=limit,
    )
    items = [_serialize_lead_for_crm(l) for l in leads]
    return {"items": items, "total": len(items)}


@router.patch("/leads/{lead_id}/stage")
async def update_lead_stage(
    lead_id: uuid.UUID,
    body: UpdateLeadStageBody,
    db: AsyncSession = Depends(get_db),
):
    """Update lead stage frontend (mapping inverso → estado_contacto backend).

    Frontend stage values: new · qualifying · meeting_exploratory ·
    proposal_sent · negotiation · won · lost · paused.

    Mapping aplicado en STAGE_TO_ESTADO_CONTACTO. Si transition no es válida
    vía VALID_TRANSITIONS, retorna 400 con mensaje claro Marcos UI.
    """
    from backend.app.motors.m13_commercial.services.lead_service import (
        LeadService,
        InvalidTransitionError,
        LeadNotFoundError,
    )

    target_estado = STAGE_TO_ESTADO_CONTACTO.get(body.stage)
    if not target_estado:
        raise HTTPException(
            status_code=400,
            detail=(
                f"stage inválido: {body.stage!r} · "
                f"valid: {sorted(STAGE_TO_ESTADO_CONTACTO.keys())}"
            ),
        )

    service = LeadService(db)
    try:
        lead = await service.transition_estado_contacto(
            lead_id=lead_id,
            target_estado=target_estado,
            notes=body.notes,
            metadata={"event": "ui_kanban_drag", "frontend_stage": body.stage},
        )
    except LeadNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Lead {lead_id} no encontrado",
        )
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # FIX(commit): get_db NO auto-commitea y transition_estado_contacto solo hace
    # flush() → sin esto el cambio de estado_contacto y la fila lead_stage_history
    # se revierten al cerrar la sesión (el Kanban "avanza" en la UI optimista pero
    # revierte al recargar). Espejo de los endpoints de propuestas (161/201/...).
    await db.commit()
    return _serialize_lead_for_crm(lead)


@router.get("/leads/{lead_id}")
async def get_lead_detail(
    lead_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """SAN-D MB-19.16 cosecha B · DEC-MB19A-LEAD-DETAIL-PAGE.

    Retorna detalle completo de un lead para LeadDetailPage frontend
    /admin/pipeline/leads/[id]:

    - lead: serialized completo (campos base + extension MB-19.1)
    - stage_history: lista LeadStageHistory ordenada created_at DESC
      (audit trail transiciones · MB-19.1 lead_stage_history table)
    - proposals: revisiones del lead ordered version DESC (MB-19.3)
    - contract: contract activo si existe (firmado_cliente_at populated)

    Refs: ADR-041 · DEC-MB19A-LEAD-DETAIL-PAGE asignado MB-19.C.
    """
    from backend.app.models.commercial import (
        Contract,
        Lead,
        LeadStageHistory,
        Proposal,
    )
    from sqlalchemy import select as _select

    lead = await db.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(
            status_code=404, detail=f"Lead {lead_id} no encontrado",
        )

    # Stage history audit trail
    stage_history_rows = list((await db.scalars(
        _select(LeadStageHistory)
        .where(LeadStageHistory.lead_id == lead_id)
        .order_by(LeadStageHistory.created_at.desc())
    )).all())

    # Proposals revisions ordered version DESC
    proposals_rows = list((await db.scalars(
        _select(Proposal)
        .where(Proposal.lead_id == lead_id)
        .order_by(Proposal.version.desc())
    )).all())

    # Contract activo asociado al lead (lead_id FK · primer match)
    contract = (await db.scalars(
        _select(Contract)
        .where(Contract.lead_id == lead_id)
        .order_by(Contract.created_at.desc())
        .limit(1)
    )).first()

    return {
        "lead": _serialize_lead_for_crm(lead),
        "stage_history": [
            {
                "id": str(h.id),
                "estado_anterior": h.estado_anterior,
                "estado_nuevo": h.estado_nuevo,
                "cambiado_por_user_id": (
                    str(h.cambiado_por_user_id)
                    if h.cambiado_por_user_id else None
                ),
                "notas": h.notas,
                "metadata": h.metadata_jsonb or {},
                "created_at": (
                    h.created_at.isoformat() if h.created_at else None
                ),
            }
            for h in stage_history_rows
        ],
        "proposals": [
            {
                "id": str(p.id),
                "version": p.version,
                "estado": p.estado,
                "categoria_objetivo": p.categoria_objetivo,
                "importe_total": (
                    float(p.importe_total)
                    if p.importe_total is not None else None
                ),
                "duracion_semanas": p.duracion_semanas,
                "validez_hasta": (
                    p.validez_hasta.isoformat()
                    if p.validez_hasta else None
                ),
                "enviado_at": (
                    p.enviado_at.isoformat() if p.enviado_at else None
                ),
                "fecha_aceptacion": (
                    p.fecha_aceptacion.isoformat()
                    if p.fecha_aceptacion else None
                ),
                "superseded": bool(p.superseded),
                "feedback_cliente": p.feedback_cliente,
                "cambios_desde_anterior": p.cambios_desde_anterior,
                "notas_marcos": p.notas_marcos,
                "created_at": (
                    p.created_at.isoformat() if p.created_at else None
                ),
            }
            for p in proposals_rows
        ],
        "contract": (
            {
                "id": str(contract.id),
                "estado": contract.estado,
                "tipo": contract.tipo,
                "cliente_firmante_nombre": contract.cliente_firmante_nombre,
                "firmado_marcos_at": (
                    contract.firmado_marcos_at.isoformat()
                    if contract.firmado_marcos_at else None
                ),
                "firmado_cliente_at": (
                    contract.firmado_cliente_at.isoformat()
                    if contract.firmado_cliente_at else None
                ),
                "vigente_desde": (
                    contract.vigente_desde.isoformat()
                    if contract.vigente_desde else None
                ),
                "vigente_hasta": (
                    contract.vigente_hasta.isoformat()
                    if contract.vigente_hasta else None
                ),
                "firmado_cliente_link_id": (
                    str(contract.firmado_cliente_link_id)
                    if contract.firmado_cliente_link_id else None
                ),
                "created_at": (
                    contract.created_at.isoformat()
                    if contract.created_at else None
                ),
            }
            if contract else None
        ),
    }


@router.patch("/leads/{lead_id}/estado-contacto")
async def update_lead_estado_contacto(
    lead_id: uuid.UUID,
    body: UpdateLeadEstadoContactoBody,
    db: AsyncSession = Depends(get_db),
):
    """Update lead estado_contacto directo backend (UI avanzada española).

    Endpoint paralelo a /leads/{id}/stage para clientes API que prefieren
    convención backend español hispano spec v2.1 sin mapping intermedio.
    """
    from backend.app.motors.m13_commercial.services.lead_service import (
        LeadService,
        InvalidTransitionError,
        LeadNotFoundError,
        VALID_TRANSITIONS,
    )

    if body.estado_contacto not in VALID_TRANSITIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"estado_contacto inválido: {body.estado_contacto!r} · "
                f"valid: {sorted(VALID_TRANSITIONS.keys())}"
            ),
        )

    service = LeadService(db)
    try:
        lead = await service.transition_estado_contacto(
            lead_id=lead_id,
            target_estado=body.estado_contacto,
            notes=body.notes,
            metadata={"event": "api_direct_transition"},
        )
    except LeadNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Lead {lead_id} no encontrado",
        )
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # FIX(commit): gemelo español de update_lead_stage · misma omisión de commit.
    await db.commit()
    return _serialize_lead_for_crm(lead)
