"""FASE 8.5 C1 backend — pipeline radar v2 + RadarLead FK pipeline_run_id.

Crea ``radar_pipeline_runs`` (status workflow + cancelacion cooperativa +
tracking incremental + LLM cost + error tracking) y extiende ``radar_leads``
con FK ``pipeline_run_id`` (ON DELETE SET NULL).

Decision Marcos Opcion C audit-first: NO se duplica detection_confidence
ni ens_level_inferred (se reusa ENSAnalysis.confidence + nivel existing).

Revision ID: cb9c8416b68a
Revises: 2ddffdcdddfc
Create Date: 2026-04-30 14:54:46.767324
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "cb9c8416b68a"
down_revision: Union[str, None] = "2ddffdcdddfc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "radar_pipeline_runs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "cancel_requested_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "cancelled_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("step_current", sa.String(length=50), nullable=True),
        sa.Column(
            "steps_completed",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "leads_processed",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "leads_filtered",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "leads_temperature_count",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "llm_calls",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "llm_cost_usd",
            sa.Numeric(precision=10, scale=4),
            nullable=False,
            server_default="0.0000",
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("error_step", sa.String(length=50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'completed', "
            "'cancelled', 'failed')",
            name="radar_pipeline_runs_status_check",
        ),
    )
    op.create_index(
        "ix_radar_pipeline_runs_status",
        "radar_pipeline_runs",
        ["status"],
    )

    op.add_column(
        "radar_leads",
        sa.Column(
            "pipeline_run_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_radar_leads_pipeline_run_id",
        "radar_leads",
        "radar_pipeline_runs",
        ["pipeline_run_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_radar_leads_pipeline_run_id",
        "radar_leads",
        ["pipeline_run_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_radar_leads_pipeline_run_id", "radar_leads")
    op.drop_constraint(
        "fk_radar_leads_pipeline_run_id",
        "radar_leads",
        type_="foreignkey",
    )
    op.drop_column("radar_leads", "pipeline_run_id")

    op.drop_index("ix_radar_pipeline_runs_status", "radar_pipeline_runs")
    op.drop_table("radar_pipeline_runs")
