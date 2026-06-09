"""add_unique_ens_measure_to_magerit_ens_mapping

Revision ID: 3adc8d40b5ea
Revises: 96ac860fe680
Create Date: 2026-04-12 23:50:39.364889
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '3adc8d40b5ea'
down_revision: Union[str, None] = '96ac860fe680'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        'uq_magerit_ens_mapping_ens_measure',
        'magerit_ens_mapping',
        ['ens_measure']
    )


def downgrade() -> None:
    op.drop_constraint(
        'uq_magerit_ens_mapping_ens_measure',
        'magerit_ens_mapping',
        type_='unique'
    )
