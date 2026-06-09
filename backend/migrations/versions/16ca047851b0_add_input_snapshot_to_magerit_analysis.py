"""add_input_snapshot_to_magerit_analysis

Revision ID: 16ca047851b0
Revises: 6689f3423dcf
Create Date: 2026-04-13 13:19:39.918052
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '16ca047851b0'
down_revision: Union[str, None] = '6689f3423dcf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Frozen snapshot of the complete analysis state for client delivery.
    # result_snapshot: JSONB with all assets, threats, calcs, treatment plan.
    # snapshot_frozen_at: timestamp when the analysis was frozen. NULL = unfrozen.
    # Both nullable for backward compatibility and unfrozen state.
    op.add_column(
        'magerit_analysis',
        sa.Column('result_snapshot', sa.dialects.postgresql.JSONB, nullable=True)
    )
    op.add_column(
        'magerit_analysis',
        sa.Column('snapshot_frozen_at', sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('magerit_analysis', 'snapshot_frozen_at')
    op.drop_column('magerit_analysis', 'result_snapshot')
