"""Schemas Pydantic FASE 8 workflow (ADR-026).

3 schemas response para endpoints /api/v1/workflow/*:

- NextAction      → respuesta /next-actions/{project_id}
- PhaseProgress   → respuesta /phase-progress/{project_id}/{phase}
- TaskItem        → componente respuesta /phase-tasks/{project_id}/{phase}

Patrón coherente con commit() pattern uniform (5.5.F.0) y RBAC global dep
require_marcos_or_client (4.D auth global dep).
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from backend.app.core.workflow_phase import WorkflowPhase


PhaseStatus = Literal["pending", "in_progress", "done"]
# 8.WORKFLOW.CALIBRATE W2: ``manual_tracking`` añadido para tasks
# no-instrumentables via query motor (e.g. proposals/contracts via lead_id sin
# link directo a project, gap_analysis sin tabla en BD). UI cliente las muestra
# como "pendiente confirmación Marcos" en lugar de fingir status real.
TaskStatus = Literal["pending", "in_progress", "completed", "manual_tracking"]
TaskPriority = Literal["high", "medium", "low"]


class NextAction(BaseModel):
    """Acción priorizada para fase actual del proyecto."""

    action_id: str = Field(..., description="ID estable cross-deploys (ej: 'create_onboarding')")
    label: str = Field(..., description="Etiqueta visible UI")
    motor: str = Field(..., description="Motor responsable (ej: 'M16')")
    endpoint: str | None = Field(default=None, description="URL UI relevante (deeplink)")
    priority: int = Field(..., ge=1, description="1 = mayor prioridad")
    estimated_minutes: int = Field(..., ge=0, description="Estimación dedicación cliente")


class PhaseProgress(BaseModel):
    """Métricas progreso fase específica del proyecto."""

    phase: WorkflowPhase
    pct_completed: float = Field(..., ge=0.0, le=100.0)
    total_items: int = Field(..., ge=0)
    items_done: int = Field(..., ge=0)
    status: PhaseStatus


class TaskItem(BaseModel):
    """Tarea expected para fase con status derivado per motor."""

    label: str
    motor: str
    priority: TaskPriority
    ord: int = Field(..., ge=1, description="Orden recomendado dentro fase")
    status: TaskStatus


class PhaseRoadmapEntry(BaseModel):
    """Una fase en el roadmap (8 entries response /roadmap)."""

    phase: WorkflowPhase
    status: PhaseStatus
    pct_completed: float = Field(..., ge=0.0, le=100.0)
    is_current: bool


class WorkflowRoadmap(BaseModel):
    """Roadmap completo proyecto · 8 fases con estados (response /roadmap)."""

    project_id: str
    current_phase: WorkflowPhase
    phases: list[PhaseRoadmapEntry]
