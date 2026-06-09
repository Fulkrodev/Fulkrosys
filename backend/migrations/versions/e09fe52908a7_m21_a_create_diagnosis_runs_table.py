"""m21-a: create diagnosis_runs table

Revision ID: e09fe52908a7
Revises: 6ec4057829bb
Create Date: 2026-04-16 20:01:48.614994
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e09fe52908a7'
down_revision: Union[str, None] = '6ec4057829bb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'diagnosis_runs',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(30), nullable=False, server_default='running'),
        sa.Column('triggered_by', sa.String(120), nullable=True),
        sa.Column('stakeholder_analysis', sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column('process_inventory', sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column('compliance_detection', sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column('maturity_scoring', sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column('summary', sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column('confidential_notes_encrypted', sa.LargeBinary, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_diagnosis_runs_project_status', 'diagnosis_runs', ['project_id', 'status'])


def downgrade() -> None:
    op.drop_table('diagnosis_runs')
