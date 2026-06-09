"""sand_audit_dry_run_001

SAN-D MB-15.1 · Tabla audit_dry_run_results para histórico orchestrator
M10+A11 dry-run pre-auditoría externa (ADR-037).

Cada row almacena resultado completo dry-run: M10 score determinista
+ A11 senior layer (PAC + sectoriales + narrativa) + métricas
agregadas para tracking histórico comparativo.

RLS via app.current_project_id (pattern MB-13.4 · MB-17.5).

Revision ID: sand_audit_dry_run_001
Revises: sand_alert_queue_001
Create Date: 2026-05-06
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "sand_audit_dry_run_001"
down_revision = "sand_alert_queue_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_dry_run_results",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "project_id",
            UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "executed_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("executed_by", UUID(as_uuid=True), nullable=True),
        sa.Column(
            "m10_run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("audit_simulation_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("category_at_execution", sa.String(20), nullable=False),
        sa.Column("archetype_at_execution", sa.String(50), nullable=True),
        sa.Column("total_questions", sa.Integer, nullable=False),
        sa.Column("questions_with_evidence", sa.Integer, nullable=False),
        sa.Column("overall_readiness_score", sa.Integer, nullable=False),
        sa.Column("gaps_detected", sa.Integer, nullable=False),
        sa.Column("critical_gaps", sa.Integer, nullable=False),
        sa.Column("execution_time_ms", sa.Integer, nullable=True),
        sa.Column("m10_payload", JSONB, nullable=True),
        sa.Column("a11_payload", JSONB, nullable=True),
        sa.Column("model_used", sa.String(50), server_default="claude-opus-4-7"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "deleted_at", sa.TIMESTAMP(timezone=True), nullable=True,
        ),
    )

    op.create_index(
        "ix_dry_run_project_executed",
        "audit_dry_run_results",
        ["project_id", sa.text("executed_at DESC")],
    )

    op.execute(
        "ALTER TABLE audit_dry_run_results ENABLE ROW LEVEL SECURITY",
    )
    op.execute(
        """
        CREATE POLICY audit_dry_run_isolation ON audit_dry_run_results
            FOR ALL TO fulkro_app
            USING (project_id::text = current_setting('app.current_project_id', true))
            WITH CHECK (project_id::text = current_setting('app.current_project_id', true))
        """,
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE ON audit_dry_run_results TO fulkro_app",
    )


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS audit_dry_run_isolation ON audit_dry_run_results",
    )
    op.drop_index(
        "ix_dry_run_project_executed", table_name="audit_dry_run_results",
    )
    op.drop_table("audit_dry_run_results")
