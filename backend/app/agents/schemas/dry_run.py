"""Pydantic schemas AuditDryRunService (ADR-037 SAN-D MB-15.1)."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class M10FindingSummary(BaseModel):
    """Resumen finding M10 para UI dashboard."""

    measure_code: str
    measure_name: str | None = None
    evaluacion: str  # conforme | no_conforme_mayor | no_conforme_menor | observacion | no_aplica
    nivel_madurez: str  # L0..L5
    contradiccion_detectada: bool = False


class M10Summary(BaseModel):
    """Resumen run M10."""

    run_id: UUID
    score_global: int
    nivel_madurez_global: str
    conformes: int
    no_conformes_mayores: int
    no_conformes_menores: int
    observaciones: int
    no_aplica: int
    contradicciones_count: int
    findings: list[M10FindingSummary] = []


class DryRunResult(BaseModel):
    """Resultado dry-run completo · expuesto en API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    executed_at: datetime
    m10_run_id: UUID | None = None
    category_at_execution: str
    archetype_at_execution: str | None = None
    total_questions: int
    questions_with_evidence: int
    overall_readiness_score: int
    gaps_detected: int
    critical_gaps: int
    execution_time_ms: int | None = None
    m10_summary: M10Summary | None = None
    a11_payload: dict[str, Any] | None = None
    model_used: str | None = None


class DryRunHistoryEntry(BaseModel):
    id: UUID
    executed_at: datetime
    score: int
    gaps: int
    critical_gaps: int


class DryRunSummary(BaseModel):
    """Vista resumen dashboard."""

    last_executed_at: datetime | None = None
    overall_readiness_score: int = 0
    gaps_detected: int = 0
    critical_gaps: int = 0
    history: list[DryRunHistoryEntry] = []
