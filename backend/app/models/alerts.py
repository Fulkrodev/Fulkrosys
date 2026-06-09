"""Modelo Alert · alertas proactivas UI admin (MB-13.4 · ADR-035).

Tabla ``alert_queue`` (migration ``sand_alert_queue_001``).
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint, ForeignKey, Index, String, Text, TIMESTAMP, text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from backend.app.models.base import Base


class Alert(Base):
    """Alerta proactiva en queue para UI admin (AlertBell + AlertsPanel)."""

    __tablename__ = "alert_queue"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('info','warning','critical')",
            name="ck_alert_queue_severity",
        ),
        CheckConstraint(
            "category IN ("
            "'bienal_art31','payment_overdue_aapp','client_inactivity',"
            "'evidence_stale','retainer_overdue','milestone_due',"
            "'workflow_blocked','audit_due','rgpd_72h',"
            "'contract_milestone','renewal_due','dpc_due',"
            "'incident_critical_pending_route','incident_ccn_cert_overdue',"
            "'antivirus_infected','antivirus_scan_error','other')",
            name="ck_alert_queue_category",
        ),
        Index(
            "ix_alert_queue_project_active",
            "project_id", "acknowledged_at",
        ),
        Index(
            "ix_alert_queue_triggered_at",
            text("triggered_at DESC"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    triggered_by: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
    )
    triggered_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    acknowledged_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )
    metadata_jsonb: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
