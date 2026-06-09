"""fase_9_0_drop_ens_reinforcements_legacy

Revision ID: 83e27091b489
Revises: c6f5ff65d8be
Create Date: 2026-05-02 13:21:45.222710
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '83e27091b489'
down_revision: Union[str, None] = 'c6f5ff65d8be'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
