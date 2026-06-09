"""Motor 9 Audit Preparation Engine models (M9-A)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, FullMixin


class AuditPreparationRun(FullMixin, Base):
    """Ejecucion de checklist pre-auditoria (M9-A)."""

    __tablename__ = "audit_preparation_runs"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id"), nullable=False, index=True,
    )
    categoria: Mapped[str] = mapped_column(String(10), nullable=False)
    estado: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", server_default="pending",
    )

    checklist_results: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict,
    )

    readiness_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    contradicciones_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
    )
    alertas_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
    )

    dossier_zip_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    dossier_generated_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    matriz_99_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    started_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )

    __table_args__ = (
        Index(
            "ix_audit_preparation_runs_project_estado",
            "project_id", "estado",
        ),
    )


class AuditChecklistItem(FullMixin, Base):
    """Item individual de la checklist (hallazgo/verificacion)."""

    __tablename__ = "audit_checklist_items"

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("audit_preparation_runs.id"),
        nullable=False, index=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"),
        nullable=False, index=True,
    )

    categoria_check: Mapped[str] = mapped_column(String(30), nullable=False)
    referencia: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)

    estado: Mapped[str] = mapped_column(String(20), nullable=False)
    severidad: Mapped[str] = mapped_column(
        String(20), nullable=False, default="info", server_default="info",
    )

    detalle: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    accion_sugerida: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    resuelto: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false",
    )
    resuelto_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    resuelto_por: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    __table_args__ = (
        Index(
            "ix_audit_checklist_items_run_estado",
            "run_id", "estado",
        ),
        Index(
            "ix_audit_checklist_items_project_severidad",
            "project_id", "severidad",
        ),
    )
