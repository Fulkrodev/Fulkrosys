"""P0.3 ENS Radar · ALTER companies ADD cif_status.

ADD column cif_status VARCHAR(20) NULL ('ok' | 'pendiente_manual').

Revision: radar_cif_status_001
Down: ccn_certs_scraper_cols_001
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "radar_cif_status_001"
down_revision: Union[str, None] = "ccn_certs_scraper_cols_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "companies", sa.Column("cif_status", sa.String(length=20), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("companies", "cif_status")
