"""clients: add provincia + numero_empleados

Revision ID: e7a5c1f30002
Revises: d4f8b2a90001
Create Date: 2026-04-20 21:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e7a5c1f30002"
down_revision: Union[str, None] = "d4f8b2a90001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "clients",
        sa.Column("provincia", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "clients",
        sa.Column("numero_empleados", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("clients", "numero_empleados")
    op.drop_column("clients", "provincia")
