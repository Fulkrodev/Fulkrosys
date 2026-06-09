"""M25 Exit Checklist · items granulares pre-cierre proyecto.

ADR-046 v3 SAN-E.MB-3.A. Provee un checklist deterministico de items
que deben completarse antes de transitar el proyecto a estado cerrado
(ENDED_RENEWAL_OK / ENDED_CHURN). NO sustituye la state machine de
M25 lifecycle · es capa de validacion sobre transiciones a cerrado.

4 categorias: legal · tecnico · documentacion · operacional.
4 estados: pendiente · completado · bloqueado · no_aplica.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, FullMixin


CATEGORIES = ("legal", "tecnico", "documentacion", "operacional")
STATUSES = ("pendiente", "completado", "bloqueado", "no_aplica")


class ExitChecklistItem(FullMixin, Base):
    __tablename__ = "exit_checklist_items"
    __table_args__ = (
        UniqueConstraint(
            "project_id", "item_code",
            name="uq_exit_checklist_project_item",
        ),
        Index(
            "ix_exit_checklist_project_status",
            "project_id", "status",
        ),
        CheckConstraint(
            "category IN ('legal','tecnico','documentacion','operacional')",
            name="ck_exit_checklist_category",
        ),
        CheckConstraint(
            "status IN ('pendiente','completado','bloqueado','no_aplica')",
            name="ck_exit_checklist_status",
        ),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_code: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text("'pendiente'"),
    )
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence.id", ondelete="SET NULL"),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )
    completed_by: Mapped[str | None] = mapped_column(
        String(255), nullable=True,
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
