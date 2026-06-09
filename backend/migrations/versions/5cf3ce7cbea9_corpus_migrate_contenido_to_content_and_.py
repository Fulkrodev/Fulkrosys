"""corpus: migrate contenido to content and cleanup

Revision ID: 5cf3ce7cbea9
Revises: 80bebdb183fd
Create Date: 2026-04-15 03:12:28.210810
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '5cf3ce7cbea9'
down_revision: Union[str, None] = '80bebdb183fd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Copy contenido -> content for rows where content IS NULL
    op.execute(
        "UPDATE knowledge_chunks SET content = contenido "
        "WHERE content IS NULL AND contenido IS NOT NULL"
    )
    # 2. Drop the generated tsvector column (references old contenido)
    op.execute("DROP INDEX IF EXISTS ix_knowledge_chunks_tsvector")
    op.execute("ALTER TABLE knowledge_chunks DROP COLUMN IF EXISTS content_tsvector")
    # 3. Drop legacy contenido column
    op.execute("ALTER TABLE knowledge_chunks DROP COLUMN IF EXISTS contenido")
    # 4. Recreate tsvector column simplified (only references content)
    op.execute(
        "ALTER TABLE knowledge_chunks ADD COLUMN content_tsvector tsvector "
        "GENERATED ALWAYS AS (to_tsvector('spanish', coalesce(content, ''))) STORED"
    )
    # 5. Recreate GIN index
    op.execute(
        "CREATE INDEX ix_knowledge_chunks_tsvector ON knowledge_chunks "
        "USING gin (content_tsvector)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_knowledge_chunks_tsvector")
    op.execute("ALTER TABLE knowledge_chunks DROP COLUMN IF EXISTS content_tsvector")
    op.execute("ALTER TABLE knowledge_chunks ADD COLUMN contenido TEXT")
    # Copy content back to contenido
    op.execute("UPDATE knowledge_chunks SET contenido = content WHERE contenido IS NULL")
    op.execute(
        "ALTER TABLE knowledge_chunks ADD COLUMN content_tsvector tsvector "
        "GENERATED ALWAYS AS (to_tsvector('spanish', coalesce(contenido, coalesce(content, '')))) STORED"
    )
    op.execute(
        "CREATE INDEX ix_knowledge_chunks_tsvector ON knowledge_chunks "
        "USING gin (content_tsvector)"
    )
