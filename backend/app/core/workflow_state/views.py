"""UI views composition · funciones public-facing (workflow_state refactor H1).

Compone outputs para frontend cliente UI desde building blocks:
``get_current_phase`` (phase.py) + ``_calculate_phase_items_done`` (items.py)
+ ``_TASK_SIGNAL_CHECKERS`` (signals.py).

Funciones públicas:
    get_next_actions(project_id, limit)   → list[NextAction]
    get_phase_progress(project_id, phase) → PhaseProgress
    get_phase_tasks(project_id, phase)    → list[TaskItem]
    verify_client_owns_project(...)       → bool (RBAC cross-pool helper)
    get_workflow_roadmap(project_id)      → WorkflowRoadmap (8 fases)
"""
from __future__ import annotations

import logging
import uuid

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.workflow_phase import WorkflowPhase
from backend.app.core.workflow_schemas import (
    NextAction,
    PhaseProgress,
    PhaseRoadmapEntry,
    TaskItem,
    WorkflowRoadmap,
)
from backend.app.core.workflow_state.items import _calculate_phase_items_done
from backend.app.core.workflow_state.phase import get_current_phase
from backend.app.core.workflow_state.signals import _TASK_SIGNAL_CHECKERS
from backend.app.core.workflow_templates import (
    ACTION_TEMPLATES,
    TASK_TEMPLATES,
    TaskTemplateDef,
)

log = logging.getLogger(__name__)


async def get_next_actions(
    session: AsyncSession,
    project_id: uuid.UUID,
    limit: int = 5,
) -> list[NextAction]:
    """Lista priorizada acciones pendientes para fase actual del proyecto.

    Strategy:
    1. ``get_current_phase`` para identificar fase
    2. Lookup ``ACTION_TEMPLATES`` per fase (Python constants ADR-026)
    3. Top ``limit`` ordenadas por priority

    Filtros completion per acción quedan delegados al frontend (cliente
    UI marca acción completada según endpoint específico). Pattern simple
    runtime sin queries adicionales.
    """
    current = await get_current_phase(session, project_id)
    templates = ACTION_TEMPLATES.get(current, [])

    sorted_templates = sorted(templates, key=lambda t: t.priority)[:limit]

    return [
        NextAction(
            action_id=t.action_id,
            label=t.label,
            motor=t.motor,
            endpoint=t.endpoint,
            priority=t.priority,
            estimated_minutes=t.estimated_minutes,
        )
        for t in sorted_templates
    ]


async def get_phase_progress(
    session: AsyncSession,
    project_id: uuid.UUID,
    phase: WorkflowPhase,
) -> PhaseProgress:
    """Métricas progreso fase específica del proyecto.

    Strategy ADR-026 + W1 calibracion:
    1. Resolve fase actual del proyecto via ``get_current_phase``
    2. Comparar orden vs ``phase`` solicitada:
       - phase < current  → status='done', pct=100, items_done=total_items
       - phase == current → status derivado de query motor real (W1):
         items_done refleja completion real, no heuristica 50%
       - phase > current  → status='pending', pct=0, items_done=0

    W1 ISSUE: la heuristica "50% midpoint" para la fase actual era enganosa
    a UI cliente (pct fijo independiente de progreso real). Ahora la fase
    actual ejecuta query motor especifica per fase que cuenta items
    completados reales basados en data motors. Status derivado de ratio:
    items_done == 0 → 'pending', == total → 'done', en medio → 'in_progress'.

    Fases pasadas/futuras conservan comportamiento simple (compat W3:
    si la fase ya cambio, projects.fase reflejara el avance/regresion via
    los phase_changed events propios cuando trigger automatico se active).
    """
    current = await get_current_phase(session, project_id)
    ordered = WorkflowPhase.ordered()
    current_idx = ordered.index(current)
    phase_idx = ordered.index(phase)

    total_items = len(TASK_TEMPLATES.get(phase, []))
    if total_items == 0:
        total_items = 1  # safety anti-divide-by-zero (fase sin tasks definidas)

    if phase_idx < current_idx:
        # Fase pasada · asumida done
        return PhaseProgress(
            phase=phase,
            pct_completed=100.0,
            total_items=total_items,
            items_done=total_items,
            status="done",
        )
    if phase_idx > current_idx:
        # Fase futura · pending
        return PhaseProgress(
            phase=phase,
            pct_completed=0.0,
            total_items=total_items,
            items_done=0,
            status="pending",
        )

    # phase == current_phase · query motor real (W1 calibracion)
    items_done = await _calculate_phase_items_done(
        session, project_id, phase
    )
    items_done = min(items_done, total_items)  # safety cap

    if items_done == 0:
        derived_status = "pending"
    elif items_done == total_items:
        derived_status = "done"
    else:
        derived_status = "in_progress"

    return PhaseProgress(
        phase=phase,
        pct_completed=round((items_done / total_items) * 100.0, 1),
        total_items=total_items,
        items_done=items_done,
        status=derived_status,
    )


