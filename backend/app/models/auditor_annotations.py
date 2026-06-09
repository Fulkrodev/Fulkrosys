"""AuditorAnnotation model · CLUSTER 3 Phase C1.1.

Persists auditor portal annotations (audit ENAC inspection comments) cross-motor
targets (evidence · medida · MAGERIT entities · plan tasks · audit_log entries).
RLS isolation enforced (Sub-atom 5.A pattern · project/client 2-way OR).
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base


class AuditorAnnotation(Base):
    """Auditor inline annotation · cross-motor inspection comment."""

    __tablename__ = "auditor_annotations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
    )
    magic_link_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("magic_links.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_type: Mapped[str] = mapped_column(String(40), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False,
    )
    annotation_text: Mapped[str] = mapped_column(Text, nullable=False)
    flag_severity: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default="open",
    )
    admin_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    admin_responded_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    admin_responded_by: Mapped[str | None] = mapped_column(
        String(255), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )

    # ── Constants from migration ────────────────────────────────────────

    TARGET_TYPES = frozenset({
        "evidence",
        "medida",
        "magerit_asset",
        "magerit_threat",
        "magerit_safeguard",
        "plan_task",
        "audit_log_entry",
    })

    SEVERITY_VALUES = frozenset({"info", "warning", "concern", "critical"})

    STATUS_VALUES = frozenset({
        "open", "admin_reviewed", "resolved", "dismissed",
    })

    DELETE_WINDOW_HOURS = 24  # Auditor self-soft-delete window (Phase C1.2 spec)
