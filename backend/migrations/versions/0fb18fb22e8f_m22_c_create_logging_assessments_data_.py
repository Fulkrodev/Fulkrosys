"""m22-c: create logging_assessments, data_flow_diagrams, continuity_assessments

Revision ID: 0fb18fb22e8f
Revises: 3403fe546fa2
Create Date: 2026-04-17 01:52:06.215180
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0fb18fb22e8f"
down_revision: Union[str, None] = "3403fe546fa2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _full_mixin_cols():
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
    # ========== 1. logging_assessments ==========
    op.create_table(
        "logging_assessments",
        *_full_mixin_cols(),
        sa.Column(
            "project_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id"), nullable=False,
        ),
        sa.Column(
            "discovery_run_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("discovery_runs_m22.id"), nullable=False,
        ),
        sa.Column("tiene_siem", sa.Boolean(), nullable=True),
        sa.Column("siem_producto", sa.String(100), nullable=True),
        sa.Column(
            "fuentes_log", postgresql.JSONB(),
            nullable=False, server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("cobertura_servidores_pct", sa.Integer(), nullable=True),
        sa.Column("cobertura_red_pct", sa.Integer(), nullable=True),
        sa.Column("cobertura_aplicaciones_pct", sa.Integer(), nullable=True),
        sa.Column("cobertura_endpoints_pct", sa.Integer(), nullable=True),
        sa.Column("retencion_minima_dias", sa.Integer(), nullable=True),
        sa.Column("retencion_maxima_dias", sa.Integer(), nullable=True),
        sa.Column("cumple_retencion_ens", sa.Boolean(), nullable=True),
        sa.Column("tiene_alertas_activas", sa.Boolean(), nullable=True),
        sa.Column("alertas_revisadas_por", sa.String(200), nullable=True),
        sa.Column("casos_uso_activos", sa.Integer(), nullable=True),
        sa.Column("cumple_op_exp_8", sa.Boolean(), nullable=True),
        sa.Column(
            "gaps_op_exp_8", postgresql.JSONB(),
            nullable=False, server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "nivel_madurez_logging", sa.String(10),
            nullable=False, server_default="L0",
        ),
        sa.Column("observaciones", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_logging_assessments_project_id", "logging_assessments", ["project_id"],
    )
    op.create_index(
        "ix_logging_assessments_discovery_run_id",
        "logging_assessments", ["discovery_run_id"],
    )

    # ========== 2. data_flow_diagrams ==========
    op.create_table(
        "data_flow_diagrams",
        *_full_mixin_cols(),
        sa.Column(
            "project_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id"), nullable=False,
        ),
        sa.Column(
            "discovery_run_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("discovery_runs_m22.id"), nullable=False,
        ),
        sa.Column("nombre", sa.String(300), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("tipo", sa.String(50), nullable=False),
        sa.Column(
            "nodos", postgresql.JSONB(),
            nullable=False, server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "flujos", postgresql.JSONB(),
            nullable=False, server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "clasificacion_max_datos", sa.String(30),
            nullable=False, server_default="sin_clasificar",
        ),
        sa.Column("mermaid_code", sa.Text(), nullable=True),
        sa.Column(
            "observaciones_seguridad", postgresql.JSONB(),
            nullable=False, server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.create_index(
        "ix_data_flow_diagrams_project_id", "data_flow_diagrams", ["project_id"],
    )
    op.create_index(
        "ix_data_flow_diagrams_discovery_run_id",
        "data_flow_diagrams", ["discovery_run_id"],
    )
    op.create_index(
        "ix_data_flow_diagrams_project_tipo",
        "data_flow_diagrams", ["project_id", "tipo"],
    )

    # ========== 3. continuity_assessments ==========
    op.create_table(
        "continuity_assessments",
        *_full_mixin_cols(),
        sa.Column(
            "project_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id"), nullable=False,
        ),
        sa.Column(
            "discovery_run_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("discovery_runs_m22.id"), nullable=False,
        ),
        sa.Column(
            "backups_inventario", postgresql.JSONB(),
            nullable=False, server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("tiene_backup_offsite", sa.Boolean(), nullable=True),
        sa.Column("tiene_backup_cifrado", sa.Boolean(), nullable=True),
        sa.Column(
            "ultima_prueba_restauracion", sa.TIMESTAMP(timezone=True), nullable=True,
        ),
        sa.Column("prueba_restauracion_exitosa", sa.Boolean(), nullable=True),
        sa.Column("tiene_drp", sa.Boolean(), nullable=True),
        sa.Column("drp_documentado", sa.Boolean(), nullable=True),
        sa.Column("drp_probado", sa.Boolean(), nullable=True),
        sa.Column("drp_ultima_prueba", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "slas_proveedores", postgresql.JSONB(),
            nullable=False, server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "spofs_detectados", postgresql.JSONB(),
            nullable=False, server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("rto_global_horas", sa.Integer(), nullable=True),
        sa.Column("rpo_global_horas", sa.Integer(), nullable=True),
        sa.Column(
            "nivel_madurez_continuidad", sa.String(10),
            nullable=False, server_default="L0",
        ),
        sa.Column("observaciones", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_continuity_assessments_project_id",
        "continuity_assessments", ["project_id"],
    )
    op.create_index(
        "ix_continuity_assessments_discovery_run_id",
        "continuity_assessments", ["discovery_run_id"],
    )

    # ========== RLS ==========
    for table in (
        "logging_assessments", "data_flow_diagrams", "continuity_assessments",
    ):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY project_isolation ON {table} "
            f"USING (project_id = current_project_id())"
        )


def downgrade() -> None:
    for table in (
        "logging_assessments", "data_flow_diagrams", "continuity_assessments",
    ):
        op.execute(f"DROP POLICY IF EXISTS project_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    op.drop_index(
        "ix_continuity_assessments_discovery_run_id",
        table_name="continuity_assessments",
    )
    op.drop_index(
        "ix_continuity_assessments_project_id",
        table_name="continuity_assessments",
    )
    op.drop_table("continuity_assessments")

    op.drop_index(
        "ix_data_flow_diagrams_project_tipo", table_name="data_flow_diagrams",
    )
    op.drop_index(
        "ix_data_flow_diagrams_discovery_run_id", table_name="data_flow_diagrams",
    )
    op.drop_index(
        "ix_data_flow_diagrams_project_id", table_name="data_flow_diagrams",
    )
    op.drop_table("data_flow_diagrams")

    op.drop_index(
        "ix_logging_assessments_discovery_run_id",
        table_name="logging_assessments",
    )
    op.drop_index(
        "ix_logging_assessments_project_id",
        table_name="logging_assessments",
    )
    op.drop_table("logging_assessments")
