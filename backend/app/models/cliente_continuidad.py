"""Cliente continuidad questionnaire + approval models · CLUSTER 2 Phase 2F.

Filosofía cliente-mínimo: cliente RECIBE drafts Marcos preparados (BIA + DRP)
y APROVA/COMENTA binding decision · NO creator mode técnico ENS.

- ClienteContinuidadInput: 1 row per project (UNIQUE upsert) · questionnaire raw
  input cliente · RTO/RPO tolerancia + procesos críticos + activos core + notas
- ClienteContinuidadApproval: audit trail approval/comments per draft (bia/drp)

Backend MVP scope · cliente UI deferred CLUSTER 6 chronological backbone.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base


class ClienteContinuidadInput(Base):
    """Questionnaire raw input cliente (1 row per project · upsert)."""

    __tablename__ = "cliente_continuidad_input"
    __table_args__ = (
        UniqueConstraint(
            "project_id", name="uq_cliente_continuidad_input_project",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    client_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    submitted_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
    )
    # Questionnaire mínimo (R29 friendly fields cliente)
    procesos_criticos: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    rto_horas_tolerancia: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rpo_horas_tolerancia: Mapped[int | None] = mapped_column(Integer, nullable=True)
    impacto_diario_eur: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True,
    )
    activos_core: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    notas_cliente: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class ClienteContinuidadApproval(Base):
    """Audit trail approval/comment cliente sobre drafts BIA/DRP."""

    __tablename__ = "cliente_continuidad_approval"
    __table_args__ = (
        CheckConstraint(
            "artifact_type IN ('bia', 'drp')",
            name="ck_cliente_continuidad_approval_type",
        ),
        CheckConstraint(
            "action IN ('approved', 'rejected', 'comment')",
            name="ck_cliente_continuidad_approval_action",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    client_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    artifact_type: Mapped[str] = mapped_column(String(20), nullable=False)
    draft_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    comment_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
    )
