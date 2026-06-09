"""Evidence Request model · CLUSTER 3 Phase 3A.

Workflow state machine canonical:
- pending_cliente → pending_review → approved | rejected | cancelled
- cliente upload links Evidence row · admin approve/reject con motivo claro
- audit_log Sub-atom 5.A 3-way OR propagated cross state transitions

Filosofía cliente-mínimo: cliente VE tarea pendiente · SUBE archivo · MARK-NA
si no aplica · NO opera Evidence vault. Marcos VALIDA / RECHAZA con motivo claro.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base


# State machine canonical · 6 states (3 active + 3 terminal)
EVIDENCE_REQUEST_STATES = frozenset({
    "pending_cliente",   # admin created · cliente pending action
    "pending_review",    # cliente uploaded · admin pending validation
    "approved",          # admin approved · TERMINAL
    "rejected",          # admin rejected con motivo · cliente puede re-upload
    "cancelled",         # admin cancelled · TERMINAL
    "marked_na",         # cliente marked no aplicable · TERMINAL
})


class EvidenceRequest(Base):
    """Evidence request workflow state machine canonical."""

    __tablename__ = "evidence_requests"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending_cliente', 'pending_review', 'approved', "
            "'rejected', 'cancelled', 'marked_na')",
            name="ck_evidence_requests_status",
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
    client_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    measure_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    control_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )
    tipo_documento: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
    )
    titulo: Mapped[str] = mapped_column(String(255), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    plantilla_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    deadline_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="pending_cliente",
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False,
    )
    # Resolution metadata
    cliente_uploaded_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence.id", ondelete="SET NULL"),
        nullable=True,
    )
    cliente_na_motivo: Mapped[str | None] = mapped_column(Text, nullable=True)
    admin_validated_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    admin_validated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )
    admin_rejection_motivo: Mapped[str | None] = mapped_column(Text, nullable=True)
