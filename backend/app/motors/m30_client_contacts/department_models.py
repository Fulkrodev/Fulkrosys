"""M30 · Department ORM (sub-atom 1.C.F.2).

Tabla project-scoped `departments` con UNIQUE(project_id, code). RLS por
``app.current_project_id`` enforced en BD (migration departments_1c_f_2_001).

Sub-atom 1.C.F.3 conecta ``client_contacts.department_id`` FK ON DELETE
SET NULL · 1 empleado pertenece a 0..1 áreas.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base


class Department(Base):
    """Área/departamento del proyecto cliente · code+name+desc."""

    __tablename__ = "departments"
    __table_args__ = (
        UniqueConstraint(
            "project_id", "code", name="uq_departments_project_code",
        ),
        Index("ix_departments_project", "project_id"),
    )

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
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )
