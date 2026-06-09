"""m_workflow_engine motor · view composer (sub-atom 1.C.D.A v3.8).

NUEVO LIGERO · VIEW COMPOSER · NO storage propio (ADR-025 sostenido).

Cruza:
  - YAML enriched task_templates (m21_portal_cliente/task_templates.yaml)
  - projects table 19 dimensions (Anexo L plan v3.8)
  - client_tasks state (existing m21_portal_cliente)
  - workflow_state derivation (existing core/workflow_state)

Output: enriched workflow vista para admin (multi-cliente) + cliente
(per project subset) + copilotos LLM (context loaders 1.D.B).

R31 sostenido · motor backend nuevo + UI dedicada en mismo sub-atom · UI
(Admin Workflow Command Center) deferred 1.C.D.B (consecutive sub-fase ·
plan v3.8 split admitido).
"""
from backend.app.motors.m_workflow_engine.dependency_resolver_service import (
    DependencyResolution,
    DependencyResolverService,
    StepStatus,
    check_dependencies_satisfied,
    dispatch_step_blocked,
    dispatch_step_completed,
    dispatch_step_unblocked,
    resolve_step_status,
)
from backend.app.motors.m_workflow_engine.engine import (
    EnrichedStepState,
    compute_steps_for_project,
)
from backend.app.motors.m_workflow_engine.service import WorkflowEngineService

__all__ = [
    "DependencyResolution",
    "DependencyResolverService",
    "EnrichedStepState",
    "StepStatus",
    "WorkflowEngineService",
    "check_dependencies_satisfied",
    "compute_steps_for_project",
    "dispatch_step_blocked",
    "dispatch_step_completed",
    "dispatch_step_unblocked",
    "resolve_step_status",
]