async def get_phase_tasks(
    session: AsyncSession,
    project_id: uuid.UUID,
    phase: WorkflowPhase,
) -> list[TaskItem]:
    """Lista tasks expected per fase con status real per task (W2 calibracion).

    W2 ISSUE: la heuristica '50% midpoint' para fase actual + 'todas done para
    fase pasada / todas pending para fase futura' era enganosa a UI cliente
    (checkboxes verdes sin completion real, o pendientes sin actividad real).

    Refactor:
    - Cada task tiene ``completion_signal`` mapeado a query SQL motor real.
    - Si signal=None: status='manual_tracking' (UI cliente honesto · depende
      de Marcos confirmando manualmente).
    - Si signal definido: ejecuta la query · status='completed' o 'pending'.
    - Heuristica 'in_progress' eliminada: una task o esta done o no.

    Nota: las queries se ejecutan en serie · si performance preocupa con
    proyectos muy activos, se puede batch en una sola query agregada
    (TODO post-deploy si feedback latencia).
    """
    templates = TASK_TEMPLATES.get(phase, [])

    items: list[TaskItem] = []
    for t in sorted(templates, key=lambda x: x.ord):
        status = await _resolve_task_status(session, project_id, t)
        items.append(
            TaskItem(
                label=t.label,
                motor=t.motor,
                priority=t.priority,
                ord=t.ord,
                status=status,
            )
        )
    return items


async def _resolve_task_status(
    session: AsyncSession,
    project_id: uuid.UUID,
    task: TaskTemplateDef,
) -> str:
    """Devuelve status real para una task individual (W2 calibracion).

    Returns:
        'completed' si signal positivo, 'pending' si no, 'manual_tracking'
        si la task no es instrumentable (signal=None).
    """
    if task.completion_signal is None:
        return "manual_tracking"

    checker = _TASK_SIGNAL_CHECKERS.get(task.completion_signal)
    if checker is None:
        # Defensa: signal definido en template pero sin checker registrado.
        log.warning(
            "workflow_state: unknown completion_signal=%s task=%s",
            task.completion_signal,
            task.label,
        )
        return "manual_tracking"

    is_done = await checker(session, project_id)
    return "completed" if is_done else "pending"


async def verify_client_owns_project(
    session: AsyncSession,
    project_id: uuid.UUID,
    client_id: uuid.UUID,
) -> bool:
    """True si project.client_id matches client_id (cross-pool RBAC check).

    Helper para endpoints ``/portal/workflow/*`` (TODO-CLIENT-WORKFLOW-VIEW
    RESOLVED durante FASE 8). Cliente solo ve workflow de SUS proyectos.
    """
    row = await session.execute(
        sa_text(
            "SELECT 1 FROM projects "
            "WHERE id = :pid AND client_id = :cid AND deleted_at IS NULL"
        ),
        {"pid": str(project_id), "cid": str(client_id)},
    )
    return row.scalar_one_or_none() is not None


async def get_workflow_roadmap(
    session: AsyncSession,
    project_id: uuid.UUID,
) -> WorkflowRoadmap:
    """Roadmap completo proyecto · 8 fases con estados (response /roadmap)."""
    current = await get_current_phase(session, project_id)
    entries: list[PhaseRoadmapEntry] = []
    for phase in WorkflowPhase.ordered():
        progress = await get_phase_progress(session, project_id, phase)
        entries.append(
            PhaseRoadmapEntry(
                phase=phase,
                status=progress.status,
                pct_completed=progress.pct_completed,
                is_current=(phase == current),
            )
        )
    return WorkflowRoadmap(
        project_id=str(project_id),
        current_phase=current,
        phases=entries,
    )
