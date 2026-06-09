"""ENS corpus extensions: refuerzos, dimensiones, guias CCN, evidencia types."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, _utcnow


# ── ENS Measure Refuerzo ───────────────────────────────────────────
class ENSMeasureRefuerzo(Base):
    """Reinforcement levels (+R1, +R2 ...) per ENS measure."""

    __tablename__ = "ens_measure_refuerzos"

    __table_args__ = (
        UniqueConstraint(
            "measure_code", "refuerzo_level",
            name="uq_ens_refuerzo_code_level",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    measure_code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    refuerzo_level: Mapped[str] = mapped_column(String(16), nullable=False)
    applicable_categories: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("knowledge_chunks.id"), nullable=True,
    )
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False,
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), onupdate=_utcnow, nullable=True,
    )


# ── ENS Measure Dimension ─────────────────────────────────────────
class ENSMeasureDimension(Base):
    """ACIDT dimensions per measure + optional refuerzo level."""

    __tablename__ = "ens_measure_dimensiones"

    __table_args__ = (
        UniqueConstraint(
            "measure_code", "refuerzo_level", "dimension",
            name="uq_ens_dimension_code_level_dim",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    measure_code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    refuerzo_level: Mapped[str | None] = mapped_column(String(16), nullable=True)
    dimension: Mapped[str] = mapped_column(String(1), nullable=False)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False,
    )


# ── ENS Measure Guia CCN ──────────────────────────────────────────
class ENSMeasureGuiaCCN(Base):
    """Links ENS measures to CCN-STIC guide sections."""

    __tablename__ = "ens_measure_guias_ccn"

    __table_args__ = (
        UniqueConstraint(
            "measure_code", "guia_code", "section_ref",
            name="uq_ens_guia_code_guia_section",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    measure_code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    guia_code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    section_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)
    chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("knowledge_chunks.id"), nullable=True,
    )
    relevance: Mapped[str] = mapped_column(
        String(32), server_default=text("'develops'"), nullable=False,
    )
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False,
    )


# ── ENS Measure Evidencia Type ─────────────────────────────────────
class ENSMeasureEvidenciaType(Base):
    """Expected evidence types per ENS measure."""

    __tablename__ = "ens_measure_evidencia_types"

    __table_args__ = (
        UniqueConstraint(
            "measure_code", "evidence_type",
            name="uq_ens_evidencia_code_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    measure_code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    evidence_type: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    freshness_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    applicable_categories: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_mandatory: Mapped[bool] = mapped_column(
        server_default=text("true"), nullable=False,
    )
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False,
    )
    # Catálogo evidencia ENS audit-grade (migración f8c1e2d4a004 2026-04-21).
    # 105 rows × 4 cols pobladas con info auditor: tool generador, formato,
    # automatable yes/no, query template auditor.
    format: Mapped[str | None] = mapped_column(
        String(120), nullable=True,
        comment="Formato esperado evidencia (ej: plain/png · ext .txt,.png).",
    )
    source_tool: Mapped[str | None] = mapped_column(
        String(120), nullable=True,
        comment="Tool/sistema generador evidencia (ej: Firewall + NAC + inspección TLS).",
    )
    automatable: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False,
        comment="¿Esta evidencia automatizable via tools/scripts?",
    )
    audit_query: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Query auditor template (ej: ¿Puede aportar la configuración de red...?).",
    )
