"""m02-reint: add signature_magic_link_id to magerit_analysis

Revision ID: 4cd6b98a6d8c
Revises: 83a6ea69a35a
Create Date: 2026-04-16 14:41:48.807996
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '4cd6b98a6d8c'
down_revision: Union[str, None] = '83a6ea69a35a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'magerit_analysis',
        sa.Column('signature_magic_link_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        'ix_magerit_analysis_signature_magic_link_id',
        'magerit_analysis',
        ['signature_magic_link_id'],
    )


def downgrade() -> None:
    op.drop_index('ix_magerit_analysis_signature_magic_link_id', table_name='magerit_analysis')
    op.drop_column('magerit_analysis', 'signature_magic_link_id')
