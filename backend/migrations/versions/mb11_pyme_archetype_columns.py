"""mb11_pyme_archetype_columns

SAN-C MB-11.6 · Añade columnas projects.archetype + archetype_confidence
para 6 arquetipos PYME formal classification (LECCIÓN-OPS LLM-vs-determinismo).

Operación non-breaking: columnas nullable, sin server_default. Projects
existentes mantienen NULL hasta que se ejecute classifier.

Revision ID: mb11_archetype
Revises: mb11_wphase_10
Create Date: 2026-05-05 (SAN-C MB-11.6)
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "mb11_archetype"
down_revision: Union[str, None] = "mb11_wphase_10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("archetype", sa.String(50), nullable=True),
    )
    op.add_column(
        "projects",
        sa.Column("archetype_confidence", sa.Numeric(3, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("projects", "archetype_confidence")
    op.drop_column("projects", "archetype")
