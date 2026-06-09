"""sand_retainer_health_001

SAN-D MB-18.1 · tabla retainer_health_signals para ChurnPredictor
heurístico explicable (ADR-040).

Snapshot per scan (Celery beat weekly Monday 09:30 Europe/Madrid):
- 7 signals: días sin login portal · días sin chat msg cliente ·
  tasks overdue · invoices overdue · avg response time · NPS último ·
  días a próximo renewal.
- Computed: churn_risk_score (0-100) + risk_level (low/medium/high/
  critical) + primary_risk_factors JSONB + recommended_action.

Cero ML black-box · heurístico explicable trazable ENAC compliance.

RLS por project_id · admin (Marcos owner) escala via SET LOCAL ROLE
fulkro pattern existing.

Revision ID: sand_retainer_health_001
Revises: sand_billing_milestones_001
Create Date: 2026-05-06
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "sand_retainer_health_001"
down_revision = "sand_billing_milestones_001"
branch_labels = None
depends_on = None


_VALID_RISK_LEVELS = ("low", "medium", "high", "critical")


def upgrade() -> None:
    op.create_table(
        "retainer_health_signals",
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
            "retainer_id",
            UUID(as_uuid=True),
            sa.ForeignKey("retainer_contracts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "computed_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "days_since_portal_login",
            sa.Integer,
            nullable=True,
        ),
        sa.Column(
            "days_since_chat_msg_client",
            sa.Integer,
            nullable=True,
        ),
        sa.Column(
            "tasks_overdue_count",
            sa.Integer,
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "invoices_overdue_count",
            sa.Integer,
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "avg_response_time_hours",
            sa.Numeric(8, 2),
            nullable=True,
        ),
        sa.Column(
            "nps_last_score",
            sa.Integer,
            nullable=True,
        ),
        sa.Column(
            "renewal_in_days",
            sa.Integer,
            nullable=True,
        ),
        sa.Column(
            "churn_risk_score",
            sa.Numeric(5, 2),
            nullable=False,
        ),
        sa.Column(
            "risk_level",
            sa.String(20),
            nullable=False,
        ),
        sa.Column(
            "primary_risk_factors",
            JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "recommended_action",
            sa.String(500),
            nullable=True,
        ),
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
            "deleted_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.CheckConstraint(
            f"risk_level IN {_VALID_RISK_LEVELS}",
            name="ck_retainer_health_risk_level",
        ),
        sa.CheckConstraint(
            "churn_risk_score >= 0 AND churn_risk_score <= 100",
            name="ck_retainer_health_score_range",
        ),
        sa.CheckConstraint(
            "tasks_overdue_count >= 0",
            name="ck_retainer_health_tasks_nonneg",
        ),
        sa.CheckConstraint(
            "invoices_overdue_count >= 0",
            name="ck_retainer_health_invoices_nonneg",
        ),
    )
    op.create_index(
        "ix_retainer_health_project_recent",
        "retainer_health_signals",
        ["project_id", sa.text("computed_at DESC")],
    )
    op.create_index(
        "ix_retainer_health_retainer_recent",
        "retainer_health_signals",
        ["retainer_id", sa.text("computed_at DESC")],
    )
    op.create_index(
        "ix_retainer_health_risk_level",
        "retainer_health_signals",
        ["risk_level", sa.text("computed_at DESC")],
    )

    op.execute(
        "ALTER TABLE retainer_health_signals ENABLE ROW LEVEL SECURITY"
    )
    op.execute(
        """
        CREATE POLICY retainer_health_signals_isolation
            ON retainer_health_signals
            FOR ALL TO fulkro_app
            USING (
                project_id::text = current_setting('app.current_project_id', true)
            )
            WITH CHECK (
                project_id::text = current_setting('app.current_project_id', true)
            )
        """,
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE ON retainer_health_signals "
        "TO fulkro_app"
    )


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS retainer_health_signals_isolation "
        "ON retainer_health_signals"
    )
    for ix in (
        "ix_retainer_health_risk_level",
        "ix_retainer_health_retainer_recent",
        "ix_retainer_health_project_recent",
    ):
        op.drop_index(ix, table_name="retainer_health_signals")
    op.drop_table("retainer_health_signals")
