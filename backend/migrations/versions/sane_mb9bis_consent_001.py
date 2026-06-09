"""SAN-E MB-9.bis atom 9.bis.1 · Cookie consent BD + audit log.

Adds the 7 consent-state columns to ``client_users`` and creates the
append-only ``fulkro_consent_audit_log`` table (Art. 7 GDPR
demonstrability obligation · Guía AEPD 2020 cookies §4.5).

Revision ID: sane_mb9bis_consent_001
Revises: sane_mb9bis_breach_001
Create Date: 2026-05-12
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "sane_mb9bis_consent_001"
down_revision = "sane_mb9bis_breach_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── client_users · 7 consent state columns ─────────────────────
    op.add_column(
        "client_users",
        sa.Column(
            "consent_functional",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "client_users",
        sa.Column(
            "consent_analytics",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "client_users",
        sa.Column(
            "consent_marketing",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "client_users",
        sa.Column("consent_timestamp", postgresql.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "client_users",
        sa.Column("consent_renewal_due", postgresql.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "client_users",
        sa.Column("consent_ip_address", postgresql.INET, nullable=True),
    )
    op.add_column(
        "client_users",
        sa.Column("consent_user_agent", sa.Text, nullable=True),
    )

    # ── fulkro_consent_audit_log · append-only ledger ─────────────
    op.create_table(
        "fulkro_consent_audit_log",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("client_users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "anonymous_session_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "tenant_client_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clients.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "timestamp",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("action_type", sa.String(40), nullable=False),
        sa.Column("old_state", postgresql.JSONB, nullable=True),
        sa.Column("new_state", postgresql.JSONB, nullable=False),
        sa.Column("ip_address", postgresql.INET, nullable=True),
        sa.Column("user_agent", sa.Text, nullable=True),
        sa.Column("page_url", sa.Text, nullable=True),
        sa.CheckConstraint(
            "action_type IN ('initial_consent', 'user_modified', "
            "'user_revoked', 'renewal_24m_trigger', 'renewal_24m_confirmed')",
            name="ck_consent_audit_action",
        ),
    )
    op.create_index(
        "ix_fulkro_consent_audit_log_user_id",
        "fulkro_consent_audit_log",
        ["user_id"],
    )
    op.create_index(
        "ix_fulkro_consent_audit_log_anonymous_session_id",
        "fulkro_consent_audit_log",
        ["anonymous_session_id"],
    )
    op.create_index(
        "ix_fulkro_consent_audit_log_timestamp",
        "fulkro_consent_audit_log",
        ["timestamp"],
    )
    op.execute(
        "GRANT SELECT, INSERT ON fulkro_consent_audit_log TO fulkro_app"
    )


def downgrade() -> None:
    op.drop_index(
        "ix_fulkro_consent_audit_log_timestamp",
        table_name="fulkro_consent_audit_log",
    )
    op.drop_index(
        "ix_fulkro_consent_audit_log_anonymous_session_id",
        table_name="fulkro_consent_audit_log",
    )
    op.drop_index(
        "ix_fulkro_consent_audit_log_user_id",
        table_name="fulkro_consent_audit_log",
    )
    op.drop_table("fulkro_consent_audit_log")
    op.drop_column("client_users", "consent_user_agent")
    op.drop_column("client_users", "consent_ip_address")
    op.drop_column("client_users", "consent_renewal_due")
    op.drop_column("client_users", "consent_timestamp")
    op.drop_column("client_users", "consent_marketing")
    op.drop_column("client_users", "consent_analytics")
    op.drop_column("client_users", "consent_functional")
