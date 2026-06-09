"""Marcos timesheet ORM model · MB-7.bis atom 7.bis.5."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, CheckConstraint, ForeignKey, Index, Integer, String, Text, text,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base


class MarcosTimesheetEntry(Base):
    """Hour tracking entries (Marcos cross-cliente)."""

    __tablename__ = "marcos_timesheet_entries"
    __table_args__ = (
        CheckConstraint(
            "source IN ('auto_endpoint', 'manual', 'import')",
            name="ck_marcos_timesheet_source",
        ),
        CheckConstraint(
            "duration_minutes IS NULL OR duration_minutes >= 0",
            name="ck_marcos_timesheet_duration_nonneg",
        ),
        Index("ix_marcos_timesheet_entries_client_id", "client_id"),
        Index("ix_marcos_timesheet_entries_retainer_id", "retainer_id"),
        Index("ix_marcos_timesheet_entries_started_at", "started_at"),
        Index(
            "ix_marcos_timesheet_started_at_desc",
            text("started_at DESC"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
    )
    retainer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("retainer_contracts.id", ondelete="SET NULL"),
        nullable=True,
    )
    activity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("retainer_activities.id", ondelete="SET NULL"),
        nullable=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False,
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
    )
    duration_minutes: Mapped[int | None] = mapped_column(
        Integer,
        comment="Computed at end_session · NULL while ongoing",
    )
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'manual'"),
    )
    manual_override: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false"),
    )
    endpoint_path: Mapped[str | None] = mapped_column(String(500))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"),
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
    )
