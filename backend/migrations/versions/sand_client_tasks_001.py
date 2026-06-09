"""sand_client_tasks_001

SAN-D MB-14.3 · tabla client_tasks per project · workspace continuo
cliente (ADR-038). Templates auto-generan tasks en transitions
workflow_phase.

Status values: pending | in_progress | blocked | done

Revision ID: sand_client_tasks_001
Revises: sand_client_audit_chain_001
Create Date: 2026-05-06
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "sand_client_tasks_001"
down_revision = "sand_client_audit_chain_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "client_tasks",
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
            "client_user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("client_users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("template_id", sa.String(80), nullable=False),
        sa.Column("phase", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("cta_label", sa.String(100), nullable=True),
        sa.Column("cta_url", sa.String(500), nullable=True),
        sa.Column("expected_evidence_type", sa.String(80), nullable=True),
        sa.Column("expected_evidence_count", sa.Integer, server_default="1"),
        sa.Column("priority", sa.Integer, server_default="0"),
        sa.Column(
            "status",
            sa.String(20),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("due_date", sa.Date, nullable=True),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("blocked_reason", sa.Text, nullable=True),
        sa.Column("metadata_jsonb", JSONB, nullable=True),
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
        sa.UniqueConstraint(
            "project_id", "template_id",
            name="uq_client_tasks_project_template",
        ),
    )

    op.create_index(
        "ix_client_tasks_project_status",
        "client_tasks",
        ["project_id", "status"],
    )
    op.create_index(
        "ix_client_tasks_phase", "client_tasks", ["phase"],
    )

    op.execute("ALTER TABLE client_tasks ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY client_tasks_isolation ON client_tasks
            FOR ALL TO fulkro_app
            USING (project_id::text = current_setting('app.current_project_id', true))
            WITH CHECK (project_id::text = current_setting('app.current_project_id', true))
        """,
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE ON client_tasks TO fulkro_app"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS client_tasks_isolation ON client_tasks")
    op.drop_index("ix_client_tasks_phase", table_name="client_tasks")
    op.drop_index(
        "ix_client_tasks_project_status", table_name="client_tasks",
    )
    op.drop_table("client_tasks")
