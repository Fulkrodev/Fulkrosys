"""SQLAlchemy models for Agent 21 — Detector Discrepancias.

Tablas:
- a21_scan_runs: ejecuciones del detector cross-motor por proyecto
- a21_discrepancies: NC detectadas (incoherencias entre motores)
  con workflow open → acknowledged/resolved/dismissed.

RLS via current_project_id() (regla férrea project isolation).
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, FullMixin


class A21ScanRun(FullMixin, Base):
    """Ejecución del detector cross-motor (manual o auto-triggered)."""

    __tablename__ = "a21_scan_runs"
    __table_args__ = (
        CheckConstraint(
            "run_status IN ('pending', 'running', 'completed', 'failed')",
            name="ck_a21_scan_runs_status",
        ),
        Index(
            "idx_a21_scan_runs_project_status",
            "project_id", "run_status",
        ),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    run_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending",
    )
    motors_scanned: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list,
    )
    discrepancies_found: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    started_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_jsonb: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict,
    )

    discrepancies: Mapped[list["A21Discrepancy"]] = relationship(
        back_populates="scan_run",
        cascade="all, delete-orphan",
    )


class A21Discrepancy(FullMixin, Base):
    """Discrepancia (NC) detectada entre motores · workflow resolución."""

    __tablename__ = "a21_discrepancies"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('critical', 'high', 'medium', 'low')",
            name="ck_a21_discrepancies_severity",
        ),
        CheckConstraint(
            "resolution_status IN ('open', 'acknowledged', 'resolved', 'dismissed')",
            name="ck_a21_discrepancies_resolution",
        ),
        Index(
            "idx_a21_discrepancies_project_status",
            "project_id", "resolution_status",
        ),
        Index(
            "idx_a21_discrepancies_severity",
            "severity",
        ),
    )

    scan_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("a21_scan_runs.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    discrepancy_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # magerit_vs_dda | dda_vs_evidence | magerit_vs_findings |
    # dda_vs_documents | findings_vs_remediation
    severity: Mapped[str] = mapped_column(String(10), nullable=False)
    motor_a: Mapped[str] = mapped_column(String(20), nullable=False)
    motor_b: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_a: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict,
    )
    evidence_b: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict,
    )
    resolution_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="open",
    )
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )

    scan_run: Mapped["A21ScanRun"] = relationship(
        back_populates="discrepancies",
    )
