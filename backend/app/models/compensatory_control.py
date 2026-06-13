"""Medidas compensatorias tipadas · RD 311/2022 Art. 8.

feat/fulkro-100 Ola D · gap ALTA. Cuando una medida del Anexo II no puede
aplicarse tal cual, el RD 311/2022 Art. 8 permite sustituirla por una medida
COMPENSATORIA de seguridad equivalente, documentando el porqué + el control
sustitutivo + el riesgo residual + la APROBACIÓN de la Dirección.

Antes esto era TEXTO LIBRE en ``dda_entries.justificacion_no_aplica``. Esta tabla
lo estructura (tipado + workflow de aprobación + trazabilidad ENAC) enlazado a la
entrada de DdA correspondiente.

RLS directa por project_id (current_project_id()) · fail-closed.
"""
from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, FullMixin


COMPENSATORY_STATES = (
    "pendiente_aprobacion",
    "aprobada",
    "rechazada",
)


class CompensatoryControl(FullMixin, Base):
    """Una medida compensatoria estructurada (RD 311/2022 Art. 8)."""

    __tablename__ = "compensatory_controls"
    __table_args__ = (
        UniqueConstraint(
            "project_id", "measure_code",
            name="uq_compensatory_project_measure",
        ),
        CheckConstraint(
            "estado IN ('pendiente_aprobacion', 'aprobada', 'rechazada')",
            name="ck_compensatory_estado",
        ),
        CheckConstraint(
            # No puede estar aprobada/rechazada sin quién la aprobó.
            "(estado = 'pendiente_aprobacion') OR (aprobado_por IS NOT NULL)",
            name="ck_compensatory_approval_consistency",
        ),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dda_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dda_entries.id", ondelete="SET NULL"),
        nullable=True,
    )
    measure_code: Mapped[str] = mapped_column(String(30), nullable=False)
    motivo_no_aplica_directa: Mapped[str] = mapped_column(Text, nullable=False)
    control_compensatorio: Mapped[str] = mapped_column(Text, nullable=False)
    riesgo_residual: Mapped[str | None] = mapped_column(Text, nullable=True)
    estado: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default="pendiente_aprobacion",
    )
    aprobado_por: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fecha_aprobacion: Mapped[date | None] = mapped_column(Date, nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
