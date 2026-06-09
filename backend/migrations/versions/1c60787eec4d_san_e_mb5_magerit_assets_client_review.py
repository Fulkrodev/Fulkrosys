"""san_e_mb5_magerit_assets_client_review

ADR-020 v6 SAN-E v3.MB-5.4 · cliente review activos MAGERIT in-portal.

Replica pattern atom 5.0.bis · 5.3.A (dda_entries) en magerit_assets.
Cliente revisa cada activo · marca review (revisada_ok · con_pregunta ·
suggest_change). Q5.3: cliente NO edita valoración DICAT (admin owns) ·
solo review.

4 cols aditivas backwards compatible:
- client_review_status (String 30 nullable · CHECK constraint enum 3)
- client_review_note (Text nullable)
- client_reviewed_at (TIMESTAMP timezone nullable)
- client_reviewed_by_user_id (UUID nullable)

Index parcial: idx_magerit_assets_client_review (analysis_id,
client_review_status) WHERE NOT NULL · acelera summary cliente.

NOTA scope MB-5.4 sub-atom A: solo assets · risks (magerit_threat_assessment)
defer follow-up sub-atom (schema diferente · UUIDPrimaryKeyMixin sin
deleted_at · re-enfoque cuando se implemente RiskRow review).

Revision ID: 1c60787eec4d
Revises: 78d80ba049de
Create Date: 2026-05-10 20:54:51.468717
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = '1c60787eec4d'
down_revision: Union[str, None] = '78d80ba049de'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "magerit_assets",
        sa.Column("client_review_status", sa.String(30), nullable=True),
    )
    op.add_column(
        "magerit_assets",
        sa.Column("client_review_note", sa.Text, nullable=True),
    )
    op.add_column(
        "magerit_assets",
        sa.Column(
            "client_reviewed_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "magerit_assets",
        sa.Column(
            "client_reviewed_by_user_id", UUID(as_uuid=True), nullable=True,
        ),
    )

    op.execute("""
        ALTER TABLE magerit_assets
        ADD CONSTRAINT ck_magerit_assets_client_review_status
        CHECK (client_review_status IS NULL OR client_review_status IN (
            'revisada_ok', 'con_pregunta', 'suggest_change'
        ))
    """)

    op.create_index(
        "idx_magerit_assets_client_review",
        "magerit_assets",
        ["analysis_id", "client_review_status"],
        postgresql_where=sa.text("client_review_status IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "idx_magerit_assets_client_review",
        table_name="magerit_assets",
    )
    op.execute(
        "ALTER TABLE magerit_assets DROP CONSTRAINT IF EXISTS "
        "ck_magerit_assets_client_review_status"
    )
    op.drop_column("magerit_assets", "client_reviewed_by_user_id")
    op.drop_column("magerit_assets", "client_reviewed_at")
    op.drop_column("magerit_assets", "client_review_note")
    op.drop_column("magerit_assets", "client_review_status")
