"""Dependency resolver · workflow cross-actor state machine (1.D.G v3.11).

Resuelve estados:
  blocked (prereq incomplete) → available (prereqs done · listo para start)
  → in_progress (started) → done (completed)

Propagation: cuando step completes · resuelve cuales otros steps
quedan unblocked y dispatcha events SSE.

Pure functions + service class wrap async DB.

Sostiene ADR-025 (NO new tables · usa client_tasks existing + view composer).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Literal, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.sse_dispatcher import sse_dispatcher
from backend.app.motors.m21_portal_cliente.models_tasks import ClientTask
from backend.app.motors.m21_portal_cliente.task_templates_loader import (
    PrimaryActor,
    TaskTemplate,
    get_enriched_steps_for_project,
    get_template_by_id,
    resolve_primary_actor,
)
from backend.app.motors.m_workflow_engine.engine import load_project_dims


StepStatus = Literal["blocked", "available", "in_progress", "done"]
"""Estados state machine cross-actor (1.D.G v3.11).

- blocked: prerequisite_template_ids not all done · cliente/admin cannot start yet
- available: prereqs satisfied · ready to start
- in_progress: ClientTask.status == "in_progress"
- done: ClientTask.status in {"done", "completed"}
"""

# Backward-compat · engine históricamente compara "completed" · task_service "done"
TERMINAL_DONE_STATUSES: frozenset[str] = frozenset({"done", "completed"})


@dataclass(frozen=True)
class DependencyResolution:
    """Resultado resolver_step_status."""

    template_id: str
    status: StepStatus
    primary_actor: PrimaryActor
    missing_prerequisites: list[str]
    blocker_reason: Optional[str]


def _format_blocker_reason(
    missing_template_ids: list[str],
    missing_primary_actors: list[PrimaryActor],
) -> str:
    """Friendly text per portal · expected_actor based.

    Si missing es cliente actor → "Esperando cliente complete: {step_title}"
    Si missing es admin actor → "Esperando Marcos termine: {step_title}"
    Si mezcla → "Bloqueado por X pasos previos pendientes"
    """
    if not missing_template_ids:
        return ""
    if len(missing_template_ids) == 1:
        tmpl = get_template_by_id(missing_template_ids[0])
        title = tmpl.title if tmpl else missing_template_ids[0]
        actor = missing_primary_actors[0] if missing_primary_actors else "admin"
        if actor == "cliente":
            return f"Esperando cliente complete: {title}"
        if actor == "admin":
            return f"Esperando Marcos termine: {title}"
        return f"Esperando proceso interno: {title}"
    # Mixed multi-prereq
    return f"Bloqueado por {len(missing_template_ids)} pasos previos pendientes"


def check_dependencies_satisfied(
    template: TaskTemplate,
    tasks_by_template: dict[str, ClientTask],
) -> tuple[bool, list[str]]:
    """Returns (satisfied, missing_prerequisite_template_ids).

    Pure function · NO DB · usa map preloaded por engine view composer.
    """
    if not template.prerequisite_template_ids:
        return True, []
    missing: list[str] = []
    for prereq_id in template.prerequisite_template_ids:
        task = tasks_by_template.get(prereq_id)
        if task is None or task.status not in TERMINAL_DONE_STATUSES:
            missing.append(prereq_id)
    return len(missing) == 0, missing


def resolve_step_status(
    template: TaskTemplate,
    tasks_by_template: dict[str, ClientTask],
) -> DependencyResolution:
    """Resuelve estado state machine cross-actor para un template.

    Pure function · cruza prereqs + existing client_task state.
    """
    primary_actor = resolve_primary_actor(template)
    task = tasks_by_template.get(template.id)

    # Step already done · final state
    if task and task.status in TERMINAL_DONE_STATUSES:
        return DependencyResolution(
            template_id=template.id,
            status="done",
            primary_actor=primary_actor,
            missing_prerequisites=[],
            blocker_reason=None,
        )

    # Step in_progress · started but not completed
    if task and task.status == "in_progress":
        return DependencyResolution(
            template_id=template.id,
            status="in_progress",
            primary_actor=primary_actor,
            missing_prerequisites=[],
            blocker_reason=None,
        )

    # Check prerequisites
    satisfied, missing = check_dependencies_satisfied(template, tasks_by_template)
    if not satisfied:
        missing_actors: list[PrimaryActor] = []
        for prereq_id in missing:
            prereq_tmpl = get_template_by_id(prereq_id)
            if prereq_tmpl:
                missing_actors.append(resolve_primary_actor(prereq_tmpl))
            else:
                missing_actors.append("admin")
        blocker = _format_blocker_reason(missing, missing_actors)
        return DependencyResolution(
            template_id=template.id,
            status="blocked",
            primary_actor=primary_actor,
            missing_prerequisites=missing,
            blocker_reason=blocker,
        )

    # Prereqs satisfied · ready
    return DependencyResolution(
        template_id=template.id,
        status="available",
        primary_actor=primary_actor,
        missing_prerequisites=[],
        blocker_reason=None,
    )


async def _load_tasks_by_template(
    db: AsyncSession, project_id: uuid.UUID,
) -> dict[str, ClientTask]:
    result = await db.execute(
        select(ClientTask).where(
            ClientTask.project_id == project_id,
            ClientTask.deleted_at.is_(None),
        )
    )
    return {t.template_id: t for t in result.scalars().all()}


class DependencyResolverService:
    """Service wrap async DB + propagation logic + SSE dispatch."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def resolve_project_states(
        self, project_id: uuid.UUID,
    ) -> dict[str, DependencyResolution]:
        """Resuelve estados todos templates aplicables al project.

        Returns dict[template_id → DependencyResolution].
        """
        dims = await load_project_dims(self.db, project_id)
        applicable = get_enriched_steps_for_project(project_dims=dims)
        tasks_map = await _load_tasks_by_template(self.db, project_id)
        return {
            tmpl.id: resolve_step_status(tmpl, tasks_map)
            for tmpl in applicable
        }

    async def propagate_unblock(  # noqa: C901
        self,
        project_id: uuid.UUID,
        completed_template_id: str,
    ) -> list[DependencyResolution]:
        """Cuando step completes · returns list newly_unblocked steps.

        Dispatcha SSE step_unblocked event per unblocked step.
        Caller debe llamar después de transition → "done".
        """
        dims = await load_project_dims(self.db, project_id)
        applicable = get_enriched_steps_for_project(project_dims=dims)
        tasks_map = await _load_tasks_by_template(self.db, project_id)

        newly_unblocked: list[DependencyResolution] = []
        for tmpl in applicable:
            if completed_template_id not in tmpl.prerequisite_template_ids:
                continue
            resolution = resolve_step_status(tmpl, tasks_map)
            if resolution.status == "available":
                newly_unblocked.append(resolution)

        # Dispatch SSE events for downstream listeners + auto-notifications
        for unblocked in newly_unblocked:
            tmpl = get_template_by_id(unblocked.template_id)
            await dispatch_step_unblocked(
                project_id=project_id,
                template_id=unblocked.template_id,
                primary_actor=unblocked.primary_actor,
                unblocked_by_template_id=completed_template_id,
                step_title=tmpl.title if tmpl else unblocked.template_id,
                estimated_days_to_complete=(
                    tmpl.estimated_days_to_complete or tmpl.estimated_days
                    if tmpl else None
                ),
            )

            # 1.D.G.F · auto-trigger notifications per primary_actor
            if tmpl is not None and (
                tmpl.notify_on_unblock if tmpl.notify_on_unblock is not None else True
            ):
                await _maybe_dispatch_notifications(
                    self.db, project_id, tmpl, unblocked.primary_actor,
                )

        return newly_unblocked


