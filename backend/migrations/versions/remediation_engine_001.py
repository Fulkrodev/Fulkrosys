"""remediation_engine_001 · ADR-055 motor de auto-remediación (Fase 1 cloud)

Crea ``remediation_jobs`` + ``remediation_snapshots`` (RLS directa por
project_id · fail-closed) y extiende ``cloud_connectors`` con las 3 columnas
opt-in del carve-out controlado de ADR-014 (default OFF · read-only de fábrica).

ADDITIVE · DB-safe (tablas nuevas 0 filas · columnas con DEFAULT no-NULL).

Revision ID: remediation_engine_001
Revises: ola_d_trusted_timestamps_004
Create Date: 2026-06-13
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID

revision: str = "remediation_engine_001"
down_revision: Union[str, None] = "ola_d_trusted_timestamps_004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _enable_project_rls(table: str) -> None:
    op.execute(
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} "
        "TO fulkro_app, fulkro_app_bypassrls"
    )
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY project_isolation ON {table} "
        "USING (project_id = current_project_id())"
    )


def _disable_project_rls(table: str) -> None:
    op.execute(f"DROP POLICY IF EXISTS project_isolation ON {table}")
    op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")


def upgrade() -> None:
    # ── remediation_jobs ────────────────────────────────────────────────
    op.create_table(
        "remediation_jobs",
        sa.Column(
            "id", UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"), primary_key=True,
        ),
        sa.Column(
            "created_at", TIMESTAMP(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.Column(
            "updated_at", TIMESTAMP(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.Column("deleted_at", TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "project_id", UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("client_id", UUID(as_uuid=True), nullable=True),
        sa.Column("source_kind", sa.String(length=20), nullable=False),
        sa.Column(
            "source_gap_id", UUID(as_uuid=True),
            sa.ForeignKey("cloud_gaps.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Column("source_finding_id", UUID(as_uuid=True), nullable=True),
        sa.Column(
            "connector_id", UUID(as_uuid=True),
            sa.ForeignKey("cloud_connectors.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Column("agent_id", UUID(as_uuid=True), nullable=True),
        sa.Column("action_type", sa.String(length=80), nullable=False),
        sa.Column("tier", sa.String(length=20), nullable=False),
        sa.Column(
            "status", sa.String(length=30), nullable=False,
            server_default=sa.text("'queued'"),
        ),
        sa.Column("target_ref", sa.String(length=255), nullable=True),
        sa.Column("params", JSONB, nullable=True),
        sa.Column(
            "dry_run", sa.Boolean(), nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("authorized_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("authorized_at", TIMESTAMP(timezone=True), nullable=True),
        sa.Column("result", JSONB, nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", TIMESTAMP(timezone=True), nullable=True),
        sa.Column("finished_at", TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint(
            "tier IN ('safe_auto', 'guarded', 'blocked')",
            name="ck_remediation_jobs_tier",
        ),
        sa.CheckConstraint(
            "source_kind IN ('cloud_gap', 'host_finding')",
            name="ck_remediation_jobs_source_kind",
        ),
    )
    op.create_index(
        "ix_remediation_jobs_project_status",
        "remediation_jobs", ["project_id", "status"],
    )
    op.create_index(
        "ix_remediation_jobs_gap", "remediation_jobs", ["source_gap_id"],
    )
    op.create_index(
        "ix_remediation_jobs_action", "remediation_jobs", ["action_type"],
    )
    _enable_project_rls("remediation_jobs")

    # ── remediation_snapshots ───────────────────────────────────────────
    op.create_table(
        "remediation_snapshots",
        sa.Column(
            "id", UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"), primary_key=True,
        ),
        sa.Column(
            "created_at", TIMESTAMP(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.Column(
            "updated_at", TIMESTAMP(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.Column("deleted_at", TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "project_id", UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "job_id", UUID(as_uuid=True),
            sa.ForeignKey("remediation_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("action_type", sa.String(length=80), nullable=False),
        sa.Column("target_ref", sa.String(length=255), nullable=True),
        sa.Column("state_before", JSONB, nullable=False),
        sa.Column("created_by_user_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "ix_remediation_snapshots_job", "remediation_snapshots", ["job_id"],
    )
    op.create_index(
        "ix_remediation_snapshots_project",
        "remediation_snapshots", ["project_id"],
    )
    _enable_project_rls("remediation_snapshots")

    # ── cloud_connectors · extend opt-in (ADR-055) ──────────────────────
    op.add_column(
        "cloud_connectors",
        sa.Column(
            "remediation_enabled", sa.Boolean(), nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "cloud_connectors",
        sa.Column(
            "auto_remediation_policy", sa.String(length=20), nullable=False,
            server_default=sa.text("'off'"),
        ),
    )
    op.add_column(
        "cloud_connectors",
        sa.Column("granted_write_scopes", JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("cloud_connectors", "granted_write_scopes")
    op.drop_column("cloud_connectors", "auto_remediation_policy")
    op.drop_column("cloud_connectors", "remediation_enabled")

    _disable_project_rls("remediation_snapshots")
    op.drop_index(
        "ix_remediation_snapshots_project", table_name="remediation_snapshots",
    )
    op.drop_index(
        "ix_remediation_snapshots_job", table_name="remediation_snapshots",
    )
    op.drop_table("remediation_snapshots")

    _disable_project_rls("remediation_jobs")
    op.drop_index("ix_remediation_jobs_action", table_name="remediation_jobs")
    op.drop_index("ix_remediation_jobs_gap", table_name="remediation_jobs")
    op.drop_index(
        "ix_remediation_jobs_project_status", table_name="remediation_jobs",
    )
    op.drop_table("remediation_jobs")
