"""add ens_measures applicability columns for DdA engine

Revision ID: b4d3ebb9628e
Revises: 5ec092800a5d
Create Date: 2026-04-13 22:56:57.781979
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'b4d3ebb9628e'
down_revision: Union[str, None] = '5ec092800a5d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 5 new columns for Motor 3 DdA Engine (Bloque 14)
    # NOTE: Alembic autogenerate false positives for drop_constraint on
    # uq_magerit_ens_mapping_ens_measure and uq_risk_matrix_impact_prob
    # removed (same issue as migration 5ec092800a5d).
    op.add_column('ens_measures', sa.Column('aplica_basica', sa.Boolean(), server_default='true', nullable=False))
    op.add_column('ens_measures', sa.Column('aplica_media', sa.Boolean(), server_default='true', nullable=False))
    op.add_column('ens_measures', sa.Column('aplica_alta', sa.Boolean(), server_default='true', nullable=False))
    op.add_column('ens_measures', sa.Column('categoria_minima', sa.String(length=10), nullable=True))
    op.add_column('ens_measures', sa.Column('dimensiones_aplicables', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('ens_measures', 'dimensiones_aplicables')
    op.drop_column('ens_measures', 'categoria_minima')
    op.drop_column('ens_measures', 'aplica_alta')
    op.drop_column('ens_measures', 'aplica_media')
    op.drop_column('ens_measures', 'aplica_basica')
