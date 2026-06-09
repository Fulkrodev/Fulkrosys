"""SAN-E MB-7.bis atom 7.bis.5 · marcos_timesheet_entries table.

Tracking horas Marcos dedicadas per cliente · retainer · activity.
Auto-tracked via FastAPI middleware (endpoints /api/v1/projects/{id}/*
+ /api/v1/admin/retainers/{id}/*) o manual entry via UI.

Source ∈ auto_endpoint / manual / import.
manual_override BOOLEAN si Marcos editó timestamp/duration tras auto-track.

Used by CapacityTile (RetainerOpsCenter) para top 3 clientes por horas.

Revision ID: sane_mb7bis_timesheet_001
Revises: 08bf3e16ef34
Create Date: 2026-05-12
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "sane_mb7bis_timesheet_001"
down_revision = "08bf3e16ef34"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "marcos_timesheet_entries",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "client_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clients.id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column(
            "retainer_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("retainer_contracts.id", ondelete="SET NULL"),
            nullable=True, index=True,
        ),
        sa.Column(
            "activity_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("retainer_activities.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "started_at", sa.TIMESTAMP(timezone=True), nullable=False, index=True,
        ),
        sa.Column(
            "ended_at", sa.TIMESTAMP(timezone=True), nullable=True,
        ),
        sa.Column(
            "duration_minutes", sa.Integer(), nullable=True,
            comment=(
                "Computed at end_session · NULL while ongoing"
            ),
        ),
        sa.Column(
            "source", sa.String(20), nullable=False,
            server_default=sa.text("'manual'"),
        ),
        sa.Column(
            "manual_override", sa.Boolean(), nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("endpoint_path", sa.String(500), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True),
            nullable=False, server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), nullable=True,
        ),
        sa.Column(
            "deleted_at", sa.TIMESTAMP(timezone=True), nullable=True,
        ),
        sa.CheckConstraint(
            "source IN ('auto_endpoint', 'manual', 'import')",
            name="ck_marcos_timesheet_source",
        ),
        sa.CheckConstraint(
            "duration_minutes IS NULL OR duration_minutes >= 0",
            name="ck_marcos_timesheet_duration_nonneg",
        ),
    )
    op.create_index(
        "ix_marcos_timesheet_started_at_desc",
        "marcos_timesheet_entries",
        [sa.text("started_at DESC")],
    )

    # Marcos timesheet stores hours cross-client · admin-only ·
    # NO RLS by project (Marcos owner bypass anyway). Grant
    # fulkro_app full CRUD so the app role can write entries via
    # middleware + UI.
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON marcos_timesheet_entries "
        "TO fulkro_app"
    )


def downgrade() -> None:
    op.drop_index(
        "ix_marcos_timesheet_started_at_desc",
        table_name="marcos_timesheet_entries",
    )
    op.drop_table("marcos_timesheet_entries")
