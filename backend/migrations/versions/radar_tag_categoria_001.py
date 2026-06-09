"""P1.3 ENS Radar · radar_leads ADD tag_categoria + revisar_tamano_empresa.

Revision: radar_tag_categoria_001
Down: radar_icp_manual_001
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "radar_tag_categoria_001"
down_revision: Union[str, None] = "radar_icp_manual_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("radar_leads", sa.Column("tag_categoria", sa.String(length=20), nullable=True))
    op.add_column(
        "radar_leads",
        sa.Column(
            "revisar_tamano_empresa", sa.Boolean(),
            nullable=False, server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("radar_leads", "revisar_tamano_empresa")
    op.drop_column("radar_leads", "tag_categoria")
