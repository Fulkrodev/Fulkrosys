"""Corpus normativo extensions · sub-lote 1.B.5.0 (ADR-CORPUS-001).

Extiende `knowledge_documents` con 4 columnas y crea `knowledge_measure_mappings`
nueva. Schema alineado con el patron knowledge_* del repo (NO `corpus_*`).

Adaptaciones respecto al SQL ilustrativo del ADR:
- `superseded_by` usa UUID FK a knowledge_documents(id) — el ADR mencionaba
  TEXT FK a doc_id, pero el schema real usa UUID PK (FullMixin), no hay
  columna doc_id TEXT.
- `knowledge_measure_mappings.document_id` UUID FK a knowledge_documents(id).
- `knowledge_measure_mappings.chunk_ids` UUID[] (knowledge_chunks PK es UUID).
- `ens_medida_id` TEXT sin FK · validacion en aplicacion (paralelismo con
  knowledge_chunks.measure_code existente).

Cierra GAP-4 plan v2 §14.1 (corpus normativo + measure mappings curados).

Revision ID: corpus_norm_ext_1b50_001
Revises: add_legal_obl_catalog_001
Create Date: 2026-05-18
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "corpus_norm_ext_1b50_001"
down_revision = "add_legal_obl_catalog_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Extend knowledge_documents (4 columnas) ────────────────────
    op.add_column(
        "knowledge_documents",
        sa.Column(
            "sector_aplicacion",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("ARRAY['publico','privado']::TEXT[]"),
        ),
    )
    op.add_column(
        "knowledge_documents",
        sa.Column("version_label", sa.Text(), nullable=True),
    )
    op.add_column(
        "knowledge_documents",
        sa.Column(
            "superseded_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("knowledge_documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "knowledge_documents",
        sa.Column(
            "exclude_from_client_exports",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    # GIN index para queries que filtran por sector_aplicacion (array overlap &&)
    op.create_index(
        "ix_knowledge_documents_sector_aplicacion",
        "knowledge_documents",
        ["sector_aplicacion"],
        postgresql_using="gin",
    )

    # ── 2. CREATE knowledge_measure_mappings ──────────────────────────
    op.create_table(
        "knowledge_measure_mappings",
        sa.Column(
            "mapping_id", sa.BigInteger(), primary_key=True, autoincrement=True,
        ),
        sa.Column("ens_medida_id", sa.Text(), nullable=False),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "chunk_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=False,
        ),
        sa.Column(
            "relevance_score",
            sa.REAL(),
            sa.CheckConstraint(
                "relevance_score BETWEEN 0 AND 1",
                name="knowledge_measure_mappings_relevance_range",
            ),
            nullable=True,
        ),
        sa.Column("curated_by", sa.Text(), nullable=True),
        sa.Column(
            "curated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "ens_medida_id", "document_id",
            name="knowledge_measure_mappings_medida_doc_key",
        ),
    )
    op.create_index(
        "ix_knowledge_measure_mappings_lookup",
        "knowledge_measure_mappings",
        ["ens_medida_id", sa.text("relevance_score DESC")],
    )

    # fulkro_app NOSUPERUSER necesita SELECT para retrieval runtime
    # (A14 + A15 + A24 consumen estas mappings). INSERT/UPDATE se hace
    # via fulkro_migrate (seed scripts) o pgAdmin (curado manual Marcos).
    op.execute("GRANT SELECT ON knowledge_measure_mappings TO fulkro_app")


def downgrade() -> None:
    op.execute("REVOKE SELECT ON knowledge_measure_mappings FROM fulkro_app")
    op.drop_index(
        "ix_knowledge_measure_mappings_lookup",
        table_name="knowledge_measure_mappings",
    )
    op.drop_table("knowledge_measure_mappings")

    op.drop_index(
        "ix_knowledge_documents_sector_aplicacion",
        table_name="knowledge_documents",
    )
    op.drop_column("knowledge_documents", "exclude_from_client_exports")
    op.drop_column("knowledge_documents", "superseded_by")
    op.drop_column("knowledge_documents", "version_label")
    op.drop_column("knowledge_documents", "sector_aplicacion")
