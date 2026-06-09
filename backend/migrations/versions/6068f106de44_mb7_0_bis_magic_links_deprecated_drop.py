"""mb7_0_bis_magic_links_deprecated_drop

Revision ID: 6068f106de44
Revises: 5eaaaaee3714
Create Date: 2026-05-11

SAN-E v3.atom MB-7.0.bis · drop legacy magic_links.deprecated_for_v3 column.

Column added en ADR-020 v3 migration original (SAN-E MB-4.bis3) para soft-deprecate
21 magic_link cliente purposes. ADR-020 IMPLEMENTED FULLY · hard-deprecation done ·
column ya NO referenced en code. Drop column + index for clean state pre-MB-7.

Reversible · downgrade restora column con default false.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '6068f106de44'
down_revision: Union[str, None] = '5eaaaaee3714'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index(
        "ix_magic_links_deprecated_for_v3",
        table_name="magic_links",
    )
    op.drop_column("magic_links", "deprecated_for_v3")


def downgrade() -> None:
    op.add_column(
        "magic_links",
        sa.Column(
            "deprecated_for_v3",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_index(
        "ix_magic_links_deprecated_for_v3",
        "magic_links",
        ["deprecated_for_v3"],
        unique=False,
    )
