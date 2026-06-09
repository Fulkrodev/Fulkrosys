"""P2 modos de ejecución · radar_pipeline_runs (tipo+métricas) + radar_leads (run marks).

Revision: radar_run_modes_001
Down: radar_cobertura_total_001
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "radar_run_modes_001"
down_revision: Union[str, None] = "radar_cobertura_total_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # radar_pipeline_runs · tipo + métricas diferenciales del run
    op.add_column(
        "radar_pipeline_runs",
        sa.Column("tipo", sa.String(length=20), nullable=False, server_default="full"),
    )
    for col in ("pliegos_nuevos", "leads_nuevos", "certificaciones_nuevas", "caducidades_detectadas"):
        op.add_column(
            "radar_pipeline_runs",
            sa.Column(col, sa.Integer(), nullable=False, server_default="0"),
        )

    # radar_leads · trazabilidad de run
    op.add_column(
        "radar_leads",
        sa.Column("primer_run_id", postgresql_uuid(), nullable=True),
    )
    op.add_column(
        "radar_leads",
        sa.Column("nuevo_en_run", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def postgresql_uuid():
    from sqlalchemy.dialects.postgresql import UUID

    return UUID(as_uuid=True)


def downgrade() -> None:
    op.drop_column("radar_leads", "nuevo_en_run")
    op.drop_column("radar_leads", "primer_run_id")
    for col in ("caducidades_detectadas", "certificaciones_nuevas", "leads_nuevos", "pliegos_nuevos"):
        op.drop_column("radar_pipeline_runs", col)
    op.drop_column("radar_pipeline_runs", "tipo")
