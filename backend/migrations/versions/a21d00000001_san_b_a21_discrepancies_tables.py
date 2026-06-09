"""san_b_a21_discrepancies_tables

Revision ID: a21d00000001
Revises: 7ebd575c4f66
Create Date: 2026-05-05 09:00:00.000000

Crea 2 tablas A21 (Detector Discrepancias) con RLS:
- a21_scan_runs: ejecuciones del detector cross-motor por proyecto
- a21_discrepancies: discrepancias encontradas (NC) con resolución status

RLS pattern simple (project_isolation) replica e41cd7163c02 pattern.

Cierra parcial: TODO-A21-IMPLEMENTATION-001 (capa BD).

Refs: SAN-B.MB-8.A.1
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "a21d00000001"
down_revision: Union[str, None] = "7ebd575c4f66"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. a21_scan_runs ────────────────────────────────────────────
    op.create_table(
        "a21_scan_runs",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"), primary_key=True,
        ),
        sa.Column(
            "project_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column(
            "run_status", sa.String(20), nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column(
            "motors_scanned", postgresql.ARRAY(sa.Text()),
            nullable=False, server_default=sa.text("ARRAY[]::TEXT[]"),
        ),
        sa.Column(
            "discrepancies_found", sa.Integer(),
            nullable=False, server_default=sa.text("0"),
        ),
        sa.Column(
            "started_at", sa.TIMESTAMP(timezone=True),
            nullable=False, server_default=sa.text("now()"),
        ),
        sa.Column(
            "completed_at", sa.TIMESTAMP(timezone=True), nullable=True,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "metadata_jsonb", postgresql.JSONB(),
            nullable=False, server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint(
            "run_status IN ('pending', 'running', 'completed', 'failed')",
            name="ck_a21_scan_runs_status",
        ),
    )
    op.create_index(
        "idx_a21_scan_runs_project_status",
        "a21_scan_runs", ["project_id", "run_status"],
    )

    # ── 2. a21_discrepancies ────────────────────────────────────────
    op.create_table(
        "a21_discrepancies",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"), primary_key=True,
        ),
        sa.Column(
            "scan_run_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("a21_scan_runs.id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column(
            "project_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column("discrepancy_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(10), nullable=False),
        sa.Column("motor_a", sa.String(20), nullable=False),
        sa.Column("motor_b", sa.String(20), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "evidence_a", postgresql.JSONB(),
            nullable=False, server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "evidence_b", postgresql.JSONB(),
            nullable=False, server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "resolution_status", sa.String(20), nullable=False,
            server_default=sa.text("'open'"),
        ),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column(
            "resolved_by", postgresql.UUID(as_uuid=True), nullable=True,
        ),
        sa.Column(
            "resolved_at", sa.TIMESTAMP(timezone=True), nullable=True,
        ),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint(
            "severity IN ('critical', 'high', 'medium', 'low')",
            name="ck_a21_discrepancies_severity",
        ),
        sa.CheckConstraint(
            "resolution_status IN ('open', 'acknowledged', 'resolved', 'dismissed')",
            name="ck_a21_discrepancies_resolution",
        ),
    )
    op.create_index(
        "idx_a21_discrepancies_project_status",
        "a21_discrepancies", ["project_id", "resolution_status"],
    )
    op.create_index(
        "idx_a21_discrepancies_severity",
        "a21_discrepancies", ["severity"],
    )

    # ── 3. RLS · pattern project_isolation ──────────────────────────
    op.execute("ALTER TABLE a21_scan_runs ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE a21_scan_runs FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY project_isolation ON a21_scan_runs "
        "USING (project_id = current_project_id())"
    )

    op.execute("ALTER TABLE a21_discrepancies ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE a21_discrepancies FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY project_isolation ON a21_discrepancies "
        "USING (project_id = current_project_id())"
    )

    # ── 4. GRANTs · fulkro_app role debe tener acceso a las tablas ──
    # (replicar pattern existente · cuando migración corre como
    # fulkro_migrate, fulkro_app no hereda privilegios automáticamente)
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE "
        "a21_scan_runs, a21_discrepancies TO fulkro_app"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS project_isolation ON a21_discrepancies")
    op.execute("DROP POLICY IF EXISTS project_isolation ON a21_scan_runs")
    op.drop_index(
        "idx_a21_discrepancies_severity",
        table_name="a21_discrepancies",
    )
    op.drop_index(
        "idx_a21_discrepancies_project_status",
        table_name="a21_discrepancies",
    )
    op.drop_table("a21_discrepancies")
    op.drop_index(
        "idx_a21_scan_runs_project_status",
        table_name="a21_scan_runs",
    )
    op.drop_table("a21_scan_runs")
