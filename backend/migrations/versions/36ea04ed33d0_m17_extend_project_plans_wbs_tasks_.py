"""m17: extend project_plans/wbs_tasks + create change_requests

Revision ID: 36ea04ed33d0
Revises: d1a80aa6f8bc
Create Date: 2026-04-17 21:23:43.051896
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "36ea04ed33d0"
down_revision: Union[str, None] = "d1a80aa6f8bc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ============ Extender project_plans ============
    op.add_column("project_plans", sa.Column("categoria", sa.String(10), nullable=True))
    op.add_column("project_plans", sa.Column("start_date", sa.Date(), nullable=True))
    op.add_column("project_plans", sa.Column("end_date_estimated", sa.Date(), nullable=True))
    op.add_column("project_plans", sa.Column("end_date_actual", sa.Date(), nullable=True))
    op.add_column(
        "project_plans",
        sa.Column("total_effort_marcos_hours", sa.Float(), nullable=True),
    )
    op.add_column(
        "project_plans",
        sa.Column("total_effort_platform_hours", sa.Float(), nullable=True),
    )
    op.add_column(
        "project_plans",
        sa.Column("total_duration_weeks", sa.Integer(), nullable=True),
    )
    op.add_column(
        "project_plans",
        sa.Column("critical_path_length_weeks", sa.Integer(), nullable=True),
    )
    op.add_column(
        "project_plans",
        sa.Column("critical_path_tasks", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "project_plans",
        sa.Column("marcos_weekly_capacity_hours", sa.Float(), nullable=True),
    )
    op.add_column(
        "project_plans",
        sa.Column("client_weekly_capacity_hours", sa.Float(), nullable=True),
    )
    op.add_column("project_plans", sa.Column("estado", sa.String(20), nullable=True))
    op.add_column(
        "project_plans",
        sa.Column("baseline_snapshot", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "project_plans",
        sa.Column("baseline_date", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column("project_plans", sa.Column("mermaid_gantt", sa.Text(), nullable=True))
    op.add_column(
        "project_plans",
        sa.Column("meeting_plan", postgresql.JSONB(), nullable=True),
    )
    op.create_index(
        "ix_project_plans_project_estado",
        "project_plans", ["project_id", "estado"],
    )

    # ============ Extender wbs_tasks ============
    op.add_column(
        "wbs_tasks",
        sa.Column(
            "project_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id"), nullable=True,
        ),
    )
    op.create_index(
        "ix_wbs_tasks_project_id", "wbs_tasks", ["project_id"],
    )
    op.add_column(
        "wbs_tasks",
        sa.Column("effort_platform_hours", sa.Float(), nullable=True),
    )
    op.add_column(
        "wbs_tasks",
        sa.Column(
            "is_critical_path", sa.Boolean(),
            nullable=False, server_default=sa.text("false"),
        ),
    )
    op.add_column("wbs_tasks", sa.Column("slack_days", sa.Integer(), nullable=True))
    op.add_column(
        "wbs_tasks",
        sa.Column(
            "progress_pct", sa.Integer(),
            nullable=False, server_default="0",
        ),
    )
    op.add_column(
        "wbs_tasks",
        sa.Column("baseline_start_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "wbs_tasks", sa.Column("baseline_end_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "wbs_tasks", sa.Column("milestone_code", sa.String(20), nullable=True),
    )
    op.add_column(
        "wbs_tasks", sa.Column("blocker_description", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_wbs_tasks_status", "wbs_tasks", ["status"],
    )

    # ============ change_requests ============
    op.create_table(
        "change_requests",
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
        sa.Column(
            "project_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id"), nullable=False,
        ),
        sa.Column(
            "plan_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("project_plans.id"), nullable=False,
        ),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("titulo", sa.String(300), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("impacto_plazo_dias", sa.Integer(), nullable=True),
        sa.Column("impacto_esfuerzo_horas", sa.Float(), nullable=True),
        sa.Column("impacto_presupuesto_eur", sa.Float(), nullable=True),
        sa.Column(
            "estado", sa.String(20),
            nullable=False, server_default="propuesto",
        ),
        sa.Column("solicitado_por", sa.String(200), nullable=False),
        sa.Column("aprobado_por", sa.String(200), nullable=True),
        sa.Column("aprobado_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_change_requests_project_id", "change_requests", ["project_id"],
    )
    op.create_index(
        "ix_change_requests_plan_id", "change_requests", ["plan_id"],
    )
    op.create_index(
        "ix_change_requests_project_estado",
        "change_requests", ["project_id", "estado"],
    )

    # ============ RLS ============
    # wbs_tasks no tenia project_id, ahora si -> habilitar RLS directa.
    op.execute("ALTER TABLE wbs_tasks ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE wbs_tasks FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY project_isolation ON wbs_tasks "
        "USING (project_id = current_project_id() OR project_id IS NULL)"
    )

    op.execute("ALTER TABLE change_requests ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE change_requests FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY project_isolation ON change_requests "
        "USING (project_id = current_project_id())"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS project_isolation ON change_requests")
    op.execute("ALTER TABLE change_requests DISABLE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS project_isolation ON wbs_tasks")
    op.execute("ALTER TABLE wbs_tasks DISABLE ROW LEVEL SECURITY")

    op.drop_index(
        "ix_change_requests_project_estado", table_name="change_requests",
    )
    op.drop_index("ix_change_requests_plan_id", table_name="change_requests")
    op.drop_index("ix_change_requests_project_id", table_name="change_requests")
    op.drop_table("change_requests")

    op.drop_index("ix_wbs_tasks_status", table_name="wbs_tasks")
    for col in (
        "blocker_description", "milestone_code",
        "baseline_end_date", "baseline_start_date",
        "progress_pct", "slack_days", "is_critical_path",
        "effort_platform_hours",
    ):
        op.drop_column("wbs_tasks", col)
    op.drop_index("ix_wbs_tasks_project_id", table_name="wbs_tasks")
    op.drop_column("wbs_tasks", "project_id")

    op.drop_index(
        "ix_project_plans_project_estado", table_name="project_plans",
    )
    for col in (
        "meeting_plan", "mermaid_gantt", "baseline_date",
        "baseline_snapshot", "estado",
        "client_weekly_capacity_hours", "marcos_weekly_capacity_hours",
        "critical_path_tasks", "critical_path_length_weeks",
        "total_duration_weeks", "total_effort_platform_hours",
        "total_effort_marcos_hours",
        "end_date_actual", "end_date_estimated", "start_date", "categoria",
    ):
        op.drop_column("project_plans", col)
