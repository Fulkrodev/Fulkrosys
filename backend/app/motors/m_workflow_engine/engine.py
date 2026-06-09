"""m_workflow_engine engine · pure functions view composer.

Sub-atom 1.C.D.A v3.8 · composer cross-data NO storage propio (ADR-025).
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.core import Project
from backend.app.motors.m21_portal_cliente.models_tasks import ClientTask
from backend.app.motors.m21_portal_cliente.task_templates_loader import (
    PrimaryActor,
    TaskTemplate,
    apply_archetype_variant,
    get_enriched_steps_for_project,
)


# ==================================================================
# Schemas
# ==================================================================


class EnrichedStepState(BaseModel):
    """Estado enriched de un sub-paso cross-data (template + task_state)."""

    # Identidad
    template_id: str
    phase: str
    order_within_phase: int | None = None
    title: str

    # Datos enriched template
    description_detailed_es: str | None = None
    rationale_es: str | None = None
    cta_label: str | None = None
    cta_url: str | None = None
    priority: int = 0
    estimated_days: int | None = None
    deliverable_codes: list[str] = Field(default_factory=list)
    prerequisite_template_ids: list[str] = Field(default_factory=list)
    actors: list[str] = Field(default_factory=list)
    completion_criteria_detailed: list[str] = Field(default_factory=list)
    adaptation_notes_es: str | None = None
    tooltips_ens: dict[str, str] = Field(default_factory=dict)
    is_enriched: bool = False

    # Adaptación archetype variant (si aplica)
    variant_extra_focus: str | None = None
    variant_reference_norms: list[str] = Field(default_factory=list)

    # Estado derived client_task (si existe)
    task_id: uuid.UUID | None = None
    status: str = "not_started"  # not_started | pending | started | completed | blocked
    due_date_iso: str | None = None
    started_at_iso: str | None = None
    completed_at_iso: str | None = None
    blocked_reason: str | None = None

    # Urgencia computed (basado en estimated_days + horas_cliente_semana + urgencia_certificacion)
    urgency_score: int = 0  # 0-100 · más alto = más urgente

    # ============= 1.D.G v3.11 cross-actor state machine =============
    primary_actor: PrimaryActor = "admin"
    """admin · cliente · system · quien debe avanzar el step."""

    dependency_status: str = "available"
    """blocked · available · in_progress · done (cross-actor state machine)."""

    missing_prerequisites: list[str] = Field(default_factory=list)
    """template_ids prereqs incomplete (si dependency_status == "blocked")."""

    estimated_days_to_complete: int | None = None
    """Días estimados para mostrar "Marcos prepara X · estará listo en N días" en UI cliente."""

    model_config = ConfigDict(extra="allow")


# ==================================================================
# Urgency computation (helper)
# ==================================================================


_URGENCIA_BOOST = {
    "urgent_30d": 40,
    "1m": 30,
    "3m": 20,
    "6m": 10,
    "no_urge": 0,
}

_HORAS_FACTOR = {
    "lt5h": 1.6,
    "5_15h": 1.0,
    "15_40h": 0.7,
    "full_time": 0.5,
}


def _compute_urgency_score(
    template: TaskTemplate,
    project_dims: dict[str, Any],
    task_status: str,
) -> int:
    """Score 0-100 · combine template priority + project urgencia + cliente horas.

    Pure function · testeable.
    """
    if task_status == "completed":
        return 0

    base = template.priority * 5  # priority 0-10 → 0-50

    # Urgencia boost
    urgencia = project_dims.get("urgencia_certificacion", "6m")
    base += _URGENCIA_BOOST.get(urgencia, 0)

    # Horas semana cliente factor (less hours → more urgent)
    horas = project_dims.get("horas_cliente_semana", "5_15h")
    factor = _HORAS_FACTOR.get(horas, 1.0)
    if template.estimated_days:
        # Estimated days adjusted by client capacity
        adjusted_days = int(template.estimated_days * factor)
        if adjusted_days <= 7:
            base += 15
        elif adjusted_days <= 14:
            base += 8

    # Pending without start gets small boost vs not_started
    if task_status == "pending":
        base += 5

    return min(base, 100)


def _adapt_estimated_days(
    template: TaskTemplate,
    project_dims: dict[str, Any],
) -> int | None:
    """Adjust estimated_days segun horas_cliente_semana."""
    if template.estimated_days is None:
        return None
    horas = project_dims.get("horas_cliente_semana", "5_15h")
    factor = _HORAS_FACTOR.get(horas, 1.0)
    return int(template.estimated_days * factor)


# ==================================================================
# Project dims loader
# ==================================================================


async def load_project_dims(
    db: AsyncSession, project_id: uuid.UUID,
) -> dict[str, Any]:
    """Lee 19 dims del proyecto en dict (NO Pydantic · simple dict para engine)."""
    project = await db.get(Project, project_id)
    if project is None:
        raise ValueError(f"Project {project_id} not found")
    return {
        # 3 existing
        "categoria_objetivo": project.categoria_objetivo,
        "archetype": project.archetype,
        "fase": project.fase,
        # 16 nuevas (1.C.D.A.0 v3.8)
        "tamano_empleados": project.tamano_empleados,
        "madurez_ens_actual": project.madurez_ens_actual,
        "geografia_operacion": project.geografia_operacion,
        "procesa_datos_sensibles_rgpd9": project.procesa_datos_sensibles_rgpd9,
        "aplica_nis2": project.aplica_nis2,
        "aplica_dora": project.aplica_dora,
        "aplica_ai_act": project.aplica_ai_act,
        "dpo_designado": project.dpo_designado,
        "arquitectura_sistemas": project.arquitectura_sistemas,
        "multi_tenancy": project.multi_tenancy,
        "equipo_ti_tamano": project.equipo_ti_tamano,
        "certificaciones_previas": list(project.certificaciones_previas or []),
        "urgencia_certificacion": project.urgencia_certificacion,
        "presupuesto_disponible": project.presupuesto_disponible,
        "compromiso_interno": project.compromiso_interno,
        "horas_cliente_semana": project.horas_cliente_semana,
    }


# ==================================================================
# Core compute · the view composer
# ==================================================================


async def compute_steps_for_project(
    db: AsyncSession,
    project_id: uuid.UUID,
    phase_filter: Optional[str] = None,
) -> list[EnrichedStepState]:
    """View composer · cruza enriched template catalog + project + client_tasks.

    Returns ordered list[EnrichedStepState] · phase canonical × order_within × priority.
    """
    # 1. Load project 19 dims
    dims = await load_project_dims(db, project_id)

    # 2. Filter templates aplicables al proyecto (19 dims filter)
    applicable_templates = get_enriched_steps_for_project(
        project_dims=dims, phase_filter=phase_filter,
    )

    # 3. Load client_tasks existentes para este proyecto (map template_id → ClientTask)
    tasks_q = await db.execute(
        select(ClientTask).where(
            ClientTask.project_id == project_id,
            ClientTask.deleted_at.is_(None),
        )
    )
    tasks_by_template: dict[str, ClientTask] = {
        t.template_id: t for t in tasks_q.scalars().all()
    }

    # 4. Compose enriched state per template
    archetype = dims.get("archetype")
    result: list[EnrichedStepState] = []

    # 1.D.G v3.11 · resolve cross-actor dependencies state machine
    from backend.app.motors.m_workflow_engine.dependency_resolver_service import (
        resolve_step_status,
    )

    for tmpl in applicable_templates:
        # Apply archetype variant overlay
        variant_data = apply_archetype_variant(tmpl, archetype)

        # Lookup task state
        task = tasks_by_template.get(tmpl.id)
        task_status = task.status if task else "not_started"

        # Compute urgency + adapted estimated_days
        urgency = _compute_urgency_score(tmpl, dims, task_status)
        adapted_days = _adapt_estimated_days(tmpl, dims)

        # 1.D.G · resolve dependency state machine cross-actor
        resolution = resolve_step_status(tmpl, tasks_by_template)
        derived_blocker_reason = (
            task.blocked_reason if task and task.blocked_reason
            else resolution.blocker_reason
        )

        state = EnrichedStepState(
            template_id=tmpl.id,
            phase=tmpl.phase,
            order_within_phase=tmpl.order_within_phase,
            title=tmpl.title,
            description_detailed_es=tmpl.description_detailed_es or tmpl.description,
            rationale_es=tmpl.rationale_es,
            cta_label=tmpl.cta_label,
            cta_url=tmpl.cta_url,
            priority=tmpl.priority,
            estimated_days=adapted_days,
            deliverable_codes=tmpl.deliverable_codes,
            prerequisite_template_ids=tmpl.prerequisite_template_ids,
            actors=variant_data.get("actors", tmpl.actors),
            completion_criteria_detailed=tmpl.completion_criteria_detailed,
            adaptation_notes_es=tmpl.adaptation_notes_es,
            tooltips_ens=tmpl.tooltips_ens,
            is_enriched=tmpl.is_enriched,
            variant_extra_focus=variant_data.get("_variant_extra_focus"),
            variant_reference_norms=variant_data.get(
                "_variant_reference_norms", [],
            ),
            task_id=task.id if task else None,
            status=task_status,
            due_date_iso=task.due_date.isoformat() if task and task.due_date else None,
            started_at_iso=(
                task.started_at.isoformat() if task and task.started_at else None
            ),
            completed_at_iso=(
                task.completed_at.isoformat() if task and task.completed_at else None
            ),
            blocked_reason=derived_blocker_reason,
            urgency_score=urgency,
            primary_actor=resolution.primary_actor,
            dependency_status=resolution.status,
            missing_prerequisites=list(resolution.missing_prerequisites),
            estimated_days_to_complete=tmpl.estimated_days_to_complete or adapted_days,
        )
        result.append(state)

    return result


# ==================================================================
# Aggregates (used by progress / timeline / current-step endpoints)
# ==================================================================


async def compute_progress_for_project(
    db: AsyncSession, project_id: uuid.UUID,
) -> dict[str, Any]:
    """Returns dict global + per-phase progress %."""
    steps = await compute_steps_for_project(db, project_id)
    if not steps:
        return {
            "global_pct": 0,
            "global_completed": 0,
            "global_total": 0,
            "per_phase": {},
        }

    completed_global = sum(1 for s in steps if s.status == "completed")
    total_global = len(steps)
    pct_global = int(round((completed_global / total_global) * 100)) if total_global else 0

    per_phase: dict[str, dict[str, int]] = {}
    for s in steps:
        if s.phase not in per_phase:
            per_phase[s.phase] = {"completed": 0, "total": 0}
        per_phase[s.phase]["total"] += 1
        if s.status == "completed":
            per_phase[s.phase]["completed"] += 1

    for phase, counts in per_phase.items():
        counts["pct"] = int(
            round((counts["completed"] / counts["total"]) * 100)
        ) if counts["total"] else 0

    return {
        "global_pct": pct_global,
        "global_completed": completed_global,
        "global_total": total_global,
        "per_phase": per_phase,
    }


async def compute_current_step_for_project(
    db: AsyncSession, project_id: uuid.UUID,
) -> EnrichedStepState | None:
    """Returns siguiente paso pendiente most-urgent · None si todo completado."""
    steps = await compute_steps_for_project(db, project_id)
    pending = [s for s in steps if s.status != "completed"]
    if not pending:
        return None
    # Sort by urgency desc · take first
    pending.sort(key=lambda s: -s.urgency_score)
    return pending[0]
