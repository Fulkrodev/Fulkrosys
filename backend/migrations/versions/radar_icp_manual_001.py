"""P1.2 ENS Radar · companies ADD forma_juridica + es_persona_fisica + flag_posible_multinacional.

Revision: radar_icp_manual_001
Down: radar_tier_s_manual_001
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "radar_icp_manual_001"
down_revision: Union[str, None] = "radar_tier_s_manual_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("companies", sa.Column("forma_juridica", sa.String(length=20), nullable=True))
    op.add_column("companies", sa.Column("es_persona_fisica", sa.Boolean(), nullable=True))
    op.add_column("companies", sa.Column("flag_posible_multinacional", sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column("companies", "flag_posible_multinacional")
    op.drop_column("companies", "es_persona_fisica")
    op.drop_column("companies", "forma_juridica")
