"""add magic_link columns: revoked_at otp_failures recipient_email allowed_countries

Revision ID: 5ec092800a5d
Revises: 16ca047851b0
Create Date: 2026-04-13 17:19:10.428617
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '5ec092800a5d'
down_revision: Union[str, None] = '16ca047851b0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 4 new columns for Motor 12 Magic Link Engine (Bloque 13)
    # NOTE: Alembic autogenerate falsely detected drop_constraint for
    # uq_magerit_ens_mapping_ens_measure and uq_risk_matrix_impact_prob.
    # These constraints exist in DB with different naming. Removed to
    # avoid destroying Motor 2 integrity constraints.
    op.add_column('magic_links', sa.Column('revoked_at', postgresql.TIMESTAMP(timezone=True), nullable=True))
    op.add_column('magic_links', sa.Column('otp_failures', sa.Integer(), server_default='0', nullable=False))
    op.add_column('magic_links', sa.Column('recipient_email', sa.String(length=255), nullable=True))
    op.add_column('magic_links', sa.Column('allowed_countries', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('magic_links', 'allowed_countries')
    op.drop_column('magic_links', 'recipient_email')
    op.drop_column('magic_links', 'otp_failures')
    op.drop_column('magic_links', 'revoked_at')
