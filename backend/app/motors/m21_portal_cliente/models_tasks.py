"""ClientTask model (ADR-038 SAN-D MB-14.3)."""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, FullMixin


class ClientTask(FullMixin, Base):
    """Task asignada a cliente · auto-generada per template + workflow phase."""

    __tablename__ = "client_tasks"
    __table_args__ = (
        UniqueConstraint(
            "project_id", "template_id",
            name="uq_client_tasks_project_template",
        ),
        Index("ix_client_tasks_phase", "phase"),
        Index("ix_client_tasks_project_status", "project_id", "status"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    client_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("client_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    template_id: Mapped[str] = mapped_column(String(80), nullable=False)
    phase: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    cta_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    cta_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    expected_evidence_type: Mapped[str | None] = mapped_column(
        String(80), nullable=True,
    )
    expected_evidence_count: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False, server_default=text("1"),
    )
    priority: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, server_default=text("0"),
    )
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False,
    )
    due_date: Mapped[date | None] = mapped_column(nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    blocked_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_jsonb: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
