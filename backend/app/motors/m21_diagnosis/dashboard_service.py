"""ProjectDashboardService aglutinador (MB-13.1 · ADR-035).

Combina cross-motor:
- backend.app.core.workflow_state.get_current_phase (existing)
- backend.app.core.workflow_state.get_next_actions (existing)
- backend.app.motors.m09_audit_prep.checklist_service.list_runs +
  AuditPreparationRun.readiness_score (existing)
- backend.app.motors.m09_audit_prep.checklist_service._collect_blockers
  (existing · extracts blockers desde checklist_results dict)

Opción B (Marcos confirmado MB-13 audit pre-flight): NO incluye
upcoming_milestones (deferred MB-18) ni maturity_breakdown (cliente
invoca GET /m21/projects/{id}/maturity directamente).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import set_tenant_context

from backend.app.core.workflow_phase import WorkflowPhase
from backend.app.core.workflow_state import (
    get_current_phase,
    get_next_actions,
)
from backend.app.core.workflow_schemas import NextAction
from backend.app.motors.m09_audit_prep.checklist_service import (
    list_runs as m09_list_runs,
    _collect_blockers,
)
from backend.app.motors.m21_diagnosis.dashboard_schemas import (
    DashboardData,
    NextActionItem,
)


PHASE_LABELS_ES: dict[WorkflowPhase, str] = {
    WorkflowPhase.PRE_VENTA: "Pre-venta",
    WorkflowPhase.ONBOARDING: "Kick-off / Onboarding",
    WorkflowPhase.DIAGNOSTICO: "Diagnóstico",
    WorkflowPhase.ANALISIS_RIESGOS: "Análisis de riesgos",
    WorkflowPhase.ADECUACION: "Plan de adecuación",
    WorkflowPhase.IMPLANTACION: "Implantación",
    WorkflowPhase.DDA_FINAL: "DdA final",
    WorkflowPhase.VERIFICACION: "Verificación",
    WorkflowPhase.CONFORMIDAD: "Conformidad",
    WorkflowPhase.RETAINER_CIERRE: "Retainer / Cierre",
}


# Días estimados PER fase PER categoría · audit empírico SAN-D + Manual ENS.
# Idx 0 = pre_venta (sin consumo días) · idx 9 = retainer_cierre (post-cert).
DAYS_REMAINING_PER_PHASE: dict[str, list[int]] = {
    "BASICA": [0, 3, 5, 5, 4, 8, 3, 3, 2, 0],   # ~33 días total post-pre_venta
    "MEDIA":  [0, 5, 8, 10, 8, 15, 5, 5, 4, 0], # ~60 días total
    "ALTA":   [0, 7, 12, 15, 12, 25, 8, 12, 8, 0],  # ~99 días total
}


_CRITICAL_PHASES_FOR_BLOCKING = (
    WorkflowPhase.VERIFICACION,
    WorkflowPhase.CONFORMIDAD,
)


class ProjectDashboardService:
    """Aglutinador info dashboard admin (MB-13.1)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_dashboard(self, project_id: UUID) -> DashboardData:
        """Retorna vista agregada admin proyecto."""
        proj = await self._load_project_row(project_id)

        current_phase = await get_current_phase(self.db, project_id)
        phase_idx = WorkflowPhase.ordered().index(current_phase)

        next_actions_raw = await get_next_actions(self.db, project_id, limit=5)
        next_actions = [
            self._to_item(a, current_phase) for a in next_actions_raw
        ]

        readiness_score, blocking_from_checklist = (
            await self._readiness_and_blockers(project_id)
        )

        category = proj["categoria_objetivo"] or "BASICA"
        estimated_days = self._estimate_days(
            phase_idx=phase_idx,
            category=category,
            readiness=readiness_score,
        )

        return DashboardData(
            project_id=project_id,
            project_name=proj["nombre"] or "Sin nombre",
            category=category,
            archetype=proj["archetype"],
            current_phase=current_phase.value,
            current_phase_label=PHASE_LABELS_ES[current_phase],
            phase_index=phase_idx,
            phase_total=10,
            next_actions=next_actions,
            readiness_score=readiness_score,
            active_alerts=[],
            active_alerts_count=0,
            estimated_days_to_certification=estimated_days,
            blocking_issues=blocking_from_checklist,
            last_updated=datetime.now(timezone.utc),
        )

    async def _load_project_row(self, project_id: UUID) -> dict:
        # RLS: la policy `client_id = current_client_id()` oculta la fila si no
        # se setea el contexto (el admin pool no trae client_id). Resolvemos el
        # owner vía get_project_owner (SECURITY DEFINER) y seteamos el contexto
        # para que este SELECT y las queries project-scoped posteriores
        # (next_actions, readiness) vean los datos.
        cid = (await self.db.execute(
            text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)},
        )).scalar()
        if cid is None:
            raise ValueError(f"Project {project_id} not found")
        await set_tenant_context(self.db, client_id=cid, project_id=project_id)

        row = await self.db.execute(
            text(
                "SELECT id, nombre, fase, categoria_objetivo, "
                "       archetype, estado, lifecycle_state "
                "FROM projects WHERE id = :pid"
            ),
            {"pid": str(project_id)},
        )
        result = row.mappings().first()
        if result is None:
            raise ValueError(f"Project {project_id} not found")
        return dict(result)

    @staticmethod
    def _to_item(
        a: NextAction, phase: WorkflowPhase,
    ) -> NextActionItem:
        action_url = a.endpoint or "#"
        urgent = a.priority <= 2
        blocking = (
            a.priority == 1 and phase in _CRITICAL_PHASES_FOR_BLOCKING
        )
        return NextActionItem(
            action_id=a.action_id,
            label=a.label,
            motor=a.motor,
            cta=a.label,
            action_url=action_url,
            estimated_minutes=a.estimated_minutes,
            priority=a.priority,
            urgent=urgent,
            blocking=blocking,
        )

    async def _readiness_and_blockers(
        self, project_id: UUID,
    ) -> tuple[int, list[str]]:
        runs = await m09_list_runs(self.db, project_id)
        if not runs:
            return 0, []
        latest = runs[0]
        score = int(latest.readiness_score or 0)
        results = latest.checklist_results or {}
        if not results:
            return score, []
        blockers_raw = _collect_blockers(results)
        blocker_strs = [
            (b.get("descripcion") or b.get("codigo") or "Bloqueante")
            for b in blockers_raw[:5]
        ]
        return score, blocker_strs

    @staticmethod
    def _estimate_days(
        phase_idx: int, category: str, readiness: int,
    ) -> Optional[int]:
        if phase_idx >= 8:
            return 0
        cat_key = category if category in DAYS_REMAINING_PER_PHASE else "BASICA"
        days = DAYS_REMAINING_PER_PHASE[cat_key]
        remaining_base = sum(days[phase_idx:])
        if remaining_base <= 0:
            return 0
        readiness_clamped = max(0, min(100, readiness))
        factor = max(0.7, min(1.5, 2.0 - readiness_clamped / 100))
        return int(remaining_base * factor)
