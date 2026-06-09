"""Motor 18 - Communication & Reporting API."""
from __future__ import annotations

import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db, set_tenant_context
from backend.app.auth.dependencies import require_owner

from .escalation_service import EscalationError, EscalationService, TRIGGERS
from .minutes_service import (
    MinutesError,
    MinutesNotFoundError,
    MinutesService,
    MinutesStateError,
    MinutesValidationError,
)
from .plan_service import CommunicationPlanService, PlanError
from .report_generator import REPORT_TEMPLATES, ReportError, ReportGeneratorService


router = APIRouter(
    prefix="/communication", tags=["Motor 18 - Communication"],
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


# ─────────── Schemas ───────────

class CreatePlanBody(BaseModel):
    destinatarios: Optional[dict] = None
    frecuencias: Optional[dict] = None
    escalations: Optional[list] = None


class UpdatePlanBody(BaseModel):
    destinatarios: Optional[dict] = None
    frecuencias: Optional[dict] = None
    escalations: Optional[list] = None
    estado: Optional[str] = Field(None, max_length=20)


class GenerateReportBody(BaseModel):
    tipo: str = Field(..., min_length=2, max_length=30)
    periodo_inicio: Optional[date] = None
    periodo_fin: Optional[date] = None


class CreateEscalationBody(BaseModel):
    trigger: str = Field(..., min_length=2, max_length=100)
    descripcion: Optional[str] = None


# ─────────── Catálogo ───────────

@router.get("/report-templates")
async def list_report_templates():
    return {
        "templates": [
            {"tipo": k, **v} for k, v in REPORT_TEMPLATES.items()
        ]
    }


@router.get("/escalation-triggers")
async def list_escalation_triggers():
    return {
        "triggers": [
            {"trigger": k, **v} for k, v in TRIGGERS.items()
        ]
    }


# ─────────── Communication Plan ───────────

@router.post(
    "/projects/{project_id}/communication/plan",
    status_code=status.HTTP_201_CREATED,
)
async def create_plan(
    project_id: uuid.UUID,
    body: CreatePlanBody,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    try:
        plan = await CommunicationPlanService().create_plan(
            db, project_id=project_id,
            destinatarios=body.destinatarios,
            frecuencias=body.frecuencias,
            escalations=body.escalations,
        )
    except PlanError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return _serialize_plan(plan)


@router.get("/projects/{project_id}/communication/plan")
async def get_plan(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    plan = await CommunicationPlanService().get_plan(db, project_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return _serialize_plan(plan)


@router.patch("/projects/{project_id}/communication/plan")
async def update_plan(
    project_id: uuid.UUID,
    body: UpdatePlanBody,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    try:
        plan = await CommunicationPlanService().update_plan(
            db, project_id, body.model_dump(exclude_none=True),
        )
    except PlanError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await db.commit()
    return _serialize_plan(plan)


@router.post("/projects/{project_id}/communication/plan/activate")
async def activate_plan(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    try:
        plan = await CommunicationPlanService().activate_plan(db, project_id)
    except PlanError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await db.commit()
    return _serialize_plan(plan)


# ─────────── Reports ───────────

@router.post(
    "/projects/{project_id}/communication/reports/generate",
    status_code=status.HTTP_201_CREATED,
)
async def generate_report(
    project_id: uuid.UUID,
    body: GenerateReportBody,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    try:
        report = await ReportGeneratorService().generate_report(
            db, project_id=project_id, tipo=body.tipo,
            periodo_inicio=body.periodo_inicio, periodo_fin=body.periodo_fin,
        )
    except ReportError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return _serialize_report(report)


@router.get("/projects/{project_id}/communication/reports")
async def list_reports(
    project_id: uuid.UUID,
    tipo: Optional[str] = None,
    estado: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    reports = await ReportGeneratorService().list_reports(
        db, project_id=project_id, tipo=tipo, estado=estado,
    )
    return {"reports": [_serialize_report(r) for r in reports]}


@router.get("/projects/{project_id}/communication/reports/{report_id}")
async def get_report(
    project_id: uuid.UUID,
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    r = await ReportGeneratorService().get_report(db, report_id)
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")
    return _serialize_report(r)


@router.get("/projects/{project_id}/communication/reports/{report_id}/docx")
async def download_docx(
    project_id: uuid.UUID,
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    try:
        content = await ReportGeneratorService().generate_docx(db, report_id)
    except ReportError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="report_{report_id}.docx"'
        },
    )


@router.post("/projects/{project_id}/communication/reports/{report_id}/review")
async def mark_review(
    project_id: uuid.UUID,
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    try:
        r = await ReportGeneratorService().mark_reviewed(db, report_id)
    except ReportError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return _serialize_report(r)


@router.post("/projects/{project_id}/communication/reports/{report_id}/send")
async def mark_send(
    project_id: uuid.UUID,
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    try:
        r = await ReportGeneratorService().mark_sent(db, report_id)
    except ReportError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return _serialize_report(r)


# ─────────── Escalations ───────────

@router.post(
    "/projects/{project_id}/communication/escalations",
    status_code=status.HTTP_201_CREATED,
)
async def create_escalation(
    project_id: uuid.UUID,
    body: CreateEscalationBody,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    try:
        event = await EscalationService().create_escalation(
            db, project_id=project_id,
            trigger=body.trigger, descripcion=body.descripcion,
        )
    except EscalationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return _serialize_escalation(event)


@router.get("/projects/{project_id}/communication/escalations")
async def list_escalations(
    project_id: uuid.UUID,
    resuelto: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    events = await EscalationService().list_escalations(
        db, project_id=project_id, resuelto=resuelto,
    )
    return {"escalations": [_serialize_escalation(e) for e in events]}


@router.post("/projects/{project_id}/communication/escalations/{event_id}/resolve")
async def resolve_escalation(
    project_id: uuid.UUID,
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    try:
        event = await EscalationService().resolve_escalation(db, event_id)
    except EscalationError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await db.commit()
    return _serialize_escalation(event)


@router.get("/projects/{project_id}/communication/escalations/active-count")
async def active_count(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    return {"active_count": await EscalationService().get_active_count(db, project_id)}


# ─────────── Serializers ───────────

def _serialize_plan(p):
    return {
        "id": str(p.id),
        "project_id": str(p.project_id),
        "destinatarios": p.destinatarios,
        "frecuencias": p.frecuencias,
        "escalations": p.escalations,
        "estado": p.estado,
        "activado_at": p.activado_at.isoformat() if p.activado_at else None,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


def _serialize_report(r):
    return {
        "id": str(r.id),
        "project_id": str(r.project_id),
        "tipo": r.tipo,
        "destinatario_rol": r.destinatario_rol,
        "periodo_inicio": r.periodo_inicio.isoformat() if r.periodo_inicio else None,
        "periodo_fin": r.periodo_fin.isoformat() if r.periodo_fin else None,
        "contenido_jsonb": r.contenido_jsonb,
        "semaforo_rag": r.semaforo_rag,
        "docx_path": r.docx_path,
        "pdf_path": r.pdf_path,
        "estado": r.estado,
        "generado_at": r.generado_at.isoformat() if r.generado_at else None,
        "revisado_at": r.revisado_at.isoformat() if r.revisado_at else None,
        "enviado_at": r.enviado_at.isoformat() if r.enviado_at else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


def _serialize_escalation(e):
    return {
        "id": str(e.id),
        "project_id": str(e.project_id),
        "trigger": e.trigger,
        "descripcion": e.descripcion,
        "notificados": e.notificados,
        "canal": e.canal,
        "resuelto": e.resuelto,
        "resuelto_at": e.resuelto_at.isoformat() if e.resuelto_at else None,
        "feed_item_id": str(e.feed_item_id) if e.feed_item_id else None,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


# ─────────── Acta de Comite (E-005 — Sesion 6) ───────────

class CreateMinutesBody(BaseModel):
    tipo_comite: str = Field(..., description="kickoff | seguimiento_trimestral | cierre | extraordinario")
    titulo: str = Field(..., min_length=2, max_length=300)
    fecha: date
    presidente: str = Field(..., min_length=2, max_length=200)
    secretario: str = Field(..., min_length=2, max_length=200)
    asistentes: list[dict] = Field(..., min_length=1, description="[{nombre, cargo, organizacion, email}]")
    orden_del_dia: list[dict] | None = None
    acuerdos: list[dict] | None = None
    proximos_pasos: list[dict] | None = None
    lugar: str | None = Field(None, max_length=300)
    notas_libres: str | None = None


class GenerateMinutesDocxBody(BaseModel):
    cliente_razon: str = Field(..., min_length=2, max_length=300)
    version_actual: str = Field("1.0", max_length=20)


class SendForSignatureBody(BaseModel):
    cliente_razon: str = Field(..., min_length=2, max_length=300)
    base_url: str = Field("https://app.fulkro.es", max_length=300)


class RegisterSignatureBody(BaseModel):
    magic_link_id: uuid.UUID
    action_proof: str | None = Field(None, max_length=1000)


def _serialize_minutes(m) -> dict:
    return {
        "id": str(m.id),
        "project_id": str(m.project_id),
        "codigo": m.codigo,
        "tipo_comite": m.tipo_comite,
        "titulo": m.titulo,
        "fecha": m.fecha.isoformat() if m.fecha and hasattr(m.fecha, "isoformat") else (m.fecha or None),
        "lugar": m.lugar,
        "presidente": m.presidente,
        "secretario": m.secretario,
        "asistentes": m.asistentes,
        "orden_del_dia": m.orden_del_dia,
        "acuerdos": m.acuerdos_jsonb,
        "proximos_pasos": m.proximos_pasos,
        "notas_libres": m.notas_libres,
        "estado": m.estado,
        "docx_path": m.docx_path,
        "pdf_path": m.pdf_path,
        "hash_sha256": m.hash_sha256,
        "signature_ed25519": m.signature_ed25519,
        "firmas": m.firmas,
        "generado_at": m.generado_at.isoformat() if m.generado_at else None,
        "enviada_at": m.enviada_at.isoformat() if m.enviada_at else None,
        "fully_signed_at": m.fully_signed_at.isoformat() if m.fully_signed_at else None,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


@router.post(
    "/projects/{project_id}/minutes",
    status_code=status.HTTP_201_CREATED,
)
async def create_minutes(
    project_id: uuid.UUID,
    body: CreateMinutesBody,
    db: AsyncSession = Depends(get_db),
):
    """Crea una nueva acta de comite (E-005) en estado draft."""
    await _set_project_rls(project_id, db)
    try:
        m = await MinutesService(db).create(
            project_id=project_id,
            tipo_comite=body.tipo_comite,
            titulo=body.titulo,
            fecha=body.fecha,
            presidente=body.presidente,
            secretario=body.secretario,
            asistentes=body.asistentes,
            orden_del_dia=body.orden_del_dia,
            acuerdos=body.acuerdos,
            proximos_pasos=body.proximos_pasos,
            lugar=body.lugar,
            notas_libres=body.notas_libres,
        )
    except MinutesValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    await db.commit()
    return _serialize_minutes(m)


@router.get("/projects/{project_id}/minutes")
async def list_minutes(
    project_id: uuid.UUID,
    estado: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    items = await MinutesService(db).list_by_project(project_id, estado=estado)
    return {"minutes": [_serialize_minutes(m) for m in items]}


@router.get("/minutes/{minutes_id}")
async def get_minutes(
    minutes_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    # RLS via project_id lookup
    row = (await db.execute(
        text("SELECT project_id FROM committee_meetings WHERE id = :mid AND deleted_at IS NULL"),
        {"mid": str(minutes_id)},
    )).first()
    if not row:
        raise HTTPException(status_code=404, detail="Acta no encontrada")
    await _set_project_rls(row[0], db)
    try:
        m = await MinutesService(db).get(minutes_id)
    except MinutesNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _serialize_minutes(m)


@router.post("/minutes/{minutes_id}/generate-docx")
async def generate_minutes_docx(
    minutes_id: uuid.UUID,
    body: GenerateMinutesDocxBody,
    db: AsyncSession = Depends(get_db),
):
    row = (await db.execute(
        text("SELECT project_id FROM committee_meetings WHERE id = :mid AND deleted_at IS NULL"),
        {"mid": str(minutes_id)},
    )).first()
    if not row:
        raise HTTPException(status_code=404, detail="Acta no encontrada")
    await _set_project_rls(row[0], db)
    try:
        m = await MinutesService(db).generate_docx(
            minutes_id, body.cliente_razon, body.version_actual,
        )
    except MinutesError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return _serialize_minutes(m)


@router.post("/minutes/{minutes_id}/send-for-signature")
async def send_minutes_for_signature(
    minutes_id: uuid.UUID,
    body: SendForSignatureBody,
    db: AsyncSession = Depends(get_db),
):
    row = (await db.execute(
        text("SELECT project_id FROM committee_meetings WHERE id = :mid AND deleted_at IS NULL"),
        {"mid": str(minutes_id)},
    )).first()
    if not row:
        raise HTTPException(status_code=404, detail="Acta no encontrada")
    await _set_project_rls(row[0], db)
    try:
        result = await MinutesService(db).send_for_signature(
            minutes_id, body.cliente_razon, body.base_url,
        )
    except MinutesStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except MinutesError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return result


@router.post("/minutes/{minutes_id}/sign")
async def register_minutes_signature(
    minutes_id: uuid.UUID,
    body: RegisterSignatureBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    row = (await db.execute(
        text("SELECT project_id FROM committee_meetings WHERE id = :mid AND deleted_at IS NULL"),
        {"mid": str(minutes_id)},
    )).first()
    if not row:
        raise HTTPException(status_code=404, detail="Acta no encontrada")
    await _set_project_rls(row[0], db)
    try:
        client_ip = request.client.host if request.client else None
        m = await MinutesService(db).register_signature(
            minutes_id,
            magic_link_id=body.magic_link_id,
            ip=client_ip,
            action_proof=body.action_proof,
        )
    except MinutesStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except MinutesValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except MinutesError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return _serialize_minutes(m)


@router.get("/minutes/{minutes_id}/signing-status")
async def get_minutes_signing_status(
    minutes_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    row = (await db.execute(
        text("SELECT project_id FROM committee_meetings WHERE id = :mid AND deleted_at IS NULL"),
        {"mid": str(minutes_id)},
    )).first()
    if not row:
        raise HTTPException(status_code=404, detail="Acta no encontrada")
    await _set_project_rls(row[0], db)
    try:
        return await MinutesService(db).get_signing_status(minutes_id)
    except MinutesNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
