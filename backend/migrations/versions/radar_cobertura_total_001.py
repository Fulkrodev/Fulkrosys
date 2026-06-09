"""P1-cobertura-total · tenders ADD sector + data_treatment + ens_borderline.

Revision: radar_cobertura_total_001
Down: radar_data_treatment_cache_001
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "radar_cobertura_total_001"
down_revision: Union[str, None] = "radar_data_treatment_cache_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tenders", sa.Column("sector", sa.String(length=50), nullable=True))
    op.add_column("tenders", sa.Column("data_treatment", sa.String(length=10), nullable=True))
    op.add_column(
        "tenders",
        sa.Column("ens_borderline", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("tenders", "ens_borderline")
    op.drop_column("tenders", "data_treatment")
    op.drop_column("tenders", "sector")
