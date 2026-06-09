"""m01-reint: add signature_magic_link_id to categorizations

Revision ID: 83a6ea69a35a
Revises: eb0a885d141a
Create Date: 2026-04-16 14:10:09.491998
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '83a6ea69a35a'
down_revision: Union[str, None] = 'eb0a885d141a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'categorizations',
        sa.Column('signature_magic_link_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        'ix_categorizations_signature_magic_link_id',
        'categorizations',
        ['signature_magic_link_id'],
    )


def downgrade() -> None:
    op.drop_index('ix_categorizations_signature_magic_link_id', table_name='categorizations')
    op.drop_column('categorizations', 'signature_magic_link_id')
