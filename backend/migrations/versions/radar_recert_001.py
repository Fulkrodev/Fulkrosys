"""P2 (C6) · radar_leads ADD recert_oportunidad + reason_reactivacion.

Revision: radar_recert_001
Down: radar_run_modes_001
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "radar_recert_001"
down_revision: Union[str, None] = "radar_run_modes_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "radar_leads",
        sa.Column("recert_oportunidad", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "radar_leads",
        sa.Column("reason_reactivacion", sa.String(length=40), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("radar_leads", "reason_reactivacion")
    op.drop_column("radar_leads", "recert_oportunidad")
