"""san_e_mb5_4b_threat_assessment_client_review

ADR-020 v6 SAN-E v3.MB-5.4.B · cliente review análisis riesgos MAGERIT.

Schema diferente vs assets (UUIDPrimaryKeyMixin sin deleted_at) ·
adaptación migration · 4 cols cliente review en magerit_threat_assessment.

Pattern alineado atom 5.4.A.

Revision ID: 210b0b0f82ad
Revises: 1c60787eec4d
Create Date: 2026-05-10 21:18:31.746036
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = '210b0b0f82ad'
down_revision: Union[str, None] = '1c60787eec4d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "magerit_threat_assessment",
        sa.Column("client_review_status", sa.String(30), nullable=True),
    )
    op.add_column(
        "magerit_threat_assessment",
        sa.Column("client_review_note", sa.Text, nullable=True),
    )
    op.add_column(
        "magerit_threat_assessment",
        sa.Column(
            "client_reviewed_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "magerit_threat_assessment",
        sa.Column(
            "client_reviewed_by_user_id", UUID(as_uuid=True), nullable=True,
        ),
    )

    op.execute("""
        ALTER TABLE magerit_threat_assessment
        ADD CONSTRAINT ck_magerit_threat_assessment_client_review_status
        CHECK (client_review_status IS NULL OR client_review_status IN (
            'revisada_ok', 'con_pregunta', 'suggest_change'
        ))
    """)

    op.create_index(
        "idx_magerit_threat_assessment_client_review",
        "magerit_threat_assessment",
        ["analysis_id", "client_review_status"],
        postgresql_where=sa.text("client_review_status IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "idx_magerit_threat_assessment_client_review",
        table_name="magerit_threat_assessment",
    )
    op.execute(
        "ALTER TABLE magerit_threat_assessment DROP CONSTRAINT IF EXISTS "
        "ck_magerit_threat_assessment_client_review_status"
    )
    op.drop_column(
        "magerit_threat_assessment", "client_reviewed_by_user_id",
    )
    op.drop_column("magerit_threat_assessment", "client_reviewed_at")
    op.drop_column("magerit_threat_assessment", "client_review_note")
    op.drop_column("magerit_threat_assessment", "client_review_status")
