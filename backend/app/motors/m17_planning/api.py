"""Motor 17 Planning API."""
from __future__ import annotations

import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db, set_tenant_context
from backend.app.auth.dependencies import require_owner

from . import effort_estimator, planning_service


router = APIRouter(
    prefix="/planning", tags=["Motor 17 - Project Planning"],
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


# ============ Schemas ============

class GeneratePlanBody(BaseModel):
    categoria: str = Field(..., min_length=1, max_length=10)
    start_date: date
    client_size: str = Field("mediana", max_length=20)
    complexity: str = Field("media", max_length=20)
    marcos_weekly_hours: float = Field(20.0, ge=1, le=60)
    client_weekly_hours: float = Field(8.0, ge=0, le=40)


class UpdateTaskBody(BaseModel):
    status: Optional[str] = Field(None, max_length=20)
    progress_pct: Optional[int] = Field(None, ge=0, le=100)
    blocker_description: Optional[str] = Field(None, max_length=2000)


class CreateCRBody(BaseModel):
    titulo: str = Field(..., min_length=2, max_length=300)
    descripcion: str = Field(..., min_length=2)
    impacto_plazo_dias: Optional[int] = None
    impacto_esfuerzo_horas: Optional[float] = None
    impacto_presupuesto_eur: Optional[float] = None
    solicitado_por: str = Field("marcos", max_length=200)


class ApprovalBody(BaseModel):
    aprobado_por: str = Field(..., min_length=2, max_length=200)


class EstimateEffortBody(BaseModel):
    base_hours: float = Field(..., ge=0)
    categoria: str = Field(..., min_length=1, max_length=10)
    client_size: str = Field("mediana", max_length=20)
    complexity: str = Field("media", max_length=20)


class EstimateFullBody(BaseModel):
    """Estimacion completa (Apendice N — calibrado).

    NO requiere ``base_hours``: se obtiene del catalogo
    ``effort_formulas_v1.json`` segun la categoria ENS.
    """
    categoria: str = Field(..., min_length=1, max_length=10, description="BASICA | MEDIA | ALTA")
    sector: str = Field("generico", max_length=40)
    madurez: str = Field("L3", max_length=4, description="L1 | L2 | L3 | L4 | L5")
    client_size: str | None = Field(None, max_length=20, description="micro | pequena | mediana | grande | muy_grande. Si se omite y se pasa n_empleados, se infiere.")
    complexity: str = Field("media", max_length=20, description="baja | media | alta | muy_alta")
    n_empleados: int | None = Field(None, ge=0, description="Opcional: para auto-clasificacion del size si client_size es null")
    tarifa_hora_eur: float | None = Field(None, ge=0, description="Opcional: override del tarifa_hora_eur_default del catalogo")


# ============ Plan ============

@router.post("/projects/{project_id}/generate")
async def generate_plan_endpoint(
    project_id: uuid.UUID,
    body: GeneratePlanBody,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    try:
        plan = await planning_service.generate_plan(
            session, project_id,
            categoria=body.categoria, start_date=body.start_date,
            client_size=body.client_size, complexity=body.complexity,
            marcos_weekly_hours=body.marcos_weekly_hours,
            client_weekly_hours=body.client_weekly_hours,
        )
    except planning_service.PlanningError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc),
        )
    await session.commit()
    return planning_service.plan_to_dict(plan)


@router.get("/projects/{project_id}")
async def get_plan_endpoint(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    plan = await planning_service.get_plan(session, project_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="No hay plan para el proyecto")
    return planning_service.plan_to_dict(plan)


@router.post("/projects/{project_id}/baseline")
async def set_baseline_endpoint(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    plan = await planning_service.get_plan(session, project_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="No hay plan para el proyecto")
    try:
        plan = await planning_service.set_baseline(session, plan.id)
    except planning_service.PlanningError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc),
        )
    await session.commit()
    return planning_service.plan_to_dict(plan)


