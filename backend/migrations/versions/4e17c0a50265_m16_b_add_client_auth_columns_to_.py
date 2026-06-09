"""m16-b: add client_auth columns to onboarding_sessions

Revision ID: 4e17c0a50265
Revises: 2b54307cea13
Create Date: 2026-04-16 17:08:53.135669
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '4e17c0a50265'
down_revision: Union[str, None] = '2b54307cea13'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('onboarding_sessions', sa.Column('client_auth_secret_hash', sa.String(120), nullable=True))
    op.add_column('onboarding_sessions', sa.Column('client_auth_issued_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('onboarding_sessions', 'client_auth_issued_at')
    op.drop_column('onboarding_sessions', 'client_auth_secret_hash')
