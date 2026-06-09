"""add_input_snapshot_to_categorizations

Revision ID: 6689f3423dcf
Revises: 8340982461b9
Create Date: 2026-04-13 03:23:36.530846
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '6689f3423dcf'
down_revision: Union[str, None] = '8340982461b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Snapshot inmutable del input usado en cada cálculo de categorización.
    # Nullable porque filas históricas previas no tenían snapshot.
    # Nuevos cálculos SIEMPRE lo escribirán a partir de ahora.
    op.add_column(
        'categorizations',
        sa.Column('input_snapshot', sa.dialects.postgresql.JSONB, nullable=True)
    )


def downgrade() -> None:
    op.drop_column('categorizations', 'input_snapshot')
