"""sand_billing_milestones_001

SAN-D MB-18.1 · tabla contract_milestones para auto-billing milestone-
completion (ADR-040).

Enriquece MilestoneSpec NamedTuple existing (rules.py:75) + get_milestones
calculator (calculator.py:282) con tracking persistente DB:
- workflow_phase_index → mapping a fase canonical (ADR-026 + SAN-C MB-11.1)
- billing_trigger (phase_complete | phase_start | manual | scheduled_date)
- status lifecycle: pending → billed → invoice_issued → payment_pending →
  paid | disputed | refunded
- paid_marked_by_user_id + payment_reference + payment_notes para audit
  reconciliación manual Marcos
- blocking_next_phase para auto-advance projects.fase post-payment

UNIQUE (contract_id, milestone_index) garantiza idempotencia
MilestoneFactory.

RLS por project_id · admin (Marcos owner) escala via SET LOCAL ROLE
fulkro pattern existing.

Revision ID: sand_billing_milestones_001
Revises: sand_notif_prefs_001
Create Date: 2026-05-06
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "sand_billing_milestones_001"
down_revision = "sand_notif_prefs_001"
branch_labels = None
depends_on = None


_VALID_STATUSES = (
    "pending",
    "billed",
    "invoice_issued",
    "payment_pending",
    "paid",
    "disputed",
    "refunded",
)

_VALID_TRIGGERS = (
    "phase_complete",
    "phase_start",
    "manual",
    "scheduled_date",
)


def upgrade() -> None:
    op.create_table(
        "contract_milestones",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "contract_id",
            UUID(as_uuid=True),
            sa.ForeignKey("contracts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("milestone_index", sa.Integer, nullable=False),
        sa.Column("milestone_name", sa.String(100), nullable=False),
        sa.Column("workflow_phase_index", sa.Integer, nullable=False),
        sa.Column(
            "billing_trigger",
            sa.String(50),
            nullable=False,
            server_default="phase_complete",
        ),
        sa.Column("amount_eur", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "vat_percent",
            sa.Numeric(4, 2),
            nullable=False,
            server_default="21.00",
        ),
        sa.Column("percent_of_total", sa.Numeric(5, 2), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "billed_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "invoice_id",
            UUID(as_uuid=True),
            sa.ForeignKey("invoices.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "paid_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "paid_marked_by_user_id",
            UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("payment_reference", sa.String(200), nullable=True),
        sa.Column("payment_notes", sa.Text, nullable=True),
        sa.Column(
            "auto_billing_enabled",
            sa.Boolean,
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "blocking_next_phase",
            sa.Boolean,
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "metadata_jsonb",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
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
            f"status IN {_VALID_STATUSES}",
            name="ck_contract_milestones_status",
        ),
        sa.CheckConstraint(
            f"billing_trigger IN {_VALID_TRIGGERS}",
            name="ck_contract_milestones_trigger",
        ),
        sa.CheckConstraint(
            "amount_eur >= 0",
            name="ck_contract_milestones_amount_nonneg",
        ),
        sa.CheckConstraint(
            "percent_of_total >= 0 AND percent_of_total <= 100",
            name="ck_contract_milestones_percent_range",
        ),
        sa.UniqueConstraint(
            "contract_id",
            "milestone_index",
            name="uq_contract_milestones_idx",
        ),
    )
    op.create_index(
        "ix_contract_milestones_project",
        "contract_milestones",
        ["project_id"],
    )
    op.create_index(
        "ix_contract_milestones_contract",
        "contract_milestones",
        ["contract_id"],
    )
    op.create_index(
        "ix_contract_milestones_phase",
        "contract_milestones",
        ["workflow_phase_index"],
    )
    op.create_index(
        "ix_contract_milestones_status",
        "contract_milestones",
        ["status"],
    )
    op.create_index(
        "ix_contract_milestones_paid_at",
        "contract_milestones",
        ["paid_at"],
    )

    op.execute(
        "ALTER TABLE contract_milestones ENABLE ROW LEVEL SECURITY"
    )
    op.execute(
        """
        CREATE POLICY contract_milestones_isolation ON contract_milestones
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
        "GRANT SELECT, INSERT, UPDATE ON contract_milestones TO fulkro_app"
    )


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS contract_milestones_isolation "
        "ON contract_milestones"
    )
    for ix in (
        "ix_contract_milestones_paid_at",
        "ix_contract_milestones_status",
        "ix_contract_milestones_phase",
        "ix_contract_milestones_contract",
        "ix_contract_milestones_project",
    ):
        op.drop_index(ix, table_name="contract_milestones")
    op.drop_table("contract_milestones")
