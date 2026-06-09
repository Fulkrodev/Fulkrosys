"""m16-a: extend onboarding_sessions + create onboarding_responses

Revision ID: 2b54307cea13
Revises: 046284bd1ca2
Create Date: 2026-04-16 16:26:34.400094
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '2b54307cea13'
down_revision: Union[str, None] = '046284bd1ca2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Extend onboarding_sessions with M16-A columns
    op.add_column('onboarding_sessions', sa.Column('template_id_str', sa.String(120), nullable=True))
    op.add_column('onboarding_sessions', sa.Column('total_questions', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('onboarding_sessions', sa.Column('answered_questions', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('onboarding_sessions', sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('onboarding_sessions', sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('onboarding_sessions', sa.Column('language', sa.String(5), nullable=True, server_default='es'))
    op.add_column('onboarding_sessions', sa.Column('metadata_extra', sa.dialects.postgresql.JSONB(), nullable=True))
    op.create_index('ix_onboarding_sessions_template_id_str', 'onboarding_sessions', ['template_id_str'])
    op.create_index('ix_onboarding_sessions_expires_at', 'onboarding_sessions', ['expires_at'])
    op.create_index('ix_onboarding_sessions_project_state', 'onboarding_sessions', ['project_id', 'estado'])
    op.create_index('ix_onboarding_sessions_project_role', 'onboarding_sessions', ['project_id', 'rol_receptor'])

    # Create onboarding_responses table
    op.create_table(
        'onboarding_responses',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', sa.dialects.postgresql.UUID(as_uuid=True),
                   sa.ForeignKey('onboarding_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('question_id', sa.String(80), nullable=False),
        sa.Column('section', sa.String(50), nullable=False),
        sa.Column('answer_value', sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column('answered_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_onboarding_responses_session_id', 'onboarding_responses', ['session_id'])
    op.create_index('ix_onboarding_responses_question_id', 'onboarding_responses', ['question_id'])
    op.create_index('ix_onboarding_responses_session_question', 'onboarding_responses',
                     ['session_id', 'question_id'], unique=True)


def downgrade() -> None:
    op.drop_table('onboarding_responses')
    op.drop_index('ix_onboarding_sessions_project_role', table_name='onboarding_sessions')
    op.drop_index('ix_onboarding_sessions_project_state', table_name='onboarding_sessions')
    op.drop_index('ix_onboarding_sessions_expires_at', table_name='onboarding_sessions')
    op.drop_index('ix_onboarding_sessions_template_id_str', table_name='onboarding_sessions')
    op.drop_column('onboarding_sessions', 'metadata_extra')
    op.drop_column('onboarding_sessions', 'language')
    op.drop_column('onboarding_sessions', 'expires_at')
    op.drop_column('onboarding_sessions', 'sent_at')
    op.drop_column('onboarding_sessions', 'answered_questions')
    op.drop_column('onboarding_sessions', 'total_questions')
    op.drop_column('onboarding_sessions', 'template_id_str')