# ============= SSE event dispatchers (1.D.G v3.11) =============


async def dispatch_step_completed(
    project_id: uuid.UUID,
    template_id: str,
    primary_actor: PrimaryActor,
    step_title: str,
) -> None:
    """SSE event · step transitioned to done."""
    await sse_dispatcher.dispatch(
        channel=f"project:{project_id}",
        event_type="step_completed",
        data={
            "template_id": template_id,
            "primary_actor": primary_actor,
            "step_title": step_title,
        },
    )


async def dispatch_step_unblocked(
    project_id: uuid.UUID,
    template_id: str,
    primary_actor: PrimaryActor,
    unblocked_by_template_id: str,
    step_title: str,
    estimated_days_to_complete: int | None,
) -> None:
    """SSE event · step prerequisites satisfied · ready to start."""
    await sse_dispatcher.dispatch(
        channel=f"project:{project_id}",
        event_type="step_unblocked",
        data={
            "template_id": template_id,
            "primary_actor": primary_actor,
            "unblocked_by_template_id": unblocked_by_template_id,
            "step_title": step_title,
            "estimated_days_to_complete": estimated_days_to_complete,
        },
    )


async def _maybe_dispatch_notifications(
    db: AsyncSession,
    project_id: uuid.UUID,
    template: TaskTemplate,
    primary_actor: PrimaryActor,
) -> None:
    """1.D.G.F · auto-dispatch notifications cliente/admin per actor.

    Graceful · ImportError o failure NO rompe propagation chain.
    Notification module se carga dinámicamente · permite test deferral.
    """
    try:
        from backend.app.notifications.workflow_step_notifications import (
            send_admin_step_completed_notification,
            send_client_unblock_notification,
        )
    except ImportError:
        import logging
        logging.getLogger(__name__).warning(
            "workflow_step_notifications module unavailable · skip dispatch",
        )
        return

    try:
        if primary_actor == "cliente":
            await send_client_unblock_notification(
                db=db, project_id=project_id, template=template,
            )
        elif primary_actor == "admin":
            await send_admin_step_completed_notification(
                db=db, project_id=project_id, template=template,
            )
    except Exception as exc:  # noqa: BLE001
        import logging
        logging.getLogger(__name__).warning(
            "auto-notification dispatch failed · project=%s template=%s err=%s",
            project_id, template.id, exc,
        )


async def dispatch_step_blocked(
    project_id: uuid.UUID,
    template_id: str,
    primary_actor: PrimaryActor,
    blocker_reason: str,
    expected_actor: PrimaryActor,
) -> None:
    """SSE event · step explícitamente blocked (raro · usado para audit)."""
    await sse_dispatcher.dispatch(
        channel=f"project:{project_id}",
        event_type="step_blocked",
        data={
            "template_id": template_id,
            "primary_actor": primary_actor,
            "blocker_reason": blocker_reason,
            "expected_actor": expected_actor,
        },
    )
