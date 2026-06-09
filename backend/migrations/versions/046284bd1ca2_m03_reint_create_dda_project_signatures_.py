"""m03-reint: create dda_project_signatures for E-040 RSEG

Revision ID: 046284bd1ca2
Revises: 4cd6b98a6d8c
Create Date: 2026-04-16 15:26:27.670284
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '046284bd1ca2'
down_revision: Union[str, None] = '4cd6b98a6d8c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'dda_project_signatures',
        sa.Column('project_id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('signature_magic_link_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_index(
        'ix_dda_project_signatures_magic_link_id',
        'dda_project_signatures',
        ['signature_magic_link_id'],
    )


def downgrade() -> None:
    op.drop_index('ix_dda_project_signatures_magic_link_id', table_name='dda_project_signatures')
    op.drop_table('dda_project_signatures')
