"""ENS measures, reinforcements, DdA, controls, obligations."""
import uuid
from datetime import date, datetime

from sqlalchemy import ForeignKey, String, Text, Float, Integer, Boolean, text as sa_text
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

try:  # pgvector opcional en dev (S11 · embeddings de medidas ENS)
    from pgvector.sqlalchemy import Vector
except ImportError:  # pragma: no cover — fallback dev sin pgvector
    from sqlalchemy import LargeBinary as Vector

from backend.app.models.base import (
    Base,
    ClientReviewMixinA,
    FullMixin,
    client_review_a_table_args,
)


class EnsMeasure(FullMixin, Base):
    __tablename__ = "ens_measures"
    codigo: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    marco: Mapped[str] = mapped_column(String(20), nullable=False)
    familia: Mapped[str | None] = mapped_column(String(20))
    descripcion: Mapped[str | None] = mapped_column(Text)
    # S11 · embedding pgvector para mapeo semántico finding→medida ENS (m08
    # ens_mapper Capa 2). Poblado por scripts/embed_ens_measures.py (fastembed).
    embedding = mapped_column(Vector(1024), nullable=True)
    requisito_base: Mapped[str | None] = mapped_column(Text)
    fuente_oficial: Mapped[str | None] = mapped_column(String(255))
    version_ens: Mapped[str | None] = mapped_column(String(20), default="RD 311/2022")
    # --- Motor 3 DdA Engine (Bloque 14) ---
    aplica_basica: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    aplica_media: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    aplica_alta: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    categoria_minima: Mapped[str | None] = mapped_column(
        String(10), nullable=True,
        doc="Categoria minima de aplicacion: BASICA, MEDIA, ALTA. NULL = aplica a todas.",
    )
    dimensiones_aplicables: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        doc="Lista de dimensiones DICAT aplicables: ['D','I','C','A','T']",
    )
    # NOTE: relationship 'reinforcements' eliminado en FASE 9.0 (ADR-029).
    # Tabla legacy ens_reinforcements drop · schema superior ens_measure_refuerzos
    # (con applicable_categories JSONB + source_chunk_id RAG-traceable) reemplaza.
    # Reseed canonico diferido a Fase alpha.2.


class DdaEntry(ClientReviewMixinA, FullMixin, Base):
    """DdA entry per medida ENS · cliente review Pattern A via ClientReviewMixinA.

    Cliente review fields (status + review_note + at + by) heredados del Mixin.
    CHECK ck_dda_entries_client_review_status + Index parcial existen en BD
    (atom 5.3.A + atom 0.1 rename client_note → client_review_note).
    """
    __tablename__ = "dda_entries"
    __table_args__ = (
        *client_review_a_table_args("dda_entries"),
    )
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    measure_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ens_measures.id"), nullable=False)
    aplicabilidad: Mapped[str | None] = mapped_column(String(20))
    justificacion_no_aplica: Mapped[str | None] = mapped_column(Text)
    refuerzos_aplicados: Mapped[dict | None] = mapped_column(JSONB)
    estado_implementacion: Mapped[str | None] = mapped_column(String(50))
    responsable: Mapped[str | None] = mapped_column(String(255))
    observaciones: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int | None] = mapped_column(Integer, default=1)
    aprobado_por: Mapped[str | None] = mapped_column(String(255))
    fecha_aprobacion: Mapped[date | None] = mapped_column()
    # Trazabilidad per-entrada: que DdA se reviso en que aniversario (migracion annual_review_e4_001).
    annual_review_record_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("annual_review_records.id"), nullable=True,
    )


class AnnualReviewRecord(FullMixin, Base):
    """Registro de auditoria del ciclo de revision anual AR/DdA (Fase 8 mantenimiento · CCN-STIC 808).

    Cada revision snapshotea el estado vigente de las 73 medidas, bumpa la version
    de las dda_entries y exige reaprobacion de Direccion. RLS project_isolation
    (ADR-013). Espejo ORM de la migracion annual_review_e4_001 (cierra alembic check drift).
    """
    __tablename__ = "annual_review_records"
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id"), nullable=False, index=True,
    )
    dda_version_from: Mapped[int | None] = mapped_column(Integer)
    dda_version_to: Mapped[int | None] = mapped_column(Integer)
    estado: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="pending", index=True,
    )  # pending | approved | rejected
    completion_snapshot: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=sa_text("'{}'::jsonb"),
    )
    aprobado_por: Mapped[str | None] = mapped_column(String(255))
    fecha_aprobacion: Mapped[date | None] = mapped_column()
    observaciones: Mapped[str | None] = mapped_column(Text)


class DdaProjectSignature(Base):
    """Signature state for DdA E-040 per project (re-integration M3+M12)."""
    __tablename__ = "dda_project_signatures"

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    signature_magic_link_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True,
        doc="FK logica (sin constraint) al magic_link de firma E-040 RSEG.",
    )
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=sa_text("now()"), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)


class Obligation(FullMixin, Base):
    __tablename__ = "obligations"
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    gap_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    tipo_ejecucion: Mapped[str | None] = mapped_column(String(50))
    entregable_esperado: Mapped[str | None] = mapped_column(String(255))
    dependencias: Mapped[dict | None] = mapped_column(JSONB)
    esfuerzo_estimado: Mapped[float | None] = mapped_column(Float)
    responsable: Mapped[str | None] = mapped_column(String(255))
    modo_ejecucion: Mapped[str | None] = mapped_column(String(50))
    estado: Mapped[str | None] = mapped_column(String(50))
    fecha_objetivo: Mapped[date | None] = mapped_column()
    # --- Motor 5 Obligations Library columns ---
    template_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    template_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    measure_code: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    titulo: Mapped[str | None] = mapped_column(String(200), nullable=True)
    entregable_tipo: Mapped[str | None] = mapped_column(String(40), nullable=True)
    magic_link_template: Mapped[str | None] = mapped_column(String(60), nullable=True)
    fecha_completado: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    dependencias_template_ids: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    criterios_aceptacion: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    fuente_normativa: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    metadata_extra: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
