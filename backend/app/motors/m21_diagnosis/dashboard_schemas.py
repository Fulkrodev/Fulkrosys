"""Schemas Pydantic dashboard agregado admin (MB-13.1 · ADR-035).

Endpoint GET /api/v1/projects/{project_id}/dashboard.

Aglutinador cross-motor que combina:
- next_actions ← workflow_state.get_next_actions (existing)
- readiness_score ← latest m09 audit_preparation_run.readiness_score
- current_phase ← workflow_state.get_current_phase (existing) + label
- blocking_issues ← _collect_blockers desde checklist_results
- estimated_days_to_certification ← lookup table per categoria + readiness
- active_alerts ← deferred MB-13.4 (placeholder schema-stable [] · count 0)

Scope ADR-035 Opción B confirmada Marcos: NO upcoming_milestones (deferred MB-18) ·
NO maturity_breakdown (cliente puede invocar GET /m21/projects/{id}/maturity
existing si lo necesita).
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class NextActionItem(BaseModel):
    """Acción concreta a ejecutar en home admin proyecto.

    Adaptación de ``NextAction`` (workflow_schemas) para UI con campos
    derivados ``cta`` · ``action_url`` · ``urgent`` · ``blocking``.
    """

    action_id: str = Field(..., description="ID estable cross-deploys")
    label: str = Field(..., description="Etiqueta visible UI")
    motor: str = Field(..., description="Motor responsable (ej: 'M16')")
    cta: str = Field(..., description="Texto del botón CTA (deriva de label)")
    action_url: str = Field(
        ...,
        description="URL UI deeplink (endpoint NextAction o '#' fallback)",
    )
    estimated_minutes: int = Field(..., ge=0)
    priority: int = Field(..., ge=1)
    urgent: bool = Field(default=False, description="Derivado: priority <= 2")
    blocking: bool = Field(
        default=False,
        description="Derivado: priority==1 en fases criticas (verif/conformidad)",
    )


class ActiveAlert(BaseModel):
    """Alerta activa que admin debe ver (m18 alert_queue · no-acknowledged)."""

    id: UUID
    severity: str = Field(..., description="info | warning | critical")
    title: str
    description: str = ""
    action_url: str = ""
    triggered_at: datetime


class DashboardData(BaseModel):
    """Vista agregada home admin proyecto (MB-13.1)."""

    project_id: UUID
    project_name: str

    category: str = Field(
        ...,
        description="BASICA / MEDIA / ALTA · default 'BASICA' si proyecto sin categoria",
    )
    archetype: str | None = Field(
        default=None,
        description="6 arquetipos PYME (SAN-C MB-11.6) · None si no clasificado",
    )

    current_phase: str = Field(..., description="WorkflowPhase enum value")
    current_phase_label: str = Field(..., description="Etiqueta humano-legible ES")
    phase_index: int = Field(..., ge=0, le=9)
    phase_total: int = Field(default=10)

    next_actions: list[NextActionItem]

    readiness_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Snapshot último AuditPreparationRun.readiness_score · 0 si sin run",
    )

    active_alerts: list[ActiveAlert] = Field(
        default_factory=list,
        description="Alertas activas (no-acknowledged) del proyecto · m18 alert_queue (S26)",
    )
    active_alerts_count: int = Field(default=0)

    estimated_days_to_certification: int | None = Field(
        default=None,
        description="Estimación días hasta certificación (lookup B/M/A · readiness factor)",
    )
    blocking_issues: list[str] = Field(
        default_factory=list,
        description="Top 5 bloqueantes activos (checklist + alerts criticas MB-13.4)",
    )

    last_updated: datetime
