"""Registro de pruebas periódicas de continuidad · medida ENS op.cont.3.

feat/fulkro-100 Ola D · gap ALTA. La medida op.cont.3 (RD 311/2022 Anexo II ·
"Pruebas periódicas" del plan de continuidad) exige EJECUTAR y DOCUMENTAR pruebas
del DRP/BCP. El BIA/DRP (m19_risk · cuestionario + borradores) ya existía, pero
NO había registro de la EJECUCIÓN de las pruebas (cuándo, qué escenario, resultado,
hallazgos, próxima prueba). Esta tabla cierra ese hueco.

Operación técnica de Marcos (admin · require_owner). El cliente, a lo sumo, lo VE.
RLS directa por project_id (current_project_id()) · fail-closed.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, FullMixin


CONTINUITY_TEST_RESULTS = ("pass", "parcial", "fail")


class ContinuityTestExecution(FullMixin, Base):
    """Una ejecución de prueba periódica del plan de continuidad (op.cont.3)."""

    __tablename__ = "continuity_test_executions"
    __table_args__ = (
        CheckConstraint(
            "resultado IN ('pass', 'parcial', 'fail')",
            name="ck_continuity_test_resultado",
        ),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    fecha_prueba: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False,
    )
    escenario: Mapped[str] = mapped_column(String(255), nullable=False)
    resultado: Mapped[str] = mapped_column(String(30), nullable=False)
    hallazgos: Mapped[str | None] = mapped_column(Text, nullable=True)
    proxima_prueba_due: Mapped[date | None] = mapped_column(Date, nullable=True)
    evidencia_ref: Mapped[str | None] = mapped_column(String(500), nullable=True)
