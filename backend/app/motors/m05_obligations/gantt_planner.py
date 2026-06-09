"""Motor 5 -- Gantt Planner -- pure algorithm (no DB, no async).

Builds a ``GanttPlan`` from a flat list of obligation dicts by:
1. Topological-sorting on ``dependencias_template_ids``.
2. Scheduling each task on business days (Mon-Fri).
3. Chaining dependent tasks so each starts after its last predecessor.
"""
from __future__ import annotations

import uuid
from collections import defaultdict, deque
from datetime import date, timedelta
from math import ceil

from backend.app.motors.m05_obligations.gantt_types import (
    CircularDependencyError,
    GanttPlan,
    GanttTask,
)


# ── Business-day helpers ──────────────────────────────────────────────


def _next_workday(d: date) -> date:
    """Return *d* if it is a weekday (Mon-Fri), otherwise the next Monday."""
    weekday = d.weekday()
    if weekday < 5:
        return d
    # Saturday=5 -> +2, Sunday=6 -> +1
    return d + timedelta(days=7 - weekday)


def _add_workdays(start: date, days: int) -> date:
    """Add *days* business days to *start* (Mon-Fri calendar).

    ``_add_workdays(start, 0)`` returns *start* unchanged.
    """
    if days <= 0:
        return start
    current = start
    remaining = days
    while remaining > 0:
        current += timedelta(days=1)
        if current.weekday() < 5:
            remaining -= 1
    return current


# ── Topological sort (Kahn's algorithm) ──────────────────────────────


def _topological_sort(obligations_by_tid: dict[str, dict]) -> list[str]:
    """Return template_ids in dependency order (Kahn's algorithm).

    ``obligations_by_tid`` maps template_id -> obligation dict.
    Any predecessor not present in the dict (external dependency) is
    silently ignored.

    Raises ``CircularDependencyError`` when a cycle is detected.
    """
    in_degree: dict[str, int] = {tid: 0 for tid in obligations_by_tid}
    adjacency: dict[str, list[str]] = defaultdict(list)

    for tid, obl in obligations_by_tid.items():
        deps = obl.get("dependencias_template_ids") or []
        for dep_tid in deps:
            if dep_tid in obligations_by_tid:
                adjacency[dep_tid].append(tid)
                in_degree[tid] += 1

    queue: deque[str] = deque(
        tid for tid, deg in in_degree.items() if deg == 0
    )
    result: list[str] = []

    while queue:
        current = queue.popleft()
        result.append(current)
        for neighbour in adjacency[current]:
            in_degree[neighbour] -= 1
            if in_degree[neighbour] == 0:
                queue.append(neighbour)

    if len(result) != len(obligations_by_tid):
        remaining = set(obligations_by_tid) - set(result)
        raise CircularDependencyError(
            f"Cycle detected among template_ids: {remaining}"
        )

    return result


# ── Main planner ─────────────────────────────────────────────────────


def build_gantt_plan(
    project_id: uuid.UUID,
    obligations: list[dict],
    fecha_kickoff: date,
    dedicacion_horas_semana: float = 8.0,
) -> GanttPlan:
    """Build a ``GanttPlan`` from obligation dicts.

    Each dict is expected to have:
    - obligation_id (UUID)
    - template_id (str)
    - measure_code (str)
    - titulo (str)
    - modo_ejecucion (str | None)
    - estado (str | None)
    - esfuerzo_estimado (float)
    - dependencias_template_ids (list[str] | None)
    """
    if not obligations:
        return GanttPlan(
            project_id=project_id,
            fecha_kickoff=fecha_kickoff,
            fecha_fin_estimada=fecha_kickoff,
            duracion_total_dias_laborables=0,
            dedicacion_cliente_horas_semana=dedicacion_horas_semana,
            tareas=[],
        )

    # Index by template_id
    by_tid: dict[str, dict] = {
        obl["template_id"]: obl for obl in obligations
    }

    # Sort topologically
    sorted_tids = _topological_sort(by_tid)

    # Daily capacity: horas_semana / 5 working days
    daily_capacity = dedicacion_horas_semana / 5.0

    # Ensure kickoff falls on a workday
    kickoff = _next_workday(fecha_kickoff)

    # Schedule each task
    task_end_dates: dict[str, date] = {}
    tareas: list[GanttTask] = []

    for tid in sorted_tids:
        obl = by_tid[tid]
        esfuerzo = obl.get("esfuerzo_estimado") or 0.0
        duracion_dias = max(1, ceil(esfuerzo / daily_capacity))

        deps = obl.get("dependencias_template_ids") or []
        # Predecessors that are in the plan
        internal_deps = [d for d in deps if d in task_end_dates]

        if internal_deps:
            latest_pred_end = max(task_end_dates[d] for d in internal_deps)
            # Start the day after the latest predecessor ends (next workday)
            earliest = _next_workday(
                _add_workdays(latest_pred_end, 1)
            )
        else:
            earliest = kickoff

        fecha_inicio = earliest
        # Duration is inclusive: task spanning 1 day starts and ends same day
        fecha_fin = _add_workdays(fecha_inicio, duracion_dias - 1)

        task_end_dates[tid] = fecha_fin

        tareas.append(
            GanttTask(
                obligation_id=obl["obligation_id"],
                template_id=tid,
                measure_code=obl.get("measure_code", ""),
                titulo=obl.get("titulo", ""),
                modo_ejecucion=obl.get("modo_ejecucion"),
                estado=obl.get("estado"),
                esfuerzo_horas=esfuerzo,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                duracion_dias_laborables=duracion_dias,
                predecesores_template_ids=internal_deps,
            )
        )

    # Compute plan-level dates
    all_ends = [t.fecha_fin for t in tareas]
    fecha_fin_estimada = max(all_ends) if all_ends else kickoff

    # Total working days between kickoff and final end
    total_dias = 0
    cursor = kickoff
    while cursor <= fecha_fin_estimada:
        if cursor.weekday() < 5:
            total_dias += 1
        cursor += timedelta(days=1)

    return GanttPlan(
        project_id=project_id,
        fecha_kickoff=kickoff,
        fecha_fin_estimada=fecha_fin_estimada,
        duracion_total_dias_laborables=total_dias,
        dedicacion_cliente_horas_semana=dedicacion_horas_semana,
        tareas=tareas,
    )
