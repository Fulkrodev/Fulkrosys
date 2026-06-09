"""SQLAlchemy model audit_dry_run_results (ADR-037 SAN-D MB-15.1).

Histórico ejecuciones AuditDryRunService orchestrator M10+A11 ·
métricas agregadas + payload combinado.
"""
from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, FullMixin


class AuditDryRunResult(FullMixin, Base):
    """Resultado dry-run pre-auditoría externa · M10 + A11 combinados."""

    __tablename__ = "audit_dry_run_results"
    __table_args__ = (
        Index(
            "ix_dry_run_project_executed",
            "project_id", text("executed_at DESC"),
        ),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    executed_at: Mapped["TIMESTAMP"] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
    )
    executed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )
    m10_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("audit_simulation_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    category_at_execution: Mapped[str] = mapped_column(
        String(20), nullable=False,
    )
    archetype_at_execution: Mapped[str | None] = mapped_column(
        String(50), nullable=True,
    )
    total_questions: Mapped[int] = mapped_column(Integer, nullable=False)
    questions_with_evidence: Mapped[int] = mapped_column(
        Integer, nullable=False,
    )
    overall_readiness_score: Mapped[int] = mapped_column(
        Integer, nullable=False,
    )
    gaps_detected: Mapped[int] = mapped_column(Integer, nullable=False)
    critical_gaps: Mapped[int] = mapped_column(Integer, nullable=False)
    execution_time_ms: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
    )
    m10_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    a11_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    model_used: Mapped[str | None] = mapped_column(String(50), nullable=True)
