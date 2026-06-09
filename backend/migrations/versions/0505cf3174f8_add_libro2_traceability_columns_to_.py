"""add libro2 traceability columns to magerit_threats

Revision ID: 0505cf3174f8
Revises: b4d3ebb9628e
Create Date: 2026-04-13 23:42:06.297933
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0505cf3174f8'
down_revision: Union[str, None] = 'b4d3ebb9628e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Libro II traceability columns (Bloque 15)
    # NOTE: 4th occurrence of Alembic autogenerate spurious drop_constraint
    # for uq_magerit_ens_mapping_ens_measure + uq_risk_matrix_impact_prob.
    # Removed. See TODO-CRITICO-ALEMBIC in progress/todos.md.
    op.add_column('magerit_threats', sa.Column('official_description', sa.Text(), nullable=True))
    op.add_column('magerit_threats', sa.Column('official_source', sa.String(length=200), nullable=True))


def downgrade() -> None:
    op.drop_column('magerit_threats', 'official_source')
    op.drop_column('magerit_threats', 'official_description')
