"""m16-e: create pkg_nodes and pkg_edges tables

Revision ID: 6ec4057829bb
Revises: f06b5b138cdd
Create Date: 2026-04-16 18:17:35.439899
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '6ec4057829bb'
down_revision: Union[str, None] = 'f06b5b138cdd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'pkg_nodes',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('node_type', sa.String(40), nullable=False),
        sa.Column('label', sa.String(300), nullable=False),
        sa.Column('external_id', sa.String(200), nullable=True),
        sa.Column('properties', sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index('ix_pkg_nodes_project_type', 'pkg_nodes', ['project_id', 'node_type'])
    op.create_index('ix_pkg_nodes_project_external', 'pkg_nodes', ['project_id', 'external_id'])

    op.create_table(
        'pkg_edges',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_node_id', sa.dialects.postgresql.UUID(as_uuid=True),
                   sa.ForeignKey('pkg_nodes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('target_node_id', sa.dialects.postgresql.UUID(as_uuid=True),
                   sa.ForeignKey('pkg_nodes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('edge_type', sa.String(40), nullable=False),
        sa.Column('properties', sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index('ix_pkg_edges_project_type', 'pkg_edges', ['project_id', 'edge_type'])
    op.create_index('ix_pkg_edges_source', 'pkg_edges', ['source_node_id'])
    op.create_index('ix_pkg_edges_target', 'pkg_edges', ['target_node_id'])


def downgrade() -> None:
    op.drop_table('pkg_edges')
    op.drop_table('pkg_nodes')
