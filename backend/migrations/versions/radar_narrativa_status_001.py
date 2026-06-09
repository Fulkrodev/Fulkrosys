"""P1.4 ENS Radar · radar_leads ADD narrativa_status.

Revision: radar_narrativa_status_001
Down: radar_tag_categoria_001
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "radar_narrativa_status_001"
down_revision: Union[str, None] = "radar_tag_categoria_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("radar_leads", sa.Column("narrativa_status", sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column("radar_leads", "narrativa_status")
