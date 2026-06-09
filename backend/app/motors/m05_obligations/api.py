"""Motor 5 -- Obligations API endpoints.

Thin HTTP layer for obligation instantiation and Gantt planning.
Pattern consistent with M04 Gap Analysis and M03 DdA Engine.
"""
from __future__ import annotations

import uuid
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db, set_tenant_context
from backend.app.models.ens import Obligation
from backend.app.motors.m05_obligations.gantt_service import (
    build_gantt_for_project,
    export_gantt_to_xlsx_bytes,
)
from backend.app.motors.m05_obligations.gantt_types import CircularDependencyError
from backend.app.motors.m05_obligations.instantiation_service import (
    instantiate_obligations_for_multiple_gaps,
)
from backend.app.motors.m05_obligations.instantiation_types import (
    ClientContext,
    GapInput,
    ProjectContext,
)

from backend.app.auth.dependencies import require_owner

router = APIRouter(
    tags=["Motor 5 - Obligations"],
    # TODO-RBAC-PER-ENDPOINT-001 Cat A: Marcos-only.
    dependencies=[Depends(require_owner)],
)


# ── Request / Response schemas ────────────────────────────────────────


class GapItem(BaseModel):
    gap_id: uuid.UUID
    measure_code: str


class ClienteBody(BaseModel):
    razon_social: str
    sector: str | None = None


class InstantiateRequest(BaseModel):
    nombre_proyecto: str
    categoria_ens: str
    cliente: ClienteBody
    gaps: list[GapItem]
    use_llm_personalization: bool = False


class InstantiateOutcomeItem(BaseModel):
    gap_id: uuid.UUID | None
    measure_code: str
    created: int
    existing: int
    validation_errors: list[str] = Field(default_factory=list)


class InstantiateResponse(BaseModel):
    total_created: int
    total_existing: int
    outcomes: list[InstantiateOutcomeItem]


# ── Helpers ───────────────────────────────────────────────────────────


async def _set_project_rls(project_id: uuid.UUID, db: AsyncSession):
    """Set RLS context for obligations table via project owner lookup."""
    client_id = (
        await db.execute(
            text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)}
        )
    ).scalar()
    if not client_id:
        raise HTTPException(status_code=404, detail="Project not found")
    await set_tenant_context(db, client_id=client_id, project_id=project_id)


# ── Instantiation endpoint ───────────────────────────────────────────


@router.post(
    "/projects/{project_id}/obligations/instantiate",
    response_model=InstantiateResponse,
)
async def instantiate_obligations(
    project_id: uuid.UUID,
    body: InstantiateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Instantiate obligations from library templates for the given gaps."""
    await _set_project_rls(project_id, db)

    ctx = ProjectContext(
        project_id=project_id,
        nombre_proyecto=body.nombre_proyecto,
        categoria_ens=body.categoria_ens,
        cliente=ClientContext(
            razon_social=body.cliente.razon_social,
            sector=body.cliente.sector,
        ),
    )
    gap_inputs = [
        GapInput(gap_id=g.gap_id, measure_code=g.measure_code)
        for g in body.gaps
    ]

    outcomes = await instantiate_obligations_for_multiple_gaps(
        db,
        gap_inputs,
        ctx,
        use_llm_personalization=body.use_llm_personalization,
    )
    await db.commit()

    items = []
    total_created = 0
    total_existing = 0
    for o in outcomes:
        created = len(o.obligations_created_ids)
        existing = len(o.obligations_existing_ids)
        total_created += created
        total_existing += existing
        items.append(
            InstantiateOutcomeItem(
                gap_id=o.gap_id,
                measure_code=o.measure_code,
                created=created,
                existing=existing,
                validation_errors=o.validation_errors,
            )
        )

    return InstantiateResponse(
        total_created=total_created,
        total_existing=total_existing,
        outcomes=items,
    )


# ── Gantt endpoint ────────────────────────────────────────────────────


@router.get("/projects/{project_id}/obligations/gantt")
async def get_gantt(
    project_id: uuid.UUID,
    fecha_kickoff: date = Query(..., description="Project kickoff date (YYYY-MM-DD)"),
    dedicacion_horas_semana: float = Query(
        8.0, description="Weekly effort hours dedicated by client"
    ),
    format: Literal["json", "xlsx"] = Query(
        "json", description="Response format: json or xlsx"
    ),
    db: AsyncSession = Depends(get_db),
):
    """Build a Gantt plan for the project's obligations."""
    await _set_project_rls(project_id, db)

    try:
        plan = await build_gantt_for_project(
            db,
            project_id=project_id,
            fecha_kickoff=fecha_kickoff,
            dedicacion_horas_semana=dedicacion_horas_semana,
        )
    except CircularDependencyError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if format == "xlsx":
        xlsx_bytes = export_gantt_to_xlsx_bytes(plan)
        return Response(
            content=xlsx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename=gantt_{project_id}.xlsx"
            },
        )

    return plan.to_json_dict()


