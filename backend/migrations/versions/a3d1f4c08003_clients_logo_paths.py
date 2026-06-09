"""clients: logo_path + logo_mime_type

Revision ID: a3d1f4c08003
Revises: e7a5c1f30002
Create Date: 2026-04-20 23:45:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a3d1f4c08003"
down_revision: Union[str, None] = "e7a5c1f30002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "clients",
        sa.Column("logo_path", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "clients",
        sa.Column("logo_mime_type", sa.String(length=80), nullable=True),
    )
    op.add_column(
        "clients",
        sa.Column("logo_sha256", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("clients", "logo_sha256")
    op.drop_column("clients", "logo_mime_type")
    op.drop_column("clients", "logo_path")
