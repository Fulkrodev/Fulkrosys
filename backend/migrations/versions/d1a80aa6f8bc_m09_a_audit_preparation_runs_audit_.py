"""m09-a: audit_preparation_runs + audit_checklist_items

Revision ID: d1a80aa6f8bc
Revises: 114ecd11e824
Create Date: 2026-04-17 19:45:52.812528
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d1a80aa6f8bc"
down_revision: Union[str, None] = "114ecd11e824"
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
    # ============ audit_preparation_runs ============
    op.create_table(
        "audit_preparation_runs",
        *_full_mixin_cols(),
        sa.Column(
            "project_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id"), nullable=False,
        ),
        sa.Column("categoria", sa.String(10), nullable=False),
        sa.Column(
            "estado", sa.String(20), nullable=False, server_default="pending",
        ),
        sa.Column(
            "checklist_results", postgresql.JSONB(),
            nullable=False, server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("readiness_score", sa.Integer(), nullable=True),
        sa.Column(
            "contradicciones_count", sa.Integer(),
            nullable=False, server_default="0",
        ),
        sa.Column(
            "alertas_count", sa.Integer(),
            nullable=False, server_default="0",
        ),
        sa.Column("dossier_zip_path", sa.String(500), nullable=True),
        sa.Column(
            "dossier_generated_at", sa.TIMESTAMP(timezone=True), nullable=True,
        ),
        sa.Column("matriz_99_path", sa.String(500), nullable=True),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_audit_preparation_runs_project_id",
        "audit_preparation_runs", ["project_id"],
    )
    op.create_index(
        "ix_audit_preparation_runs_project_estado",
        "audit_preparation_runs", ["project_id", "estado"],
    )

    # ============ audit_checklist_items ============
    op.create_table(
        "audit_checklist_items",
        *_full_mixin_cols(),
        sa.Column(
            "run_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("audit_preparation_runs.id"), nullable=False,
        ),
        sa.Column(
            "project_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id"), nullable=False,
        ),
        sa.Column("categoria_check", sa.String(30), nullable=False),
        sa.Column("referencia", sa.String(100), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False),
        sa.Column(
            "severidad", sa.String(20), nullable=False, server_default="info",
        ),
        sa.Column("detalle", sa.Text(), nullable=True),
        sa.Column("accion_sugerida", sa.Text(), nullable=True),
        sa.Column(
            "resuelto", sa.Boolean(),
            nullable=False, server_default=sa.text("false"),
        ),
        sa.Column("resuelto_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("resuelto_por", sa.String(100), nullable=True),
    )
    op.create_index(
        "ix_audit_checklist_items_run_id",
        "audit_checklist_items", ["run_id"],
    )
    op.create_index(
        "ix_audit_checklist_items_project_id",
        "audit_checklist_items", ["project_id"],
    )
    op.create_index(
        "ix_audit_checklist_items_run_estado",
        "audit_checklist_items", ["run_id", "estado"],
    )
    op.create_index(
        "ix_audit_checklist_items_project_severidad",
        "audit_checklist_items", ["project_id", "severidad"],
    )

    # ============ RLS ============
    for table in ("audit_preparation_runs", "audit_checklist_items"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY project_isolation ON {table} "
            f"USING (project_id = current_project_id())"
        )


def downgrade() -> None:
    for table in ("audit_preparation_runs", "audit_checklist_items"):
        op.execute(f"DROP POLICY IF EXISTS project_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    op.drop_index(
        "ix_audit_checklist_items_project_severidad",
        table_name="audit_checklist_items",
    )
    op.drop_index(
        "ix_audit_checklist_items_run_estado",
        table_name="audit_checklist_items",
    )
    op.drop_index(
        "ix_audit_checklist_items_project_id",
        table_name="audit_checklist_items",
    )
    op.drop_index(
        "ix_audit_checklist_items_run_id",
        table_name="audit_checklist_items",
    )
    op.drop_table("audit_checklist_items")

    op.drop_index(
        "ix_audit_preparation_runs_project_estado",
        table_name="audit_preparation_runs",
    )
    op.drop_index(
        "ix_audit_preparation_runs_project_id",
        table_name="audit_preparation_runs",
    )
    op.drop_table("audit_preparation_runs")