# ═══════════════════════════════════════════════════════════════
# CRUD + Estado + Summary (sprint C2)
# ═══════════════════════════════════════════════════════════════

VALID_ESTADOS_OBLIGATION = {
    "pendiente", "en_curso", "completada", "verificada", "bloqueada",
}


class CreateObligationBody(BaseModel):
    titulo: str = Field(..., min_length=2, max_length=200)
    descripcion: str = Field(..., min_length=2)
    measure_code: str | None = Field(None, max_length=40)
    tipo_ejecucion: str | None = Field(None, max_length=50)
    modo_ejecucion: str | None = Field(None, max_length=50)
    responsable: str | None = Field(None, max_length=255)
    esfuerzo_estimado: float | None = Field(None, ge=0)
    fecha_objetivo: date | None = None
    gap_id: uuid.UUID | None = None
    entregable_esperado: str | None = Field(None, max_length=255)


class UpdateObligationBody(BaseModel):
    titulo: str | None = Field(None, max_length=200)
    descripcion: str | None = None
    responsable: str | None = Field(None, max_length=255)
    modo_ejecucion: str | None = Field(None, max_length=50)
    estado: str | None = Field(None, max_length=50)
    esfuerzo_estimado: float | None = Field(None, ge=0)
    fecha_objetivo: date | None = None


def _serialize_obligation(ob: Obligation) -> dict:
    return {
        "id": str(ob.id),
        "project_id": str(ob.project_id),
        "gap_id": str(ob.gap_id) if ob.gap_id else None,
        "titulo": ob.titulo,
        "descripcion": ob.descripcion,
        "measure_code": ob.measure_code,
        "tipo_ejecucion": ob.tipo_ejecucion,
        "modo_ejecucion": ob.modo_ejecucion,
        "estado": ob.estado,
        "responsable": ob.responsable,
        "esfuerzo_estimado": float(ob.esfuerzo_estimado) if ob.esfuerzo_estimado is not None else None,
        "fecha_objetivo": ob.fecha_objetivo.isoformat() if ob.fecha_objetivo else None,
        "fecha_completado": ob.fecha_completado.isoformat() if ob.fecha_completado else None,
        "entregable_esperado": ob.entregable_esperado,
        "template_id": ob.template_id,
        "created_at": ob.created_at.isoformat() if ob.created_at else None,
    }


