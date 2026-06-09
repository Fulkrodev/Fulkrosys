"""P0.5 ENS Radar · CREATE TABLE excluded_leads (exclusión persistente).

Revision: radar_excluded_leads_001
Down: radar_web_ens_signal_001
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "radar_excluded_leads_001"
down_revision: Union[str, None] = "radar_web_ens_signal_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "excluded_leads",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cif_norm", sa.String(length=20), nullable=True),
        sa.Column("razon_social_norm", sa.String(length=500), nullable=True),
        sa.Column("reason", sa.String(length=20), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("idx_excluded_cif_norm", "excluded_leads", ["cif_norm"])
    op.create_index("idx_excluded_razon_norm", "excluded_leads", ["razon_social_norm"])
    # GRANT runtime (fulkro_app es NOSUPERUSER · RLS enforced).
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON excluded_leads TO fulkro_app")
    op.execute("GRANT USAGE, SELECT ON SEQUENCE excluded_leads_id_seq TO fulkro_app")


def downgrade() -> None:
    op.drop_index("idx_excluded_razon_norm", table_name="excluded_leads")
    op.drop_index("idx_excluded_cif_norm", table_name="excluded_leads")
    op.drop_table("excluded_leads")
