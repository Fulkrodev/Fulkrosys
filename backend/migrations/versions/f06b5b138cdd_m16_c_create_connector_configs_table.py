"""m16-c: create connector_configs table

Revision ID: f06b5b138cdd
Revises: 4e17c0a50265
Create Date: 2026-04-16 17:52:01.382305
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f06b5b138cdd'
down_revision: Union[str, None] = '4e17c0a50265'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'connector_configs',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('provider', sa.String(40), nullable=False, index=True),
        sa.Column('encrypted_credentials', sa.LargeBinary, nullable=False),
        sa.Column('scopes', sa.String(500), nullable=True),
        sa.Column('status', sa.String(30), nullable=False, server_default='configured'),
        sa.Column('last_discovery_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('discovery_result_summary', sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
    )
    op.create_index('ix_connector_configs_project_provider', 'connector_configs', ['project_id', 'provider'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_connector_configs_project_provider', table_name='connector_configs')
    op.drop_table('connector_configs')
