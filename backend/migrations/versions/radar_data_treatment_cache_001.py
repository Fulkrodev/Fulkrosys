"""P1-cobertura-total · CREATE TABLE data_treatment_cache.

Revision: radar_data_treatment_cache_001
Down: radar_narrativa_status_001
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "radar_data_treatment_cache_001"
down_revision: Union[str, None] = "radar_narrativa_status_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "data_treatment_cache",
        sa.Column("objeto_hash", sa.String(length=64), primary_key=True),
        sa.Column("data_treatment", sa.String(length=10), nullable=False),
        sa.Column("sector_sugerido", sa.String(length=50), nullable=True),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column("model", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON data_treatment_cache TO fulkro_app")


def downgrade() -> None:
    op.drop_table("data_treatment_cache")
