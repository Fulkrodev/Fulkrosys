"""san_e_mb5_dda_client_review

ADR-020 v5 SAN-E v3.MB-5.3 · cliente in-portal review DdA · 73 medidas Anexo II.

4 cols aditivas backwards compatible en dda_entries:
- client_review_status (str 30 nullable · CHECK constraint enum 4 valores)
- client_note (text nullable)
- client_reviewed_at (timestamp nullable)
- client_reviewed_by_user_id (uuid nullable)

CHECK constraint enum: pendiente_revision | revisada_ok | con_pregunta | suggest_change.
Default: NULL = nunca revisado por cliente (admin acaba de generar entry).

Index parcial NEW: idx_dda_entries_client_review_status (project_id, client_review_status)
WHERE client_review_status IS NOT NULL · acelera summary cliente.

Revision ID: 78d80ba049de
Revises: 123920e86153
Create Date: 2026-05-10 16:54:21.477077
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = '78d80ba049de'
down_revision: Union[str, None] = '123920e86153'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "dda_entries",
        sa.Column("client_review_status", sa.String(30), nullable=True),
    )
    op.add_column(
        "dda_entries",
        sa.Column("client_note", sa.Text, nullable=True),
    )
    op.add_column(
        "dda_entries",
        sa.Column(
            "client_reviewed_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "dda_entries",
        sa.Column(
            "client_reviewed_by_user_id", UUID(as_uuid=True), nullable=True,
        ),
    )

    op.execute("""
        ALTER TABLE dda_entries
        ADD CONSTRAINT ck_dda_entries_client_review_status
        CHECK (client_review_status IS NULL OR client_review_status IN (
            'pendiente_revision',
            'revisada_ok',
            'con_pregunta',
            'suggest_change'
        ))
    """)

    op.create_index(
        "idx_dda_entries_client_review_status",
        "dda_entries",
        ["project_id", "client_review_status"],
        postgresql_where=sa.text("client_review_status IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "idx_dda_entries_client_review_status",
        table_name="dda_entries",
    )
    op.execute(
        "ALTER TABLE dda_entries DROP CONSTRAINT IF EXISTS "
        "ck_dda_entries_client_review_status"
    )
    op.drop_column("dda_entries", "client_reviewed_by_user_id")
    op.drop_column("dda_entries", "client_reviewed_at")
    op.drop_column("dda_entries", "client_note")
    op.drop_column("dda_entries", "client_review_status")
