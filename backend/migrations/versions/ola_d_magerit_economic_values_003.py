"""ola_d_magerit_economic_values_003 · MAGERIT capa cuantitativa (económica)

feat/fulkro-100 Ola D · gap ALTA. Crea ``magerit_economic_values`` (entrada
económica OPCIONAL por activo) para la capa CUANTITATIVA MAGERIT Libro III sec 2.3
sobre el modelo cualitativo existente. El ALE se deriva on-query (no se persiste).
RLS child 1-level vía ``magerit_analysis.project_id`` (fail-closed).

ADDITIVE · DB-safe (tabla nueva · backward-compat · sin filas = solo cualitativo).

Revision ID: ola_d_magerit_economic_values_003
Revises: ola_d_compensatory_controls_002
Create Date: 2026-06-13
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID

revision: str = "ola_d_magerit_economic_values_003"
down_revision: Union[str, None] = "ola_d_compensatory_controls_002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "magerit_economic_values",
        sa.Column(
            "id", UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"), primary_key=True,
        ),
        sa.Column(
            "created_at", TIMESTAMP(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.Column("updated_at", TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "analysis_id", UUID(as_uuid=True),
            sa.ForeignKey("magerit_analysis.id"), nullable=False,
        ),
        sa.Column(
            "asset_id", UUID(as_uuid=True),
            sa.ForeignKey("magerit_assets.id"), nullable=False,
        ),
        sa.Column("asset_value_eur", sa.Numeric(15, 2), nullable=False),
        sa.Column(
            "exposure_factor", sa.Numeric(5, 4),
            server_default=sa.text("1.0"), nullable=False,
        ),
        sa.UniqueConstraint(
            "analysis_id", "asset_id",
            name="uq_magerit_economic_analysis_asset",
        ),
    )
    op.create_index(
        "ix_magerit_economic_values_analysis_id",
        "magerit_economic_values", ["analysis_id"],
    )

    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON magerit_economic_values "
        "TO fulkro_app, fulkro_app_bypassrls"
    )
    op.execute("ALTER TABLE magerit_economic_values ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE magerit_economic_values FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY project_isolation ON magerit_economic_values USING ("
        "EXISTS (SELECT 1 FROM magerit_analysis a "
        "WHERE a.id = magerit_economic_values.analysis_id "
        "AND a.project_id = current_project_id()))"
    )


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS project_isolation ON magerit_economic_values"
    )
    op.execute(
        "ALTER TABLE magerit_economic_values DISABLE ROW LEVEL SECURITY"
    )
    op.drop_index(
        "ix_magerit_economic_values_analysis_id",
        table_name="magerit_economic_values",
    )
    op.drop_table("magerit_economic_values")
