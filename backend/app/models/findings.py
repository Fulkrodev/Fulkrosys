"""Findings, remediation, audit sessions."""
import uuid
from datetime import date

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, FullMixin


class Finding(FullMixin, Base):
    __tablename__ = "findings"
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    fuente: Mapped[str | None] = mapped_column(String(100))
    severidad: Mapped[str | None] = mapped_column(String(20))
    medida_afectada: Mapped[str | None] = mapped_column(String(20))
    descripcion: Mapped[str | None] = mapped_column(Text)
    evidencia_relacionada: Mapped[str | None] = mapped_column(String(500))
    estado: Mapped[str | None] = mapped_column(String(50))
    asignado_a: Mapped[str | None] = mapped_column(String(255))
    fecha_objetivo: Mapped[date | None] = mapped_column()
    metadata_jsonb: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        doc="Metadatos del gap: estado_actual, estado_objetivo, esfuerzo_horas, quick_win, dependencias, guia_remediacion. Usado por Motor 4 Gap Analysis.",
    )


class RemediationPlan(FullMixin, Base):
    __tablename__ = "remediation_plans"
    finding_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("findings.id"), nullable=False)
    accion: Mapped[str | None] = mapped_column(Text)
    responsable: Mapped[str | None] = mapped_column(String(255))
    fecha_objetivo: Mapped[date | None] = mapped_column()
    estado: Mapped[str | None] = mapped_column(String(50))
    evidencia_cierre: Mapped[str | None] = mapped_column(String(500))


class AuditSession(FullMixin, Base):
    __tablename__ = "audit_sessions"
    __table_args__ = (
        Index("ix_audit_sessions_project_codigo_externo", "project_id", "codigo_externo"),
    )
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    tipo: Mapped[str | None] = mapped_column(String(50))
    fecha_inicio: Mapped[date | None] = mapped_column()
    fecha_fin: Mapped[date | None] = mapped_column()
    auditor: Mapped[str | None] = mapped_column(String(255))
    alcance: Mapped[str | None] = mapped_column(Text)
    resultado: Mapped[str | None] = mapped_column(String(50))
    informe_path: Mapped[str | None] = mapped_column(String(500))
    # R26 · clave de la auditoría externa de origen (E-321 codigo_auditoria_ext)
    # para upsert idempotente de la proyección desde live_records.
    codigo_externo: Mapped[str | None] = mapped_column(String(50))


class AuditFinding(FullMixin, Base):
    __tablename__ = "audit_findings"
    __table_args__ = (
        Index("ix_audit_findings_session_codigo", "audit_session_id", "codigo_externo"),
    )
    audit_session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("audit_sessions.id"), nullable=False)
    severidad: Mapped[str | None] = mapped_column(String(20))
    medida_afectada: Mapped[str | None] = mapped_column(String(20))
    descripcion: Mapped[str | None] = mapped_column(Text)
    plan_remediacion_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("remediation_plans.id"))
    # R26 · proyección estructurada de la NC E-322 (severidad + PAC + plazos).
    # El JSONB en live_records es la fuente WORM; estos campos son derivados.
    codigo_externo: Mapped[str | None] = mapped_column(String(50))
    estado: Mapped[str | None] = mapped_column(String(30))
    accion_correctiva: Mapped[str | None] = mapped_column(Text)
    responsable: Mapped[str | None] = mapped_column(String(255))
    fecha_compromiso: Mapped[date | None] = mapped_column()
    fecha_cierre: Mapped[date | None] = mapped_column()
