"""Sesión 3B-2B.8 Phase 1E · M17 Planning cliente portal endpoint.

GET /api/v1/client-portal/plan · cliente READ-ONLY view del plan adecuación
ENS · returns TimelineResponse mirror admin schema + `responsible` field
expuesto para frontend "Solo mis tareas" filter.

Doctrinas:
- ADR-013 doble pool (require_client_user)
- ADR-014 read-only (cliente NO modifica · solo lectura)
- ADR-025 reuse get_project_timeline composer logic (NO duplicar)
- Sub-atom 5.A audit_log emit (project_id + client_id 3-way OR)
- R29 friendly Spanish · R30 inverso (NO admin lingo)
"""
from __future__ import annotations

import json as _json
import logging
import uuid
from datetime import date
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db, set_tenant_context
from backend.app.models.client_portal import ClientUser
from backend.app.models.core import Project
from backend.app.models.planning import ProjectPlan, WbsTask
from backend.app.motors.m21_portal_cliente.api import get_current_client_user


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/client-portal/plan",
    tags=["Motor 17 - Plan Cliente READ-ONLY"],
)


# ════════════════════════════════════════════════════════════════════
# Schemas (mirror admin TimelineResponse + responsible field expuesto)
# ════════════════════════════════════════════════════════════════════


