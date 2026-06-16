"""Motor 23 - Retainer Management API."""
from __future__ import annotations

import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db, set_tenant_context
from backend.app.auth.dependencies import require_owner
from backend.app.motors.m23_retainer.report_renderer import (
    render_annual_report_docx,
    render_quarterly_report_docx,
)

from .retainer_service import (
    CADENCES_BY_PROFILE,
    HOURS_BY_PROFILE,
    SLA_BY_PROFILE,
    VALID_PROFILES,
    DRIFT_DIMENSIONS,
    DRIFT_IMPACTS,
    DRIFT_SEVERITIES,
    RetainerError,
    RetainerService,
)


router = APIRouter(
    prefix="/retainer", tags=["Motor 23 - Retainer"],
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


async def _set_rls_for_retainer(retainer_id: uuid.UUID, db: AsyncSession):
    """FIX(RLS): los endpoints retainer_id-scoped (descarga DOCX) reciben
    retainer_id sin project_id. Resolver client_id/project_id del contrato
    (cruzando RLS vía bypass admin acotado) + fijar tenant context, si no
    _fetch_retainer_with_client devuelve None → ValueError → 404 en prod."""
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    try:
        row = (await db.execute(
            text(
                "SELECT client_id, project_id FROM retainer_contracts "
                "WHERE id = :rid"
            ),
            {"rid": str(retainer_id)},
        )).first()
    finally:
        await db.execute(text("RESET ROLE"))
    if row is None:
        raise HTTPException(status_code=404, detail="Retainer not found")
    await set_tenant_context(db, client_id=row[0], project_id=row[1])


# ─────────── Schemas ───────────

class CreateRetainerBody(BaseModel):
    client_id: uuid.UUID
    perfil: str = Field("R_STD", min_length=5, max_length=20)
    precio_mensual: float = Field(..., ge=0)
    inicio: date
    fin: Optional[date] = None
    contract_id: Optional[uuid.UUID] = None
    next_renewal_date: Optional[date] = None
    modalidad: str = Field("mensual", max_length=20)


class UpdateRetainerBody(BaseModel):
    perfil: Optional[str] = Field(None, max_length=20)
    precio_mensual: Optional[float] = Field(None, ge=0)
    fin: Optional[date] = None
    renovacion_automatica: Optional[bool] = None
    estado: Optional[str] = Field(None, max_length=20)


class GenerateActivitiesBody(BaseModel):
    year: int = Field(..., ge=2024, le=2100)


class CompleteActivityBody(BaseModel):
    horas_consumidas: float = Field(..., ge=0)
    resultado: Optional[str] = None


class RenewBody(BaseModel):
    new_renewal_date: date


class RegisterDriftBody(BaseModel):
    dimension: str = Field(..., min_length=2, max_length=30)
    descripcion: str = Field(..., min_length=2)
    severidad: str = Field(..., min_length=3, max_length=10)
    impacto: str = Field(..., min_length=3, max_length=20)


# ─────────── Catálogos ───────────

@router.get("/profiles")
async def list_profiles():
    return {
        "profiles": [
            {
                "codigo": p,
                "sla_respuesta_horas": SLA_BY_PROFILE[p],
                "horas_previstas_anual": HOURS_BY_PROFILE[p],
                "actividades": sorted(CADENCES_BY_PROFILE[p].keys()),
            }
            for p in VALID_PROFILES
        ]
    }


@router.get("/profiles/{profile}/cadences")
async def get_profile_cadences(profile: str):
    if profile not in CADENCES_BY_PROFILE:
        raise HTTPException(status_code=404, detail=f"Profile {profile} no existe")
    return {
        "profile": profile,
        "sla_respuesta_horas": SLA_BY_PROFILE[profile],
        "horas_previstas_anual": HOURS_BY_PROFILE[profile],
        "cadencias": CADENCES_BY_PROFILE[profile],
    }


@router.get("/drift-catalog")
async def drift_catalog():
    return {
        "dimensions": list(DRIFT_DIMENSIONS),
        "severities": list(DRIFT_SEVERITIES),
        "impacts": list(DRIFT_IMPACTS),
    }


# ─────────── Dashboard multi-cliente (SIN RLS) ───────────

@router.get("/dashboard")
async def dashboard(db: AsyncSession = Depends(get_db)):
    """Vista global Marcos — bypass RLS (regla 13)."""
    return await RetainerService().get_dashboard(db)


@router.get("/list")
async def list_all_retainers(
    estado: Optional[str] = None,
    perfil: Optional[str] = None,
    rag: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Listado global sin RLS."""
    rows = await RetainerService().list_all_retainers_admin(
        db, estado=estado, perfil=perfil, rag=rag,
    )
    return {"retainers": [_serialize(r) for r in rows]}


@router.get("/active-client-ids")
async def list_active_retainer_client_ids(
    db: AsyncSession = Depends(get_db),
) -> dict[str, list[str]]:
    """#29 · IDs de clientes con un retainer ACTIVO · alimenta el bucket
    'En retainer' del sidebar admin (antes ``filterRetainer`` devolvía siempre []).
    Vista global Marcos (require_owner a nivel de router · sin RLS)."""
    # FIX(RLS): retainer_contracts es RLS fail-closed bajo fulkro_app · sin bypass
    # ni tenant context la query devuelve [] (los retainers reales tienen
    # project_id non-NULL → ni client_isolation ni el escape project_id IS NULL los
    # rescatan). Elevar a bypassrls como hacen /dashboard y /list (vía service).
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    try:
        rows = await db.execute(text(
            "SELECT DISTINCT client_id FROM retainer_contracts "
            "WHERE estado = 'active' AND deleted_at IS NULL"
        ))
        client_ids = [str(r[0]) for r in rows.all()]
    finally:
        await db.execute(text("RESET ROLE"))
    return {"client_ids": client_ids}


# ─────────── Lifecycle por proyecto ───────────

@router.post(
    "/projects/{project_id}/retainer",
    status_code=status.HTTP_201_CREATED,
)
async def create_retainer(
    project_id: uuid.UUID,
    body: CreateRetainerBody,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    try:
        r = await RetainerService().create_retainer(
            db,
            client_id=body.client_id,
            project_id=project_id,
            perfil=body.perfil,
            precio_mensual=body.precio_mensual,
            inicio=body.inicio,
            fin=body.fin,
            contract_id=body.contract_id,
            next_renewal_date=body.next_renewal_date,
            modalidad=body.modalidad,
        )
    except RetainerError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return _serialize(r)


@router.get("/projects/{project_id}/retainer")
async def get_retainer_by_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    r = await RetainerService().get_retainer_by_project(db, project_id)
    if not r:
        raise HTTPException(status_code=404, detail="Retainer not found")
    return _serialize(r)


@router.patch("/projects/{project_id}/retainer")
async def update_retainer(
    project_id: uuid.UUID,
    body: UpdateRetainerBody,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    svc = RetainerService()
    r = await svc.get_retainer_by_project(db, project_id)
    if not r:
        raise HTTPException(status_code=404, detail="Retainer not found")
    try:
        if body.perfil and body.perfil != r.perfil:
            r = await svc.update_retainer_profile(db, r.id, body.perfil)
        if body.precio_mensual is not None:
            r.precio_mensual = body.precio_mensual
        if body.fin is not None:
            r.fin = body.fin
        if body.renovacion_automatica is not None:
            r.renovacion_automatica = body.renovacion_automatica
        if body.estado is not None:
            if body.estado not in {"active", "paused", "expired", "cancelled"}:
                raise HTTPException(
                    status_code=422,
                    detail="estado invalido · active/paused/expired/cancelled",
                )
            r.estado = body.estado
        await db.flush()
    except RetainerError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return _serialize(r)


@router.post("/projects/{project_id}/retainer/pause")
async def pause_retainer(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    svc = RetainerService()
    r = await svc.get_retainer_by_project(db, project_id)
    if not r:
        raise HTTPException(status_code=404, detail="Retainer not found")
    r = await svc.pause_retainer(db, r.id)
    await db.commit()
    return _serialize(r)


@router.post("/projects/{project_id}/retainer/cancel")
async def cancel_retainer(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    svc = RetainerService()
    r = await svc.get_retainer_by_project(db, project_id)
    if not r:
        raise HTTPException(status_code=404, detail="Retainer not found")
    r = await svc.cancel_retainer(db, r.id)
    await db.commit()
    return _serialize(r)


# ─────────── Activities ───────────

@router.post(
    "/projects/{project_id}/retainer/activities/generate",
    status_code=status.HTTP_201_CREATED,
)
async def generate_activities(
    project_id: uuid.UUID,
    body: GenerateActivitiesBody,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    svc = RetainerService()
    r = await svc.get_retainer_by_project(db, project_id)
    if not r:
        raise HTTPException(status_code=404, detail="Retainer not found")
    try:
        activities = await svc.generate_annual_activities(db, r.id, body.year)
    except RetainerError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return {
        "year": body.year,
        "count": len(activities),
        "activities": [_serialize_activity(a) for a in activities],
    }


@router.get("/projects/{project_id}/retainer/activities")
async def list_activities(
    project_id: uuid.UUID,
    tipo: Optional[str] = None,
    estado: Optional[str] = None,
    desde: Optional[date] = None,
    hasta: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    activities = await RetainerService().list_activities(
        db, project_id=project_id, tipo=tipo, estado=estado, desde=desde, hasta=hasta,
    )
    return {"activities": [_serialize_activity(a) for a in activities]}


@router.post("/projects/{project_id}/retainer/activities/{activity_id}/start")
async def start_activity(
    project_id: uuid.UUID,
    activity_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    try:
        a = await RetainerService().start_activity(db, activity_id)
    except RetainerError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return _serialize_activity(a)


@router.post("/projects/{project_id}/retainer/activities/{activity_id}/complete")
async def complete_activity(
    project_id: uuid.UUID,
    activity_id: uuid.UUID,
    body: CompleteActivityBody,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    try:
        a = await RetainerService().complete_activity(
            db, activity_id,
            horas_consumidas=body.horas_consumidas,
            resultado=body.resultado,
        )
    except RetainerError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return _serialize_activity(a)


@router.get("/projects/{project_id}/retainer/activities/overdue")
async def overdue_activities(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    svc = RetainerService()
    r = await svc.get_retainer_by_project(db, project_id)
    if not r:
        raise HTTPException(status_code=404, detail="Retainer not found")
    activities = await svc.get_overdue_activities(db, r.id)
    return {"activities": [_serialize_activity(a) for a in activities]}


# ─────────── Renewal clock ───────────

@router.get("/projects/{project_id}/retainer/renewal-status")
async def renewal_status(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    svc = RetainerService()
    r = await svc.get_retainer_by_project(db, project_id)
    if not r:
        raise HTTPException(status_code=404, detail="Retainer not found")
    r = await svc.update_renewal_status(db, r.id)
    return {
        "retainer_id": str(r.id),
        "next_renewal_date": r.next_renewal_date.isoformat() if r.next_renewal_date else None,
        "renewal_status": r.renewal_status,
    }


@router.post("/projects/{project_id}/retainer/renew")
async def renew_retainer(
    project_id: uuid.UUID,
    body: RenewBody,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    svc = RetainerService()
    r = await svc.get_retainer_by_project(db, project_id)
    if not r:
        raise HTTPException(status_code=404, detail="Retainer not found")
    r = await svc.mark_renewed(db, r.id, body.new_renewal_date)
    await db.commit()
    return _serialize(r)


# ─────────── Drift ───────────

@router.post(
    "/projects/{project_id}/retainer/drifts",
    status_code=status.HTTP_201_CREATED,
)
async def register_drift(
    project_id: uuid.UUID,
    body: RegisterDriftBody,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    svc = RetainerService()
    r = await svc.get_retainer_by_project(db, project_id)
    if not r:
        raise HTTPException(status_code=404, detail="Retainer not found")
    try:
        d = await svc.register_drift(
            db,
            retainer_id=r.id,
            project_id=project_id,
            dimension=body.dimension,
            descripcion=body.descripcion,
            severidad=body.severidad,
            impacto=body.impacto,
        )
    except RetainerError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return _serialize_drift(d)


@router.get("/projects/{project_id}/retainer/drifts")
async def list_drifts(
    project_id: uuid.UUID,
    severidad: Optional[str] = None,
    estado: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    drifts = await RetainerService().list_drifts(
        db, project_id=project_id, severidad=severidad, estado=estado,
    )
    return {"drifts": [_serialize_drift(d) for d in drifts]}


@router.post("/projects/{project_id}/retainer/drifts/{drift_id}/resolve")
async def resolve_drift(
    project_id: uuid.UUID,
    drift_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    try:
        d = await RetainerService().resolve_drift(db, drift_id)
    except RetainerError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await db.commit()
    return _serialize_drift(d)


@router.post("/projects/{project_id}/retainer/rag/recalculate")
async def recalculate_rag(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    svc = RetainerService()
    r = await svc.get_retainer_by_project(db, project_id)
    if not r:
        raise HTTPException(status_code=404, detail="Retainer not found")
    rag = await svc.calculate_rag(db, r.id)
    await db.commit()
    return {"retainer_id": str(r.id), "rag_status": rag}


# ─────────── GAP 2: Recurring billing M23 → M15 ───────────

@router.post(
    "/projects/{project_id}/retainer/generate-monthly-invoice",
    status_code=status.HTTP_201_CREATED,
)
async def generate_monthly_invoice_endpoint(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Genera factura mensual para el retainer del proyecto."""
    await _set_project_rls(project_id, db)
    svc = RetainerService()
    r = await svc.get_retainer_by_project(db, project_id)
    if not r:
        raise HTTPException(status_code=404, detail="Retainer not found")
    try:
        result = await svc.generate_monthly_invoice(db, r.id)
    except RetainerError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return result


# ─────────── Serializers ───────────

def _serialize(r):
    return {
        "id": str(r.id),
        "client_id": str(r.client_id) if r.client_id else None,
        "project_id": str(r.project_id) if r.project_id else None,
        "contract_id": str(r.contract_id) if r.contract_id else None,
        "perfil": r.perfil,
        "modalidad": r.modalidad,
        "precio_mensual": float(r.precio_mensual) if r.precio_mensual is not None else None,
        "inicio": r.inicio.isoformat() if r.inicio else None,
        "fin": r.fin.isoformat() if r.fin else None,
        "renovacion_automatica": r.renovacion_automatica,
        "sla_respuesta_horas": r.sla_respuesta_horas,
        "estado": r.estado,
        "next_renewal_date": r.next_renewal_date.isoformat() if r.next_renewal_date else None,
        "renewal_status": r.renewal_status,
        "rag_status": r.rag_status,
        "horas_consumidas_total": float(r.horas_consumidas_total or 0),
        "horas_previstas_anual": float(r.horas_previstas_anual or 0),
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


def _serialize_activity(a):
    return {
        "id": str(a.id),
        "retainer_contract_id": str(a.retainer_contract_id),
        "project_id": str(a.project_id) if a.project_id else None,
        "tipo_actividad": a.tipo_actividad,
        "titulo": a.titulo,
        "descripcion": a.descripcion,
        "fecha_programada": a.fecha_programada.isoformat() if a.fecha_programada else None,
        "fecha_ejecutada": a.fecha_ejecutada.isoformat() if a.fecha_ejecutada else None,
        "estado": a.estado,
        "horas_estimadas": float(a.horas_estimadas or 0),
        "horas_consumidas": float(a.horas_consumidas or 0),
        "resultado": a.resultado,
        "prioridad": a.prioridad,
    }


def _serialize_drift(d):
    return {
        "id": str(d.id),
        "retainer_contract_id": str(d.retainer_contract_id),
        "project_id": str(d.project_id),
        "dimension": d.dimension,
        "descripcion": d.descripcion,
        "severidad": d.severidad,
        "impacto": d.impacto,
        "estado": d.estado,
        "resuelto_at": d.resuelto_at.isoformat() if d.resuelto_at else None,
        "created_at": d.created_at.isoformat() if d.created_at else None,
    }


# ═══════════════════════════════════════════════════════════════════
# MB-7.bis atom 7.bis.4 · DOCX report rendering endpoints (Q5.B+D)
# ═══════════════════════════════════════════════════════════════════

import io as _io

_DOCX_MEDIA = (
    "application/vnd.openxmlformats-officedocument."
    "wordprocessingml.document"
)


@router.get("/{retainer_id}/reports/quarterly/{period_start}/download")
async def download_quarterly_report(
    retainer_id: uuid.UUID,
    period_start: str,
    db: AsyncSession = Depends(get_db),
):
    """Render+download quarterly DOCX for retainer + period_start (YYYY-MM-DD)."""
    await _set_rls_for_retainer(retainer_id, db)
    try:
        blob = await render_quarterly_report_docx(
            db, retainer_id, period_start,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    filename = f"retainer_{retainer_id}_quarterly_{period_start}.docx"
    return StreamingResponse(
        _io.BytesIO(blob),
        media_type=_DOCX_MEDIA,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get("/{retainer_id}/reports/annual/{year}/download")
async def download_annual_report(
    retainer_id: uuid.UUID,
    year: int,
    db: AsyncSession = Depends(get_db),
):
    """Render+download annual DOCX aggregating 4 quarters of `year`."""
    if year < 2024 or year > 2100:
        raise HTTPException(status_code=400, detail="Year out of range")
    await _set_rls_for_retainer(retainer_id, db)
    try:
        blob = await render_annual_report_docx(db, retainer_id, year)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    filename = f"retainer_{retainer_id}_annual_{year}.docx"
    return StreamingResponse(
        _io.BytesIO(blob),
        media_type=_DOCX_MEDIA,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
