"""m08-a addendum: purple_team_results table

Revision ID: 114ecd11e824
Revises: 543780f42083
Create Date: 2026-04-17 12:23:08.875393
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "114ecd11e824"
down_revision: Union[str, None] = "543780f42083"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "purple_team_results",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"), primary_key=True,
        ),
        sa.Column(
            "project_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id"), nullable=False,
        ),
        sa.Column(
            "pentest_run_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("pentest_runs.id"), nullable=False,
        ),
        sa.Column("iteration", sa.Integer(), nullable=False),
        sa.Column("mitre_technique", sa.String(20), nullable=False),
        sa.Column("mitre_tactic", sa.String(50), nullable=False),
        sa.Column("action_description", sa.Text(), nullable=False),
        sa.Column("executed_successfully", sa.Boolean(), nullable=False),
        sa.Column("detected_by_defender", sa.Boolean(), nullable=True),
        sa.Column("detection_source", sa.String(200), nullable=True),
        sa.Column("detection_time_seconds", sa.Integer(), nullable=True),
        sa.Column("gap_description", sa.Text(), nullable=True),
        sa.Column("remediation_suggestion", sa.Text(), nullable=True),
        sa.Column(
            "medidas_ens_deteccion", postgresql.JSONB(),
            nullable=False, server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
    )
    op.create_index(
        "ix_purple_team_results_project_id",
        "purple_team_results", ["project_id"],
    )
    op.create_index(
        "ix_purple_team_results_pentest_run_id",
        "purple_team_results", ["pentest_run_id"],
    )
    op.create_index(
        "ix_purple_team_results_run_iteration",
        "purple_team_results", ["pentest_run_id", "iteration"],
    )

    op.execute("ALTER TABLE purple_team_results ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE purple_team_results FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY project_isolation ON purple_team_results "
        "USING (project_id = current_project_id())"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS project_isolation ON purple_team_results")
    op.execute("ALTER TABLE purple_team_results DISABLE ROW LEVEL SECURITY")
    op.drop_index(
        "ix_purple_team_results_run_iteration",
        table_name="purple_team_results",
    )
    op.drop_index(
        "ix_purple_team_results_pentest_run_id",
        table_name="purple_team_results",
    )
    op.drop_index(
        "ix_purple_team_results_project_id",
        table_name="purple_team_results",
    )
    op.drop_table("purple_team_results")