class ClienteTimelineTask(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    task_code: str
    task_name: str
    phase: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: str | None = None
    progress_pct: int = 0
    is_critical_path: bool = False
    # Sesión 3B-2B.8 Phase 1E · exponer responsible para filter "Mis tareas"
    responsible: str | None = None


class ClienteTimelineMilestone(BaseModel):
    name: str
    date: date | None
    type: str
    status: str | None = None


class ClienteTimelineResponse(BaseModel):
    """Cliente READ-ONLY view del plan adecuación ENS."""

    plan_start: date | None
    plan_end: date | None
    tasks: list[ClienteTimelineTask]
    milestones: list[ClienteTimelineMilestone]
    plan_estado: str | None = None
    project_id: str


# ════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════


async def _resolve_project_id(
    db: AsyncSession, client_id: uuid.UUID,
) -> Optional[uuid.UUID]:
    row = (
        await db.execute(
            text(
                "SELECT id FROM projects "
                "WHERE client_id = :cid AND deleted_at IS NULL "
                "ORDER BY created_at DESC LIMIT 1"
            ),
            {"cid": str(client_id)},
        )
    ).first()
    return uuid.UUID(str(row[0])) if row else None


async def _resolve_project_id_scoped(
    db: AsyncSession, client_id: uuid.UUID,
) -> Optional[uuid.UUID]:
    """F-18-01b · resolución project-scoped cliente con contexto RLS correcto.

    Espeja ``m11_copiloto.portal_api._resolve_project_meta_scoped`` (Batch 1
    F-18-01). El runtime conecta como ``fulkro_app`` (RLS activa) y NO hay
    middleware que setee ``app.current_client_id`` → la política
    ``client_isolation`` de ``projects`` ciega la fila del cliente →
    ``_resolve_project_id`` plano devolvería ``None`` (fail-closed, NO fuga) y
    el timeline respondería 404 a su dueño legítimo (F-18-01b).

    Orden (NO basta resolver-antes-de-setear, que era el bug):
      1. setea ``client_id`` ANTES de resolver (RLS de ``projects`` es por
         client_id; sin esto la query es ciega),
      2. resuelve el proyecto server-side (RLS-gated),
      3. setea ``project_id`` para las lecturas project-scoped posteriores
         (``Project`` / ``ProjectPlan`` / ``WbsTask``).

    ``set_tenant_context`` usa SIEMPRE ``is_local=true`` (auto-reset al fin de
    transacción · ``is_local=false`` PROHIBIDO: bleed cross-tenant en la
    conexión del pool). Aquí NO hace falta re-set tras commit: el único
    ``db.commit()`` del endpoint es terminal (no hay lecturas project-scoped
    después · a diferencia de ``/chat/stream``).
    """
    await set_tenant_context(db, client_id=client_id)
    project_id = await _resolve_project_id(db, client_id)
    if project_id is not None:
        await set_tenant_context(db, project_id=project_id)
    return project_id


async def _emit_audit_log(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    client_id: uuid.UUID,
    user_email: str | None,
    payload: dict,
) -> None:
    """audit_log cliente.plan.viewed Sub-atom 5.A 3-way OR pattern."""
    await db.execute(text(
        "INSERT INTO audit_log (id, tabla, registro_id, accion, usuario, "
        "project_id, client_id, payload_new, timestamp) "
        "VALUES (gen_random_uuid(), 'project_plans', :pid, "
        "'cliente.plan.viewed', :user, :pid, :cid, :payload, now())"
    ), {
        "pid": str(project_id),
        "user": (user_email or "cliente")[:255],
        "cid": str(client_id),
        "payload": _json.dumps(payload),
    })


# ════════════════════════════════════════════════════════════════════
# GET /client-portal/plan · cliente READ-ONLY timeline
# ════════════════════════════════════════════════════════════════════


@router.get("", response_model=ClienteTimelineResponse)
async def get_cliente_plan_timeline(
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> ClienteTimelineResponse:
    """Cliente READ-ONLY view del plan adecuación · mirror admin timeline."""
    # F-18-01b · contexto RLS (client_id ANTES de resolver, project_id tras
    # resolver) en una sola puerta · sin esto el timeline es ciego a su propio
    # proyecto en prod → 404 al dueño legítimo (ver _resolve_project_id_scoped).
    project_id = await _resolve_project_id_scoped(db, user.client_id)
    if project_id is None:
        raise HTTPException(
            status_code=404, detail="No hay proyecto activo para este cliente.",
        )

    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    plan_row = (await db.execute(
        select(ProjectPlan).where(
            ProjectPlan.project_id == project_id,
            ProjectPlan.deleted_at.is_(None),
        ).order_by(ProjectPlan.version.desc()).limit(1),
    )).scalar_one_or_none()

    tasks: list[ClienteTimelineTask] = []
    milestones: list[ClienteTimelineMilestone] = []
    plan_start: date | None = None
    plan_end: date | None = None
    plan_estado: str | None = None

    if plan_row is not None:
        plan_start = plan_row.start_date
        plan_end = plan_row.end_date_estimated
        plan_estado = plan_row.estado

        rows = (await db.execute(
            select(WbsTask).where(
                WbsTask.project_plan_id == plan_row.id,
                WbsTask.deleted_at.is_(None),
            ).order_by(WbsTask.start_date.asc().nulls_last()),
        )).scalars().all()
        tasks = [ClienteTimelineTask.model_validate(t) for t in rows]

        raw_milestones = plan_row.milestones or {}
        milestone_list: list[Any]
        if isinstance(raw_milestones, list):
            milestone_list = raw_milestones
        elif isinstance(raw_milestones, dict):
            milestone_list = list(raw_milestones.get("items") or [])
        else:
            milestone_list = []
        for m in milestone_list:
            if not isinstance(m, dict):
                continue
            try:
                m_date = (
                    date.fromisoformat(m["date"])
                    if m.get("date") else None
                )
            except (ValueError, TypeError):
                m_date = None
            milestones.append(ClienteTimelineMilestone(
                name=str(m.get("name") or m.get("title") or "Hito"),
                date=m_date,
                type="plan_milestone",
                status=m.get("status"),
            ))

    if project.fecha_kickoff:
        milestones.append(ClienteTimelineMilestone(
            name="Inicio",
            date=project.fecha_kickoff,
            type="kickoff",
            status="completed" if project.fecha_kickoff <= date.today() else "pending",
        ))
    if project.fecha_objetivo_certificacion:
        milestones.append(ClienteTimelineMilestone(
            name="Certificación objetivo",
            date=project.fecha_objetivo_certificacion,
            type="objective",
            status="pending",
        ))
    if project.certified_at:
        milestones.append(ClienteTimelineMilestone(
            name="Certificado",
            date=project.certified_at,
            type="objective",
            status="completed",
        ))

    # Derive plan_start/end from tasks/milestones si plan sin fechas
    if plan_start is None and tasks:
        candidates = [t.start_date for t in tasks if t.start_date]
        plan_start = min(candidates) if candidates else None
    if plan_end is None and tasks:
        candidates = [t.end_date for t in tasks if t.end_date]
        plan_end = max(candidates) if candidates else None
    if plan_end is None and milestones:
        candidates = [m.date for m in milestones if m.date]
        plan_end = max(candidates) if candidates else None

    milestones.sort(key=lambda m: m.date or date.max)

    # audit_log emit · cliente.plan.viewed Sub-atom 5.A (best-effort)
    try:
        await _emit_audit_log(
            db,
            project_id=project_id,
            client_id=user.client_id,
            user_email=user.email,
            payload={
                "tasks_count": len(tasks),
                "milestones_count": len(milestones),
                "plan_estado": plan_estado,
                "cliente_tasks_count": sum(
                    1 for t in tasks if t.responsible in ("cliente", "mixto")
                ),
            },
        )
        await db.commit()
    except Exception:
        logger.exception("audit_log cliente.plan.viewed emit failed")

    return ClienteTimelineResponse(
        plan_start=plan_start,
        plan_end=plan_end,
        tasks=tasks,
        milestones=milestones,
        plan_estado=plan_estado,
        project_id=str(project_id),
    )
