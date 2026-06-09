"""m_workflow_engine service · wrappers around client_tasks CRUD (existing).

Sub-atom 1.C.D.A v3.8 · NO storage propio (ADR-025) · service expone helpers
para advance/mark_done sobre ClientTask existing.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m21_portal_cliente.models_tasks import ClientTask
from backend.app.motors.m21_portal_cliente.task_templates_loader import (
    get_template_by_id,
    resolve_primary_actor,
)

logger = logging.getLogger(__name__)


class WorkflowEngineServiceError(ValueError):
    """Errores del service workflow engine."""


class WorkflowEngineService:
    """Service wrappers · ClientTask CRUD + advance helpers."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def advance_step(
        self,
        project_id: uuid.UUID,
        template_id: str,
        updated_by: uuid.UUID,
    ) -> ClientTask:
        """Marcar sub-paso como completado (admin override · used by Marcos UI).

        Idempotente · si tarea NO existe · crea desde template + marca completed.
        Si ya existe · transita status='completed' + set completed_at.

        OPS-043 sostenido · await db.commit() explícito.
        """
        # Buscar task existente
        row = await self.db.execute(
            select(ClientTask).where(
                ClientTask.project_id == project_id,
                ClientTask.template_id == template_id,
                ClientTask.deleted_at.is_(None),
            )
        )
        task = row.scalar_one_or_none()

        now = datetime.now(timezone.utc)

        if task is None:
            # Crear desde template
            tmpl = get_template_by_id(template_id)
            if tmpl is None:
                raise WorkflowEngineServiceError(
                    f"Template {template_id} not found",
                )
            task = ClientTask(
                project_id=project_id,
                template_id=tmpl.id,
                phase=tmpl.phase,
                title=tmpl.title,
                description=tmpl.description_detailed_es or tmpl.description,
                cta_label=tmpl.cta_label,
                cta_url=tmpl.cta_url,
                expected_evidence_type=tmpl.expected_evidence_type,
                expected_evidence_count=tmpl.expected_evidence_count,
                priority=tmpl.priority,
                status="completed",
                completed_at=now,
                metadata_jsonb={"advanced_by_admin_uuid": str(updated_by)},
            )
            self.db.add(task)
        else:
            task.status = "completed"
            task.completed_at = now
            task.blocked_reason = None
            existing_meta = dict(task.metadata_jsonb or {})
            existing_meta["advanced_by_admin_uuid"] = str(updated_by)
            task.metadata_jsonb = existing_meta

        await self.db.commit()  # OPS-043 sostenido
        await self.db.refresh(task)

        # #13 Ola 3 · notificar al cliente en tiempo real que Marcos (admin)
        # avanzó un sub-paso. POST-COMMIT + BEST-EFFORT REAL: el SSE es
        # notificación, NO transacción · un fallo del dispatch JAMÁS revierte el
        # avance (try/except traga + loguea, no propaga). El cliente recibe
        # step_completed solo si primary_actor == "admin" (filtro audiencia
        # existente · "Marcos terminó su paso").
        try:
            from backend.app.motors.m_workflow_engine.dependency_resolver_service import (  # noqa: E501
                dispatch_step_completed,
            )

            tmpl = get_template_by_id(template_id)
            await dispatch_step_completed(
                project_id=project_id,
                template_id=template_id,
                primary_actor=resolve_primary_actor(tmpl) if tmpl else "admin",
                step_title=tmpl.title if tmpl else template_id,
            )
        except Exception:  # noqa: BLE001 · SSE best-effort · nunca rompe el avance
            logger.warning(
                "SSE dispatch_step_completed best-effort falló · "
                "project=%s template=%s (avance NO revertido)",
                project_id,
                template_id,
                exc_info=True,
            )

        return task
