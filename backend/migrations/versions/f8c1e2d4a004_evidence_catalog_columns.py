"""ens_measure_evidencia_types: add format + source_tool + automatable + audit_query

Revision ID: f8c1e2d4a004
Revises: a3d1f4c08003
Create Date: 2026-04-21 00:15:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f8c1e2d4a004"
down_revision: Union[str, None] = "a3d1f4c08003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ens_measure_evidencia_types",
        sa.Column("format", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "ens_measure_evidencia_types",
        sa.Column("source_tool", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "ens_measure_evidencia_types",
        sa.Column(
            "automatable",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "ens_measure_evidencia_types",
        sa.Column("audit_query", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ens_measure_evidencia_types", "audit_query")
    op.drop_column("ens_measure_evidencia_types", "automatable")
    op.drop_column("ens_measure_evidencia_types", "source_tool")
    op.drop_column("ens_measure_evidencia_types", "format")