@router.get("/projects/{project_id}/progress")
async def plan_progress_endpoint(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    plan = await planning_service.get_plan(session, project_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="No hay plan")
    return await planning_service.get_plan_progress(session, plan.id)


@router.get("/projects/{project_id}/fase0-governance")
async def fase0_governance_endpoint(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    """FASE 0 gobierno · estado del checklist (P10-F09 · Ejecutable 8 Pasada 16).

    Composer thin pure-functional: pasos kickoff→alcance→roles→comité→plan con
    branch por categoría (BÁSICA vs MEDIA/ALTA), separación RSeg≠RSis (m30) y
    cadencia del comité (m_meetings). Read-only · admin require_owner.
    """
    await _set_project_rls(project_id, session)
    from backend.app.motors.m17_planning.fase0_governance import (
        compute_fase0_governance_state,
    )
    return await compute_fase0_governance_state(session, project_id)


@router.get("/projects/{project_id}/delays")
async def plan_delays_endpoint(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    plan = await planning_service.get_plan(session, project_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="No hay plan")
    delays = await planning_service.detect_delays(session, plan.id)
    return {"total": len(delays), "delays": delays}


@router.get("/projects/{project_id}/mermaid")
async def plan_mermaid_endpoint(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    plan = await planning_service.get_plan(session, project_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="No hay plan")
    return {
        "mermaid_gantt": plan.mermaid_gantt or "",
        "plan_id": str(plan.id),
    }


@router.get("/projects/{project_id}/export/xlsx")
async def plan_export_xlsx_endpoint(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    from fastapi.responses import Response
    await _set_project_rls(project_id, session)
    plan = await planning_service.get_plan(session, project_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="No hay plan")
    tasks = await planning_service.get_tasks(session, plan.id)
    data = planning_service.export_gantt_xlsx(tasks, plan)
    return Response(
        content=data,
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": (
                f'attachment; filename="gantt_{project_id}.xlsx"'
            ),
        },
    )


@router.post("/projects/{project_id}/pda/generate")
async def generate_pda_endpoint(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    """Genera Plan de Adecuación CCN-STIC 806 (DOCX) cross-motor.

    Aglutina M01 categorización + M02 MAGERIT + M03 DdA + M04 gap +
    M17 plan tasks en un único DOCX firmable conforme E-150 (CCN-STIC
    806). Output streaming para descarga directa.

    Refs: SAN-C.MB-9.3
    """
    from fastapi.responses import Response

    from .pda_generator import build_pda_context, generate_pda_docx

    await _set_project_rls(project_id, session)
    ctx = await build_pda_context(session, project_id)
    bio = generate_pda_docx(ctx)
    return Response(
        content=bio.getvalue(),
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
        headers={
            "Content-Disposition": (
                f'attachment; filename="plan_adecuacion_{project_id}.docx"'
            ),
        },
    )


# ============ Tasks ============

@router.get("/projects/{project_id}/tasks")
async def list_tasks_endpoint(
    project_id: uuid.UUID,
    phase: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    is_critical: Optional[bool] = Query(None),
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    plan = await planning_service.get_plan(session, project_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="No hay plan")
    tasks = await planning_service.get_tasks(
        session, plan.id, phase=phase, status=status, is_critical=is_critical,
    )
    return [planning_service.task_to_dict(t) for t in tasks]


@router.get("/projects/{project_id}/tasks/critical-path")
async def critical_path_endpoint(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    plan = await planning_service.get_plan(session, project_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="No hay plan")
    tasks = await planning_service.get_tasks(
        session, plan.id, is_critical=True,
    )
    return {
        "plan_id": str(plan.id),
        "total_critical": len(tasks),
        "tasks": [planning_service.task_to_dict(t) for t in tasks],
    }


@router.get("/projects/{project_id}/tasks/{task_id}")
async def get_task_endpoint(
    project_id: uuid.UUID,
    task_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    task = await planning_service.get_task(session, task_id)
    if task is None or task.project_id != project_id:
        raise HTTPException(status_code=404, detail="Task no encontrada")
    return planning_service.task_to_dict(task)


@router.patch("/projects/{project_id}/tasks/{task_id}")
async def update_task_endpoint(
    project_id: uuid.UUID,
    task_id: uuid.UUID,
    body: UpdateTaskBody,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    task = await planning_service.get_task(session, task_id)
    if task is None or task.project_id != project_id:
        raise HTTPException(status_code=404, detail="Task no encontrada")
    try:
        if body.status is not None:
            task = await planning_service.update_task_status(
                session, task_id,
                status=body.status,
                progress_pct=body.progress_pct,
                blocker=body.blocker_description,
            )
        else:
            if body.progress_pct is not None:
                task.progress_pct = max(0, min(100, int(body.progress_pct)))
            if body.blocker_description is not None:
                task.blocker_description = body.blocker_description
            await session.flush()
    except planning_service.PlanningError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc),
        )
    await session.commit()
    # El commit cierra la transacción y SET LOCAL pierde el contexto de tenant;
    # las lecturas post-commit (projects/ClientUser) quedarían sin RLS → no se
    # enviaría la notificación al cliente. Re-fijar contexto para el bloque siguiente.
    await _set_project_rls(project_id, session)

    # Sesión 3B-2B.8 Phase 1E · SSE dispatch m17.plan.updated cliente subscribe.
    # Best-effort try/except pattern Phase 1A+1B+1C+1D sostained.
    try:
        from backend.app.core.sse_dispatcher import sse_dispatcher

        await sse_dispatcher.dispatch(
            channel=f"project:{project_id}",
            event_type="m17.plan.updated",
            data={
                "task_id": str(task_id),
                "task_code": task.task_code,
                "task_name": task.task_name,
                "status": task.status,
                "progress_pct": task.progress_pct,
                "audience": "cliente",
            },
        )
    except Exception:
        import logging
        logging.getLogger(__name__).exception(
            "SSE dispatch m17.plan.updated failed",
        )

    # Sesión 3B-2B.8 CLUSTER 2 Phase 2B · SSE + ClientNotification dual emit
    # pattern (#14 cumulative). Admin PATCH task → cliente VE/RECIBE plan
    # update · filosofía cliente-mínimo aligned · priority low (no urgencia).
    try:
        from sqlalchemy import select as sa_select

        from backend.app.models.client_portal import ClientUser
        from backend.app.motors.m21_portal_cliente.notification_service import (
            emit_client_notification,
        )

        project_row = (await session.execute(
            text(
                "SELECT client_id FROM projects "
                "WHERE id = :pid AND deleted_at IS NULL"
            ),
            {"pid": str(project_id)},
        )).fetchone()
        if project_row:
            client_id = project_row[0]
            users_q = await session.execute(
                sa_select(ClientUser).where(
                    ClientUser.client_id == client_id,
                    ClientUser.deactivated_at.is_(None),
                )
            )
            for user in users_q.scalars().all():
                await emit_client_notification(
                    session,
                    project_id=project_id,
                    client_user_id=user.id,
                    type="generic_alert",
                    title="Plan ENS actualizado",
                    body=f"Marcos actualizó la tarea {task.task_name}.",
                    target_url="/client-portal/plan",
                    priority="low",
                    emitted_by_motor="m17_planning",
                    payload={
                        "task_id": str(task_id),
                        "task_code": task.task_code,
                        "task_name": task.task_name,
                        "source": "m17.plan.updated",
                    },
                )
            await session.commit()
    except Exception:  # pragma: no cover · best-effort
        import logging as _logging
        _logging.getLogger(__name__).exception(
            "ClientNotification emit failed post m17.plan.updated · task_id=%s",
            task_id,
        )

    return planning_service.task_to_dict(task)


# ============ Change Requests ============

@router.post("/projects/{project_id}/change-requests")
async def create_cr_endpoint(
    project_id: uuid.UUID,
    body: CreateCRBody,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    plan = await planning_service.get_plan(session, project_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="No hay plan")
    cr = await planning_service.create_change_request(
        session, project_id, plan.id,
        titulo=body.titulo, descripcion=body.descripcion,
        impacto_plazo_dias=body.impacto_plazo_dias,
        impacto_esfuerzo_horas=body.impacto_esfuerzo_horas,
        impacto_presupuesto_eur=body.impacto_presupuesto_eur,
        solicitado_por=body.solicitado_por,
    )
    await session.commit()
    return planning_service.cr_to_dict(cr)


@router.get("/projects/{project_id}/change-requests")
async def list_crs_endpoint(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    crs = await planning_service.list_change_requests(session, project_id)
    return [planning_service.cr_to_dict(cr) for cr in crs]


@router.get("/projects/{project_id}/change-requests/{cr_id}")
async def get_cr_endpoint(
    project_id: uuid.UUID,
    cr_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    cr = await planning_service.get_change_request(session, cr_id)
    if cr is None or cr.project_id != project_id:
        raise HTTPException(status_code=404, detail="CR no encontrado")
    return planning_service.cr_to_dict(cr)


@router.post("/projects/{project_id}/change-requests/{cr_id}/approve")
async def approve_cr_endpoint(
    project_id: uuid.UUID,
    cr_id: uuid.UUID,
    body: ApprovalBody,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    cr = await planning_service.get_change_request(session, cr_id)
    if cr is None or cr.project_id != project_id:
        raise HTTPException(status_code=404, detail="CR no encontrado")
    try:
        cr = await planning_service.approve_change_request(
            session, cr_id, body.aprobado_por,
        )
    except planning_service.PlanningError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc),
        )
    await session.commit()
    return planning_service.cr_to_dict(cr)


@router.post("/projects/{project_id}/change-requests/{cr_id}/reject")
async def reject_cr_endpoint(
    project_id: uuid.UUID,
    cr_id: uuid.UUID,
    body: ApprovalBody,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    cr = await planning_service.get_change_request(session, cr_id)
    if cr is None or cr.project_id != project_id:
        raise HTTPException(status_code=404, detail="CR no encontrado")
    cr = await planning_service.reject_change_request(
        session, cr_id, body.aprobado_por,
    )
    await session.commit()
    return planning_service.cr_to_dict(cr)


# ============ Effort estimator (global, no project) ============

@router.post("/estimate-effort")
async def estimate_effort_endpoint(body: EstimateEffortBody):
    try:
        hours = effort_estimator.estimate_effort(
            body.base_hours,
            categoria=body.categoria,
            client_size=body.client_size,
            complexity=body.complexity,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc),
        )
    return {
        "base_hours": body.base_hours,
        "categoria": body.categoria,
        "client_size": body.client_size,
        "complexity": body.complexity,
        "estimated_hours": hours,
        "duration_weeks": effort_estimator.estimate_duration_weeks(body.categoria),
    }


@router.post("/estimate-full")
async def estimate_full_endpoint(body: EstimateFullBody):
    """Estimacion completa con horas_base intrinsecas a la categoria ENS.

    Devuelve un breakdown auditable: horas base, factores aplicados con
    su justificacion textual, factor combinado, horas finales, presupuesto
    y avisos sobre limites de calibracion.
    """
    try:
        return effort_estimator.estimate_full(
            categoria=body.categoria,
            sector=body.sector,
            madurez=body.madurez,
            client_size=body.client_size,
            complexity=body.complexity,
            n_empleados=body.n_empleados,
            tarifa_hora_eur=body.tarifa_hora_eur,
        )
    except effort_estimator.EffortFormulasError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc),
        )


@router.get("/effort-formulas")
async def get_effort_formulas():
    """Devuelve el catalogo completo de formulas (lectura)."""
    try:
        return effort_estimator.load_formulas()
    except effort_estimator.EffortFormulasError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc),
        )
