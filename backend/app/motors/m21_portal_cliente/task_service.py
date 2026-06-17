"""ClientTaskService · workspace tasks generator + lifecycle (ADR-038
SAN-D MB-14.3).

Genera tareas auto-applicable cuando workflow phase del proyecto
cambia. Tareas idempotentes vía UNIQUE (project_id, template_id) ·
re-generación skip ya existing.

Lifecycle: pending → in_progress → done | blocked.

Endpoints expuestos en `task_api.py`:
- GET  /client-portal/tasks               · cliente lista tasks current project
- POST /client-portal/tasks/{id}/start
- POST /client-portal/tasks/{id}/complete
- POST /client-portal/tasks/{id}/block    · body {reason}
- POST /admin/projects/{id}/tasks/regenerate · admin force regen
"""
from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

import json as _json

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.core import Project
from backend.app.motors.m21_portal_cliente.models_tasks import ClientTask
from backend.app.motors.m21_portal_cliente.task_templates_loader import (
    get_template_by_id,
    get_templates_for_phase,
    resolve_primary_actor,
)


VALID_STATUSES = {"pending", "in_progress", "blocked", "done"}


class TaskError(Exception):
    pass


class ClientTaskService:
    """Service · genera tareas + lifecycle transitions."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def regenerate_for_project(
        self, project_id: UUID,
    ) -> dict:
        """Regenerate tareas aplicables fase actual proyecto.

        Idempotente · skip si template_id already exists para project.
        """
        project = await self.db.get(Project, project_id)
        if not project:
            return {"created": 0, "skipped": 0, "error": "project_not_found"}

        categoria = (project.categoria_objetivo or "BASICA").upper()
        archetype = project.archetype
        phase = project.fase or "pre_venta"

        applicable = get_templates_for_phase(
            phase=phase, categoria=categoria, archetype=archetype,
        )

        existing_template_ids = set(
            (
                await self.db.execute(
                    select(ClientTask.template_id)
                    .where(ClientTask.project_id == project_id)
                    .where(ClientTask.deleted_at.is_(None))
                )
            ).scalars().all(),
        )

        created = 0
        skipped = 0
        for tmpl in applicable:
            if tmpl.id in existing_template_ids:
                skipped += 1
                continue

            due_date_val: Optional[date] = None
            if tmpl.estimated_days:
                due_date_val = (
                    datetime.now(timezone.utc).date()
                    + timedelta(days=tmpl.estimated_days)
                )

            task = ClientTask(
                project_id=project_id,
                template_id=tmpl.id,
                phase=tmpl.phase,
                title=tmpl.title,
                description=tmpl.description,
                cta_label=tmpl.cta_label,
                cta_url=tmpl.cta_url,
                expected_evidence_type=tmpl.expected_evidence_type,
                expected_evidence_count=tmpl.expected_evidence_count,
                priority=tmpl.priority,
                status="pending",
                due_date=due_date_val,
            )
            self.db.add(task)
            created += 1

        await self.db.flush()
        return {"created": created, "skipped": skipped}

    async def list_tasks(
        self,
        project_id: UUID,
        status: Optional[str] = None,
    ) -> list[ClientTask]:
        query = (
            select(ClientTask)
            .where(ClientTask.project_id == project_id)
            .where(ClientTask.deleted_at.is_(None))
            .order_by(
                ClientTask.priority.desc(),
                ClientTask.created_at.asc(),
            )
        )
        if status:
            query = query.where(ClientTask.status == status)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def transition(
        self,
        task_id: UUID,
        new_status: str,
        blocked_reason: Optional[str] = None,
        enforce_prereqs: bool = True,
        client_initiated: bool = False,
        expected_project_id: Optional[UUID] = None,
    ) -> ClientTask:
        """Lifecycle transition · 1.D.G v3.11 enforces prereqs en in_progress.

        Args:
            enforce_prereqs: si True (default) bloquea transition a "in_progress"
                cuando prerequisite_template_ids del template no están todos done.
                Útil bypass tests · admin override.
            client_initiated: HIGH #6 · si True (llamada desde el portal cliente)
                rechaza transiciones sobre tareas cuyo primary_actor != 'cliente'
                (las gestiona Fulkro · cliente-mínimo). approve_plan es flujo aparte.
            expected_project_id: HIGH #6 · si se pasa, verifica que la tarea
                pertenece a ese proyecto (guard cross-proyecto · defensa adicional).
        """
        if new_status not in VALID_STATUSES:
            raise TaskError(
                f"Invalid status: {new_status}. Allowed: {VALID_STATUSES}",
            )

        task = await self.db.get(ClientTask, task_id)
        if not task:
            raise TaskError("Task not found")

        # HIGH #6 · guard cross-proyecto (la tarea debe ser del proyecto del cliente).
        if expected_project_id is not None and task.project_id != expected_project_id:
            raise TaskError("Task not found")

        # HIGH #6 · guard de actor · el cliente solo opera SUS tareas (cliente-mínimo).
        # Las tareas admin las gestiona Fulkro · el cliente las VE (read-only) pero
        # no puede marcarlas hechas/empezadas/bloqueadas.
        if client_initiated:
            tmpl_actor = get_template_by_id(task.template_id)
            if tmpl_actor and resolve_primary_actor(tmpl_actor) != "cliente":
                raise TaskError(
                    "Esta tarea la gestiona Fulkro · no requiere acción del cliente.",
                )

        # 1.D.G · state machine guard · check prereqs en start
        # FULKRO_SKIP_WORKFLOW_GATES=1 bypass (testing existing motors aislados)
        if (
            new_status == "in_progress"
            and enforce_prereqs
            and os.environ.get("FULKRO_SKIP_WORKFLOW_GATES") != "1"
        ):
            tmpl = get_template_by_id(task.template_id)
            if tmpl and tmpl.prerequisite_template_ids:
                from backend.app.motors.m_workflow_engine.dependency_resolver_service import (
                    check_dependencies_satisfied,
                )
                # Load project tasks
                result = await self.db.execute(
                    select(ClientTask).where(
                        ClientTask.project_id == task.project_id,
                        ClientTask.deleted_at.is_(None),
                    )
                )
                tasks_map = {
                    t.template_id: t for t in result.scalars().all()
                }
                satisfied, missing = check_dependencies_satisfied(tmpl, tasks_map)
                if not satisfied:
                    missing_titles = [
                        (get_template_by_id(mid).title if get_template_by_id(mid) else mid)
                        for mid in missing
                    ]
                    raise TaskError(
                        f"Step bloqueado · prerequisitos pendientes: {', '.join(missing_titles)}"
                    )

        now = datetime.now(timezone.utc)
        previous_status = task.status
        task.status = new_status

        if new_status == "in_progress" and task.started_at is None:
            task.started_at = now
        elif new_status == "done":
            task.completed_at = now
            if task.started_at is None:
                task.started_at = now
            # Clear blocked_reason on completion
            task.blocked_reason = None
        elif new_status == "blocked":
            task.blocked_reason = blocked_reason or task.blocked_reason

        await self.db.flush()

        # 1.D.G · SSE dispatch + propagation on done transition
        if new_status == "done" and previous_status not in {"done", "completed"}:
            await self._dispatch_done_and_propagate(task)

        return task

    async def _dispatch_done_and_propagate(self, task: ClientTask) -> None:
        """Fires step_completed event + propagates unblock chain.

        Adicional FASE C Phase A · invoca M14 workflow_hooks para auto-trigger
        adenda generation si template_id matchea pattern provider-related.
        Hook follows same graceful pattern as _maybe_dispatch_notifications
        (NUNCA bloquea propagation chain).
        """
        from backend.app.motors.m_workflow_engine.dependency_resolver_service import (
            DependencyResolverService,
            dispatch_step_completed,
        )
        tmpl = get_template_by_id(task.template_id)
        primary_actor = resolve_primary_actor(tmpl) if tmpl else "admin"
        step_title = tmpl.title if tmpl else task.title

        await dispatch_step_completed(
            project_id=task.project_id,
            template_id=task.template_id,
            primary_actor=primary_actor,
            step_title=step_title,
        )

        resolver = DependencyResolverService(self.db)
        await resolver.propagate_unblock(task.project_id, task.template_id)

        # FASE C Phase A · adenda auto-trigger hook
        await _maybe_dispatch_adenda_hook(
            db=self.db,
            project_id=task.project_id,
            completed_template_id=task.template_id,
        )

    async def approve_plan(
        self,
        task_id: UUID,
        *,
        client_user_id: UUID,
        client_id: UUID,
        expected_project_id: Optional[UUID] = None,
    ) -> ClientTask:
        """#27 Ola 6 · aprobación EXPLÍCITA y trazable del Plan de Adecuación.

        "Aprobar" ≠ "firmar": es un registro de conformidad del cliente con el
        PDA (audit_log R6 + estado tarea done + SSE), NO una firma criptográfica
        (la cadena Ed25519/sign_canvas NO se toca). El auditor ENAC ve "el
        cliente aprobó el PDA el día Y" como evento canónico, sin inferirlo de
        otra firma.

        Solo aplica a los templates PHASE5_*_APPROVE_PDA. Idempotente (si ya
        está done, no re-loguea).

        Args:
            expected_project_id: B3 IDOR fix · si se pasa (siempre, desde el
                endpoint), la tarea DEBE pertenecer a ese proyecto. Bajo el pool
                cliente RLS está OFF (auth_service bypassrls), así que sin este
                guard un cliente podía aprobar el PDA de otro tenant + forjar la
                fila ``audit_log 'plan.approved'`` con el project_id de la víctima
                (evidencia ENAC falsa). Se propaga también a ``transition``.
        """
        task = await self.db.get(ClientTask, task_id)
        if not task:
            raise TaskError("Task not found")
        # B3 · la tarea debe pertenecer al proyecto del cliente (guard cross-tenant).
        if expected_project_id is not None and task.project_id != expected_project_id:
            raise TaskError("Task not found")
        if "APPROVE_PDA" not in (task.template_id or ""):
            raise TaskError(
                "Esta tarea no es una aprobación de Plan de Adecuación",
            )
        if task.status == "done":
            return task  # idempotente · ya aprobado

        # Estado done + SSE (reuse del state machine · _dispatch_done_and_propagate)
        task = await self.transition(
            task_id, "done", enforce_prereqs=False,
            expected_project_id=expected_project_id,
        )

        # R6 audit_log · evento canónico plan.approved · Sub-atom 5.A (3-way OR).
        # Bajo contexto RLS cliente (current_project_id + current_client_id ya
        # fijados por _resolve_project_id) · el trigger hash-chain sella la fila.
        await self.db.execute(text(
            "INSERT INTO audit_log (id, tabla, registro_id, accion, usuario, "
            "project_id, client_id, payload_new, timestamp) "
            "VALUES (gen_random_uuid(), 'client_tasks', :tid, 'plan.approved', "
            "'cliente', :pid, :cid, CAST(:payload AS jsonb), now())"
        ), {
            "tid": str(task_id),
            "pid": str(task.project_id),
            "cid": str(client_id),
            "payload": _json.dumps({
                "template_id": task.template_id,
                "title": task.title,
                "approved_by_client_user_id": str(client_user_id),
            }),
        })
        return task


async def _maybe_dispatch_adenda_hook(
    db,
    project_id,
    completed_template_id: str,
) -> None:
    """Graceful adenda hook · NUNCA rompe propagation chain.

    Mismo patrón _maybe_dispatch_notifications (ImportError safe + outer
    try/except).
    """
    import logging
    try:
        from backend.app.motors.m14_contracts.workflow_hooks import (
            maybe_dispatch_adenda_on_step_completed,
        )
    except ImportError:
        logging.getLogger(__name__).warning(
            "m14_contracts.workflow_hooks unavailable · skip adenda dispatch",
        )
        return

    try:
        await maybe_dispatch_adenda_on_step_completed(
            db=db,
            project_id=project_id,
            completed_template_id=completed_template_id,
        )
    except Exception as exc:  # noqa: BLE001
        logging.getLogger(__name__).warning(
            "adenda auto-trigger failed · project=%s template=%s err=%s",
            project_id, completed_template_id, exc,
        )
