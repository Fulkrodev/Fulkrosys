"""P0.6 ENS Radar · radar_leads ADD requiere_verificacion_manual + checklist_manual.

Revision: radar_tier_s_manual_001
Down: radar_excluded_leads_001
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "radar_tier_s_manual_001"
down_revision: Union[str, None] = "radar_excluded_leads_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "radar_leads",
        sa.Column(
            "requiere_verificacion_manual", sa.Boolean(),
            nullable=False, server_default=sa.text("true"),
        ),
    )
    op.add_column(
        "radar_leads", sa.Column("checklist_manual", sa.Text(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("radar_leads", "checklist_manual")
    op.drop_column("radar_leads", "requiere_verificacion_manual")