@router.post(
    "/projects/{project_id}/obligations",
    status_code=http_status.HTTP_201_CREATED,
)
async def create_obligation(
    project_id: uuid.UUID,
    body: CreateObligationBody,
    db: AsyncSession = Depends(get_db),
):
    """Crea obligación manual.

    GAP 5: si `modo_ejecucion == "cliente_aporta_evidencia"`, genera magic link
    M12 tipo APORTE_EVIDENCIA automáticamente. Best-effort.
    """
    await _set_project_rls(project_id, db)
    ob = Obligation(
        project_id=project_id,
        gap_id=body.gap_id,
        titulo=body.titulo,
        descripcion=body.descripcion,
        measure_code=body.measure_code,
        tipo_ejecucion=body.tipo_ejecucion,
        modo_ejecucion=body.modo_ejecucion,
        responsable=body.responsable,
        esfuerzo_estimado=body.esfuerzo_estimado,
        fecha_objetivo=body.fecha_objetivo,
        entregable_esperado=body.entregable_esperado,
        estado="pendiente",
    )
    db.add(ob)
    await db.flush()

    # Hook GAP 5: cliente_aporta → magic link
    magic_link_data = None
    if body.modo_ejecucion == "cliente_aporta_evidencia":
        magic_link_data = await _trigger_cliente_aporta_magic_link(
            db, project_id, ob,
        )

    response = _serialize_obligation(ob)
    if magic_link_data:
        response["magic_link"] = magic_link_data
    return response


async def _trigger_cliente_aporta_magic_link(
    db: AsyncSession,
    project_id: uuid.UUID,
    ob: Obligation,
) -> dict | None:
    """Trigger evidence_request notification para obligación cliente_aporta.

    Post-MB-4.bis3 (ADR-020 v3 IMPLEMENTED FULLY): emite ClientNotification
    in-portal · target_url /client-portal/evidencias?obligation={id}.
    NO genera magic_link cliente.

    Si NO hay ClientUser activado para el proyecto · retorna None
    (best-effort · NO bloquea creación obligación).
    """
    try:
        from sqlalchemy import select
        from backend.app.models.client_portal import ClientUser
        from backend.app.models.core import Project
        from backend.app.motors.m21_portal_cliente import (
            notification_service,
        )

        # Resuelve client_user del proyecto · single-user-RW (ADR-013 v3)
        proj_res = await db.execute(
            select(Project).where(Project.id == project_id),
        )
        project = proj_res.scalar_one_or_none()
        if project is None:
            return None
        user_res = await db.execute(
            select(ClientUser)
            .where(ClientUser.client_id == project.client_id)
            .order_by(ClientUser.created_at.desc())
            .limit(1),
        )
        client_user = user_res.scalar_one_or_none()
        if client_user is None:
            # Cliente no tiene cuenta portal aún · ignora silenciosamente
            return None

        notif = await notification_service.emit_client_notification(
            db,
            project_id=project_id,
            client_user_id=client_user.id,
            type="evidence_request",
            title=f"Aportar evidencia: {ob.measure_code}",
            body=ob.titulo,
            target_url=f"/client-portal/evidencias?obligation={ob.id}",
            priority="high",
            payload={
                "obligation_id": str(ob.id),
                "measure_code": ob.measure_code,
                "titulo": ob.titulo,
            },
            emitted_by_motor="m05",
        )
        return {
            "notification_id": str(notif.id),
            "type": notif.type,
            "target_url": notif.target_url,
            "_portal_alternative": notif.target_url,
        }
    except Exception:
        # Best-effort: si falla la notification, NO bloquear creación obligación
        return None


