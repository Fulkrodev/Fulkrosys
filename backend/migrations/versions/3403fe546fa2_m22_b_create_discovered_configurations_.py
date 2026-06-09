"""m22-b: create discovered_configurations, vulnerability_inventory, discovered_data_stores

Revision ID: 3403fe546fa2
Revises: 50226269fa60
Create Date: 2026-04-17 01:24:16.784451
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "3403fe546fa2"
down_revision: Union[str, None] = "50226269fa60"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _full_mixin_cols():
    """Columnas comunes FullMixin (id UUID PK + created/updated/deleted_at)."""
    return [
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"), primary_key=True,
        ),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    ]


def upgrade() -> None:
    # ========== 1. discovered_configurations ==========
    op.create_table(
        "discovered_configurations",
        *_full_mixin_cols(),
        sa.Column(
            "project_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id"), nullable=False,
        ),
        sa.Column(
            "discovery_run_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("discovery_runs_m22.id"), nullable=False,
        ),
        sa.Column("fuente_conector", sa.String(50), nullable=False),
        sa.Column("sistema", sa.String(300), nullable=False),
        sa.Column("control_id", sa.String(100), nullable=False),
        sa.Column("control_description", sa.Text(), nullable=True),
        sa.Column("estado", sa.String(20), nullable=False),
        sa.Column("valor_actual", sa.Text(), nullable=True),
        sa.Column("valor_esperado", sa.Text(), nullable=True),
        sa.Column("gap_severidad", sa.String(20), nullable=True),
        sa.Column("herramienta_deteccion", sa.String(50), nullable=False),
        sa.Column(
            "medidas_ens_afectadas", postgresql.JSONB(),
            nullable=False, server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "raw_output", postgresql.JSONB(),
            nullable=False, server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "descubierto_at", sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"), nullable=True,
        ),
    )
    op.create_index(
        "ix_discovered_configurations_project_id",
        "discovered_configurations", ["project_id"],
    )
    op.create_index(
        "ix_discovered_configurations_discovery_run_id",
        "discovered_configurations", ["discovery_run_id"],
    )
    op.create_index(
        "ix_discovered_configurations_gap_severidad",
        "discovered_configurations", ["gap_severidad"],
    )
    op.create_index(
        "ix_discovered_configurations_project_gap",
        "discovered_configurations", ["project_id", "gap_severidad"],
    )

    # ========== 2. vulnerability_inventory ==========
    op.create_table(
        "vulnerability_inventory",
        *_full_mixin_cols(),
        sa.Column(
            "project_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id"), nullable=False,
        ),
        sa.Column(
            "discovery_run_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("discovery_runs_m22.id"), nullable=False,
        ),
        sa.Column("fuente", sa.String(50), nullable=False),
        sa.Column("titulo", sa.String(500), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("cve_id", sa.String(30), nullable=True),
        sa.Column("cvss_score", sa.Float(), nullable=True),
        sa.Column("cvss_vector", sa.String(100), nullable=True),
        sa.Column("cvss_severity", sa.String(20), nullable=True),
        sa.Column("asset_afectado", sa.String(500), nullable=True),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("es_explotable", sa.Boolean(), nullable=True),
        sa.Column("exploit_disponible", sa.Boolean(), nullable=True),
        sa.Column("remediacion_sugerida", sa.Text(), nullable=True),
        sa.Column(
            "medidas_ens_afectadas", postgresql.JSONB(),
            nullable=False, server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "mitre_tactics", postgresql.JSONB(),
            nullable=False, server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "estado", sa.String(20), nullable=False, server_default="open",
        ),
        sa.Column(
            "raw_finding", postgresql.JSONB(),
            nullable=False, server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "descubierto_at", sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"), nullable=True,
        ),
    )
    op.create_index(
        "ix_vulnerability_inventory_project_id",
        "vulnerability_inventory", ["project_id"],
    )
    op.create_index(
        "ix_vulnerability_inventory_discovery_run_id",
        "vulnerability_inventory", ["discovery_run_id"],
    )
    op.create_index(
        "ix_vulnerability_inventory_cve_id",
        "vulnerability_inventory", ["cve_id"],
    )
    op.create_index(
        "ix_vulnerability_inventory_cvss_severity",
        "vulnerability_inventory", ["cvss_severity"],
    )
    op.create_index(
        "ix_vulnerability_inventory_project_severity",
        "vulnerability_inventory", ["project_id", "cvss_severity"],
    )

    # ========== 3. discovered_data_stores ==========
    op.create_table(
        "discovered_data_stores",
        *_full_mixin_cols(),
        sa.Column(
            "project_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id"), nullable=False,
        ),
        sa.Column(
            "discovery_run_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("discovery_runs_m22.id"), nullable=False,
        ),
        sa.Column("fuente_conector", sa.String(50), nullable=False),
        sa.Column("tipo", sa.String(50), nullable=False),
        sa.Column("nombre", sa.String(300), nullable=False),
        sa.Column("ubicacion", sa.String(500), nullable=False),
        sa.Column("volumen_estimado_gb", sa.Float(), nullable=True),
        sa.Column(
            "clasificacion_inicial", sa.String(30),
            nullable=False, server_default="sin_clasificar",
        ),
        sa.Column(
            "patrones_detectados", postgresql.JSONB(),
            nullable=False, server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("tiene_datos_personales", sa.Boolean(), nullable=True),
        sa.Column("tiene_datos_salud", sa.Boolean(), nullable=True),
        sa.Column("tiene_datos_financieros", sa.Boolean(), nullable=True),
        sa.Column("cifrado_en_reposo", sa.Boolean(), nullable=True),
        sa.Column("cifrado_en_transito", sa.Boolean(), nullable=True),
        sa.Column("control_acceso", sa.String(50), nullable=True),
        sa.Column("tiene_backup", sa.Boolean(), nullable=True),
        sa.Column(
            "metadata_extra", postgresql.JSONB(),
            nullable=False, server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("pkg_node_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "descubierto_at", sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"), nullable=True,
        ),
    )
    op.create_index(
        "ix_discovered_data_stores_project_id",
        "discovered_data_stores", ["project_id"],
    )
    op.create_index(
        "ix_discovered_data_stores_discovery_run_id",
        "discovered_data_stores", ["discovery_run_id"],
    )
    op.create_index(
        "ix_discovered_data_stores_project_clasificacion",
        "discovered_data_stores", ["project_id", "clasificacion_inicial"],
    )

    # ========== RLS ==========
    for table in (
        "discovered_configurations",
        "vulnerability_inventory",
        "discovered_data_stores",
    ):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY project_isolation ON {table} "
            f"USING (project_id = current_project_id())"
        )


def downgrade() -> None:
    for table in (
        "discovered_configurations",
        "vulnerability_inventory",
        "discovered_data_stores",
    ):
        op.execute(f"DROP POLICY IF EXISTS project_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    op.drop_index(
        "ix_discovered_data_stores_project_clasificacion",
        table_name="discovered_data_stores",
    )
    op.drop_index(
        "ix_discovered_data_stores_discovery_run_id",
        table_name="discovered_data_stores",
    )
    op.drop_index(
        "ix_discovered_data_stores_project_id",
        table_name="discovered_data_stores",
    )
    op.drop_table("discovered_data_stores")

    op.drop_index(
        "ix_vulnerability_inventory_project_severity",
        table_name="vulnerability_inventory",
    )
    op.drop_index(
        "ix_vulnerability_inventory_cvss_severity",
        table_name="vulnerability_inventory",
    )
    op.drop_index(
        "ix_vulnerability_inventory_cve_id",
        table_name="vulnerability_inventory",
    )
    op.drop_index(
        "ix_vulnerability_inventory_discovery_run_id",
        table_name="vulnerability_inventory",
    )
    op.drop_index(
        "ix_vulnerability_inventory_project_id",
        table_name="vulnerability_inventory",
    )
    op.drop_table("vulnerability_inventory")

    op.drop_index(
        "ix_discovered_configurations_project_gap",
        table_name="discovered_configurations",
    )
    op.drop_index(
        "ix_discovered_configurations_gap_severidad",
        table_name="discovered_configurations",
    )
    op.drop_index(
        "ix_discovered_configurations_discovery_run_id",
        table_name="discovered_configurations",
    )
    op.drop_index(
        "ix_discovered_configurations_project_id",
        table_name="discovered_configurations",
    )
    op.drop_table("discovered_configurations")
