"""SAN-E MB-9.bis atom 9.bis.6 · FULKRO Self-Monitoring System tables.

Three platform-global tables (no RLS, no tenant context) backing the
autonomous compliance verification subsystem:

- ``compliance_checks``  · registry of 17 named checks (latest state)
- ``compliance_alerts``  · append-only alert ledger
- ``compliance_reports`` · weekly/monthly status report artifacts

Each table is admin-only (no client access). RLS is not enabled because
the data describes the FULKRO platform itself, not cliente data.

Revision ID: sane_mb9bis_monitor_001
Revises: sane_mb9_rls_focused_002
Create Date: 2026-05-12
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "sane_mb9bis_monitor_001"
down_revision = "sane_mb9_rls_focused_002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "compliance_checks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at", postgresql.TIMESTAMP(timezone=True), nullable=True
        ),
        sa.Column("check_name", sa.String(100), nullable=False, unique=True),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("frequency", sa.String(20), nullable=False),
        sa.Column(
            "severity_threshold", sa.String(20), nullable=False, server_default="medium"
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="unknown"),
        sa.Column("last_run_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("next_run_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_result", postgresql.JSONB, nullable=True),
        sa.Column(
            "consecutive_failures",
            sa.Integer,
            nullable=False,
            server_default="0",
        ),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("regulatory_basis", sa.String(255), nullable=True),
    )
    op.create_index(
        "ix_compliance_checks_status",
        "compliance_checks",
        ["status"],
    )
    op.create_index(
        "ix_compliance_checks_frequency",
        "compliance_checks",
        ["frequency"],
    )
    op.create_index(
        "ix_compliance_checks_next_run_at",
        "compliance_checks",
        ["next_run_at"],
    )

    op.create_table(
        "compliance_alerts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "check_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("compliance_checks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("check_name", sa.String(100), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("details", postgresql.JSONB, nullable=True),
        sa.Column(
            "triggered_at", postgresql.TIMESTAMP(timezone=True), nullable=False
        ),
        sa.Column(
            "resolved_at", postgresql.TIMESTAMP(timezone=True), nullable=True
        ),
        sa.Column("resolved_by", sa.String(255), nullable=True),
        sa.Column("resolution_note", sa.Text, nullable=True),
        sa.Column(
            "auto_resolved", sa.Boolean, nullable=False, server_default=sa.text("false")
        ),
        sa.Column("email_sent_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_compliance_alerts_status",
        "compliance_alerts",
        ["status"],
    )
    op.create_index(
        "ix_compliance_alerts_check_id",
        "compliance_alerts",
        ["check_id"],
    )
    op.create_index(
        "ix_compliance_alerts_triggered_at",
        "compliance_alerts",
        ["triggered_at"],
    )

    op.create_table(
        "compliance_reports",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("report_type", sa.String(50), nullable=False),
        sa.Column("period_start", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("period_end", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("summary", postgresql.JSONB, nullable=False),
        sa.Column("body_markdown", sa.Text, nullable=True),
        sa.Column("storage_mode", sa.String(20), nullable=False),
        sa.Column("storage_path", sa.String(1000), nullable=True),
        sa.Column("signed_url", sa.String(2000), nullable=True),
        sa.Column(
            "signed_url_expires_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column("email_sent_to", sa.String(255), nullable=True),
        sa.Column("email_sent_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("generated_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_compliance_reports_generated_at",
        "compliance_reports",
        ["generated_at"],
    )
    op.create_index(
        "ix_compliance_reports_report_type",
        "compliance_reports",
        ["report_type"],
    )

    for table in ("compliance_checks", "compliance_alerts", "compliance_reports"):
        op.execute(
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO fulkro_app"
        )


def downgrade() -> None:
    for ix, table in [
        ("ix_compliance_reports_report_type", "compliance_reports"),
        ("ix_compliance_reports_generated_at", "compliance_reports"),
        ("ix_compliance_alerts_triggered_at", "compliance_alerts"),
        ("ix_compliance_alerts_check_id", "compliance_alerts"),
        ("ix_compliance_alerts_status", "compliance_alerts"),
        ("ix_compliance_checks_next_run_at", "compliance_checks"),
        ("ix_compliance_checks_frequency", "compliance_checks"),
        ("ix_compliance_checks_status", "compliance_checks"),
    ]:
        op.drop_index(ix, table_name=table)
    op.drop_table("compliance_reports")
    op.drop_table("compliance_alerts")
    op.drop_table("compliance_checks")
