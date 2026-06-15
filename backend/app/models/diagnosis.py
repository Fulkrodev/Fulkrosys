"""Motor 21 Organizational Diagnosis model."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, Integer, String, Text, DateTime, Index, LargeBinary, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, FullMixin


class DiagnosisRun(Base):
    __tablename__ = "diagnosis_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # §2.2: FK a projects (antes UUID suelto sin constraint · inconsistente).
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="running")
    triggered_by: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)

    stakeholder_analysis: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    process_inventory: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    compliance_detection: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    maturity_scoring: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    summary: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    confidential_notes_encrypted: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)

    report_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    report_docx_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    report_pdf_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_diagnosis_runs_project_status", "project_id", "status"),
    )


# ───────────── Sprint C4: tablas core del diagnóstico ─────────────

class Stakeholder(FullMixin, Base):
    """Stakeholder del proyecto (tabla nuclear spec M21)."""
    __tablename__ = "stakeholders"
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id"), nullable=False, index=True,
    )
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    cargo: Mapped[str | None] = mapped_column(String(200))
    departamento: Mapped[str | None] = mapped_column(String(200))
    poder: Mapped[int | None] = mapped_column(Integer)  # 1-5
    interes: Mapped[int | None] = mapped_column(Integer)  # 1-5
    actitud: Mapped[str | None] = mapped_column(String(30))
    # champion | supporter | neutral | resistant | blocker
    email: Mapped[str | None] = mapped_column(String(255))
    telefono: Mapped[str | None] = mapped_column(String(50))
    relaciones: Mapped[dict | None] = mapped_column(JSONB)
    notas_confidenciales: Mapped[str | None] = mapped_column(Text)


class BusinessProcess(FullMixin, Base):
    """Proceso de negocio (tabla nuclear spec M21)."""
    __tablename__ = "business_processes"
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id"), nullable=False, index=True,
    )
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    criticidad: Mapped[str | None] = mapped_column(String(20))  # alta|media|baja
    propietario: Mapped[str | None] = mapped_column(String(200))
    dependencias: Mapped[dict | None] = mapped_column(JSONB)
    sistemas_involucrados: Mapped[dict | None] = mapped_column(JSONB)
    bpmn_mermaid: Mapped[str | None] = mapped_column(Text)
    rto_horas: Mapped[int | None] = mapped_column(Integer)
    rpo_horas: Mapped[int | None] = mapped_column(Integer)


class LegalObligation(FullMixin, Base):
    """Obligación legal/normativa cruzada (tabla nuclear spec M21)."""
    __tablename__ = "legal_obligations"
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id"), nullable=False, index=True,
    )
    normativa: Mapped[str] = mapped_column(String(200), nullable=False)
    articulo: Mapped[str | None] = mapped_column(String(100))
    alcance: Mapped[str | None] = mapped_column(Text)
    impacto_ens: Mapped[str | None] = mapped_column(Text)
    estado: Mapped[str | None] = mapped_column(String(30))
    # identificada | evaluada | cumplida
    notas: Mapped[str | None] = mapped_column(Text)
    measure_codes_relacionadas: Mapped[dict | None] = mapped_column(JSONB)
