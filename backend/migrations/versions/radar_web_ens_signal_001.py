"""P0.4 ENS Radar · ALTER companies ADD web_ens_signal + web_ens_checked_at.

Revision: radar_web_ens_signal_001
Down: radar_cif_status_001
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "radar_web_ens_signal_001"
down_revision: Union[str, None] = "radar_cif_status_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("companies", sa.Column("web_ens_signal", sa.String(length=30), nullable=True))
    op.add_column("companies", sa.Column("web_ens_checked_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("companies", "web_ens_checked_at")
    op.drop_column("companies", "web_ens_signal")
