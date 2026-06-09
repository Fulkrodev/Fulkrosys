"""m22-a: create discovery_runs_m22 and discovery_alerts, extend discovered_assets/identities

Revision ID: 50226269fa60
Revises: 1b32bac44237
Create Date: 2026-04-17 01:00:15.802486
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "50226269fa60"
down_revision: Union[str, None] = "1b32bac44237"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ========== 1. discovery_runs_m22 ==========
    op.create_table(
        "discovery_runs_m22",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"), primary_key=True,
        ),
        sa.Column(
            "project_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id"), nullable=False,
        ),
        sa.Column("modules", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("connector_sources", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("progress", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("error_details", sa.Text(), nullable=True),
        sa.Column("triggered_by", sa.String(50), nullable=False, server_default="manual"),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_discovery_runs_m22_project_id", "discovery_runs_m22", ["project_id"],
    )
    op.create_index(
        "ix_discovery_runs_m22_project_status", "discovery_runs_m22",
        ["project_id", "status"],
    )

    # ========== 2. discovery_alerts ==========
    op.create_table(
        "discovery_alerts",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            nullable=False, primary_key=True,
        ),
        sa.Column(
            "project_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id"), nullable=False,
        ),
        sa.Column(
            "discovery_run_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("discovery_runs_m22.id"), nullable=False,
        ),
        sa.Column("modulo", sa.String(30), nullable=False),
        sa.Column("severidad", sa.String(20), nullable=False),
        sa.Column("codigo", sa.String(50), nullable=False),
        sa.Column("titulo", sa.String(300), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "medidas_ens_afectadas", postgresql.JSONB(),
            nullable=False, server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("gap_volcado", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("gap_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_discovery_alerts_project_id", "discovery_alerts", ["project_id"],
    )
    op.create_index(
        "ix_discovery_alerts_discovery_run_id", "discovery_alerts", ["discovery_run_id"],
    )
    op.create_index(
        "ix_discovery_alerts_severidad", "discovery_alerts", ["severidad"],
    )
    op.create_index(
        "ix_discovery_alerts_project_severidad", "discovery_alerts",
        ["project_id", "severidad"],
    )

    # ========== 3. Extender discovered_assets ==========
    op.add_column(
        "discovered_assets",
        sa.Column(
            "discovery_run_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("discovery_runs_m22.id"), nullable=True,
        ),
    )
    op.create_index(
        "ix_discovered_assets_discovery_run_id", "discovered_assets", ["discovery_run_id"],
    )
    op.add_column(
        "discovered_assets",
        sa.Column("descripcion", sa.Text(), nullable=True),
    )
    op.add_column(
        "discovered_assets",
        sa.Column("pkg_node_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    # ========== 4. Extender discovered_identities ==========
    op.add_column(
        "discovered_identities",
        sa.Column(
            "discovery_run_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("discovery_runs_m22.id"), nullable=True,
        ),
    )
    op.create_index(
        "ix_discovered_identities_discovery_run_id", "discovered_identities", ["discovery_run_id"],
    )
    op.add_column(
        "discovered_identities",
        sa.Column("display_name", sa.String(300), nullable=True),
    )
    op.add_column(
        "discovered_identities",
        sa.Column("tipo_cuenta", sa.String(30), nullable=True),
    )
    op.add_column(
        "discovered_identities",
        sa.Column("es_activa", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "discovered_identities",
        sa.Column("password_policy_compliant", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "discovered_identities",
        sa.Column("pkg_node_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    # ========== 5. RLS en nuevas tablas ==========
    for table in ("discovery_runs_m22", "discovery_alerts"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY project_isolation ON {table} "
            f"USING (project_id = current_project_id())"
        )


def downgrade() -> None:
    # RLS
    for table in ("discovery_runs_m22", "discovery_alerts"):
        op.execute(f"DROP POLICY IF EXISTS project_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    # discovered_identities extras
    op.drop_column("discovered_identities", "pkg_node_id")
    op.drop_column("discovered_identities", "password_policy_compliant")
    op.drop_column("discovered_identities", "es_activa")
    op.drop_column("discovered_identities", "tipo_cuenta")
    op.drop_column("discovered_identities", "display_name")
    op.drop_index("ix_discovered_identities_discovery_run_id", table_name="discovered_identities")
    op.drop_column("discovered_identities", "discovery_run_id")

    # discovered_assets extras
    op.drop_column("discovered_assets", "pkg_node_id")
    op.drop_column("discovered_assets", "descripcion")
    op.drop_index("ix_discovered_assets_discovery_run_id", table_name="discovered_assets")
    op.drop_column("discovered_assets", "discovery_run_id")

    # discovery_alerts
    op.drop_index("ix_discovery_alerts_project_severidad", table_name="discovery_alerts")
    op.drop_index("ix_discovery_alerts_severidad", table_name="discovery_alerts")
    op.drop_index("ix_discovery_alerts_discovery_run_id", table_name="discovery_alerts")
    op.drop_index("ix_discovery_alerts_project_id", table_name="discovery_alerts")
    op.drop_table("discovery_alerts")

    # discovery_runs_m22
    op.drop_index("ix_discovery_runs_m22_project_status", table_name="discovery_runs_m22")
    op.drop_index("ix_discovery_runs_m22_project_id", table_name="discovery_runs_m22")
    op.drop_table("discovery_runs_m22")
