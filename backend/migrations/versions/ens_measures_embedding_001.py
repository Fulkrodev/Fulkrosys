"""m08 · ens_measures.embedding vector(1024) (S11 · mapeo semántico finding→medida)

EnsMapper._semantic_match (Capa 2) hacía `return []` siempre porque ens_measures
no tenía columna de embedding (la Capa 3 LLM cubría el fallback). Esta migración
añade la columna pgvector (nullable). Los embeddings se pre-calculan con el script
backend/scripts/embed_ens_measures.py (infra-gated · fastembed multilingual-e5-large).
Sin embeddings poblados, _semantic_match sigue devolviendo [] de forma graceful.

Revision ID: ens_measures_embedding_001
Revises: magerit_asset_cpstic_certified_001
Create Date: 2026-06-17
"""
from __future__ import annotations

from alembic import op

revision = "ens_measures_embedding_001"
down_revision = "magerit_asset_cpstic_certified_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # pgvector ya está instalado (knowledge_chunks.embedding lo usa). Raw SQL
    # porque el tipo `vector` no es nativo de SQLAlchemy core.
    op.execute("ALTER TABLE ens_measures ADD COLUMN IF NOT EXISTS embedding vector(1024)")


def downgrade() -> None:
    op.execute("ALTER TABLE ens_measures DROP COLUMN IF EXISTS embedding")
