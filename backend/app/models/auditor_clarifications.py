"""AuditorClarificationRequest model · CLUSTER 3 Phase C2.1.

Persists auditor portal clarification queries · auditor formula pregunta formal
sobre target específico o consulta general scoped por proyecto · admin (Marcos)
responde + status workflow. RLS isolation 2-way OR (Phase C1 pattern reused).
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base


class AuditorClarificationRequest(Base):
    """Auditor clarification query · cross-motor formal question."""

    __tablename__ = "auditor_clarification_requests"

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
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    linked_target_type: Mapped[str] = mapped_column(
        String(40), nullable=False, server_default="general",
    )
    linked_target_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )
    priority: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="normal",
    )
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

    # ── Constants ───────────────────────────────────────────────────────

    TARGET_TYPES = frozenset({
        "evidence",
        "medida",
        "magerit_asset",
        "magerit_threat",
        "magerit_safeguard",
        "plan_task",
        "audit_log_entry",
        "general",  # NO target anchor
    })

    PRIORITY_VALUES = frozenset({"low", "normal", "high", "urgent"})

    STATUS_VALUES = frozenset({"open", "in_progress", "responded", "closed"})
