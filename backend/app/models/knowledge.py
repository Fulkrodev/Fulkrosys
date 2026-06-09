"""Knowledge base for RAG: sources, documents, chunks, links, and LLM interaction log."""
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Computed,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    REAL,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TIMESTAMP, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, FullMixin, _utcnow

try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    from sqlalchemy import LargeBinary as Vector  # fallback for dev without pgvector


# ── Knowledge Source ────────────────────────────────────────────────
class KnowledgeSource(Base):
    """A corpus source (regulation, CCN guide, BOE publication, etc.)."""

    __tablename__ = "knowledge_sources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    publisher: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    publication_date: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    language: Mapped[str] = mapped_column(String(8), server_default=text("'es'"), nullable=False)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False,
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), onupdate=_utcnow, nullable=True,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True, default=None,
    )

    documents: Mapped[list["KnowledgeDocument"]] = relationship(
        back_populates="source", cascade="all, delete-orphan",
    )


# ── Knowledge Document (existing table — extended) ─────────────────
class KnowledgeDocument(FullMixin, Base):
    __tablename__ = "knowledge_documents"

    # Schema consolidado SAN-B.MB-2.2 · 6 columnas legacy droppeadas
    # (fuente, titulo, version, fecha_publicacion, hash_sha256,
    # contenido_path). Datos sin equivalente new (version,
    # fecha_publicacion, contenido_path) preservados en metadata JSONB
    # con keys legacy_version / legacy_publication_date / legacy_content_path.
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("knowledge_sources.id"), nullable=True,
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(
        String(128), server_default=text("'text/html'"), nullable=False,
    )
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    # Sub-lote 1.B.5.0 · ADR-CORPUS-001 extensions
    sector_aplicacion: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        server_default=text("ARRAY['publico','privado']::TEXT[]"),
    )
    version_label: Mapped[str | None] = mapped_column(Text, nullable=True)
    superseded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    exclude_from_client_exports: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false"),
    )

    # --- relationships ---
    chunks: Mapped[list["KnowledgeChunk"]] = relationship(back_populates="document")
    source: Mapped["KnowledgeSource | None"] = relationship(back_populates="documents")


# ── Knowledge Chunk (existing table — extended) ────────────────────
class KnowledgeChunk(FullMixin, Base):
    __tablename__ = "knowledge_chunks"

    __table_args__ = (
        Index(
            "ix_knowledge_chunks_tsvector",
            "content_tsvector",
            postgresql_using="gin",
        ),
        Index(
            "ix_knowledge_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
            postgresql_with={"m": 16, "ef_construction": 64},
        ),
    )

    # --- columns ---
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_documents.id"), nullable=False,
    )
    seccion: Mapped[str | None] = mapped_column(String(255))
    # NOTE: legacy 'contenido' migrated to 'content' in 5cf3ce7cbea9
    embedding = mapped_column(Vector(1024), nullable=True)
    metadata_extra: Mapped[dict | None] = mapped_column(JSONB)

    chunk_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    heading_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    measure_code: Mapped[str | None] = mapped_column(
        String(32), nullable=True, index=True,
    )
    article_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_tsvector = mapped_column(
        TSVECTOR,
        Computed(
            "to_tsvector('spanish', coalesce(content, ''))",
            persisted=True,
        ),
        nullable=True,
    )

    # --- relationships ---
    document: Mapped["KnowledgeDocument"] = relationship(back_populates="chunks")


# ── Knowledge Link ─────────────────────────────────────────────────
class KnowledgeLink(Base):
    """Directional link between two chunks (cross-ref, implements, etc.)."""

    __tablename__ = "knowledge_links"

    __table_args__ = (
        UniqueConstraint(
            "source_chunk_id", "target_chunk_id", "link_type",
            name="uq_knowledge_links_src_tgt_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    source_chunk_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_chunks.id"), nullable=False,
    )
    target_chunk_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_chunks.id"), nullable=False,
    )
    link_type: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Numeric(4, 3), nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False,
    )


# ── Knowledge Measure Mappings (sub-lote 1.B.5.0 · ADR-CORPUS-001) ─
class KnowledgeMeasureMapping(Base):
    """Mapping curado N:M entre medida ENS y chunks de un documento.

    Complementa `knowledge_chunks.measure_code` (1 chunk → 1 medida) con
    scoring + curado + provenance. Permite priorizar fuentes por medida
    en retrieval RAG y trazar quien curó cada mapping (`curated_by`:
    'auto-rag' | 'marcos' | 'consultor:<id>').
    """

    __tablename__ = "knowledge_measure_mappings"

    __table_args__ = (
        UniqueConstraint(
            "ens_medida_id", "document_id",
            name="knowledge_measure_mappings_medida_doc_key",
        ),
        CheckConstraint(
            "relevance_score BETWEEN 0 AND 1",
            name="knowledge_measure_mappings_relevance_range",
        ),
        Index(
            "ix_knowledge_measure_mappings_lookup",
            "ens_medida_id",
            text("relevance_score DESC"),
        ),
    )

    mapping_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True,
    )
    ens_medida_id: Mapped[str] = mapped_column(Text, nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False,
    )
    relevance_score: Mapped[float | None] = mapped_column(REAL, nullable=True)
    curated_by: Mapped[str | None] = mapped_column(Text, nullable=True)
    curated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False,
    )


# ── LLM Interaction Log ───────────────────────────────────────────
class LLMInteractionLog(Base):
    """Tracks every LLM call for observability and cost accounting."""

    __tablename__ = "llm_interaction_log"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True,
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True,
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True,
    )
    feature: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    prompt_preview: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_preview: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    cached_input_tokens: Mapped[int] = mapped_column(
        BigInteger, server_default=text("0"), nullable=False, index=True,
    )
    cost_usd: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), server_default=text("'success'"), nullable=False, index=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False, index=True,
    )