@router.get("/projects/{project_id}/obligations")
async def list_obligations(
    project_id: uuid.UUID,
    estado: str | None = Query(None),
    modo: str | None = Query(None),
    measure: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Lista obligaciones del proyecto con filtros opcionales."""
    await _set_project_rls(project_id, db)
    stmt = select(Obligation).where(
        Obligation.project_id == project_id,
        Obligation.deleted_at.is_(None),
    )
    if estado:
        stmt = stmt.where(Obligation.estado == estado)
    if modo:
        stmt = stmt.where(Obligation.modo_ejecucion == modo)
    if measure:
        stmt = stmt.where(Obligation.measure_code == measure)
    stmt = stmt.order_by(Obligation.created_at.desc())
    res = await db.execute(stmt)
    return {"obligations": [_serialize_obligation(o) for o in res.scalars().all()]}


@router.get("/projects/{project_id}/obligations/summary")
async def obligations_summary(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Resumen: total + counts por estado."""
    await _set_project_rls(project_id, db)
    rows = (await db.execute(
        select(Obligation.estado, func.count(Obligation.id)).where(
            Obligation.project_id == project_id,
            Obligation.deleted_at.is_(None),
        ).group_by(Obligation.estado)
    )).all()
    by_estado = {row[0] or "sin_estado": row[1] for row in rows}
    return {
        "total": sum(by_estado.values()),
        "by_estado": by_estado,
        "pendientes": by_estado.get("pendiente", 0),
        "en_curso": by_estado.get("en_curso", 0),
        "completadas": by_estado.get("completada", 0),
        "verificadas": by_estado.get("verificada", 0),
    }


@router.get("/projects/{project_id}/obligations/{obligation_id}")
async def get_obligation(
    project_id: uuid.UUID,
    obligation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    res = await db.execute(
        select(Obligation).where(
            Obligation.id == obligation_id,
            Obligation.project_id == project_id,
        )
    )
    ob = res.scalar_one_or_none()
    if not ob:
        raise HTTPException(status_code=404, detail="Obligation not found")
    return _serialize_obligation(ob)


@router.patch("/projects/{project_id}/obligations/{obligation_id}")
async def update_obligation(
    project_id: uuid.UUID,
    obligation_id: uuid.UUID,
    body: UpdateObligationBody,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    ob = (await db.execute(
        select(Obligation).where(
            Obligation.id == obligation_id,
            Obligation.project_id == project_id,
        )
    )).scalar_one_or_none()
    if not ob:
        raise HTTPException(status_code=404, detail="Obligation not found")
    updates = body.model_dump(exclude_none=True)
    if "estado" in updates and updates["estado"] not in VALID_ESTADOS_OBLIGATION:
        raise HTTPException(
            status_code=400,
            detail=f"Estado inválido. Válidos: {sorted(VALID_ESTADOS_OBLIGATION)}",
        )
    for key, val in updates.items():
        setattr(ob, key, val)
    await db.flush()
    return _serialize_obligation(ob)


async def _transition_estado(
    db: AsyncSession,
    project_id: uuid.UUID,
    obligation_id: uuid.UUID,
    from_states: tuple[str, ...],
    to_state: str,
    mark_completado: bool = False,
) -> dict:
    await _set_project_rls(project_id, db)
    ob = (await db.execute(
        select(Obligation).where(
            Obligation.id == obligation_id,
            Obligation.project_id == project_id,
        )
    )).scalar_one_or_none()
    if not ob:
        raise HTTPException(status_code=404, detail="Obligation not found")
    if ob.estado not in from_states:
        raise HTTPException(
            status_code=400,
            detail=f"Transición no permitida desde '{ob.estado}' a '{to_state}'. Origen válido: {list(from_states)}",
        )
    ob.estado = to_state
    if mark_completado:
        from datetime import datetime as _dt, timezone as _tz
        ob.fecha_completado = _dt.now(_tz.utc)
    await db.flush()
    return _serialize_obligation(ob)


@router.post("/projects/{project_id}/obligations/{obligation_id}/start")
async def start_obligation(
    project_id: uuid.UUID,
    obligation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    return await _transition_estado(
        db, project_id, obligation_id, ("pendiente", "bloqueada"), "en_curso",
    )


@router.post("/projects/{project_id}/obligations/{obligation_id}/complete")
async def complete_obligation(
    project_id: uuid.UUID,
    obligation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    return await _transition_estado(
        db, project_id, obligation_id, ("en_curso", "pendiente"), "completada",
        mark_completado=True,
    )


@router.post("/projects/{project_id}/obligations/{obligation_id}/verify")
async def verify_obligation(
    project_id: uuid.UUID,
    obligation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    return await _transition_estado(
        db, project_id, obligation_id, ("completada",), "verificada",
    )
