"""SAN-E MB-9.bis atom 9.bis.5 · sub_processor_subscribers table.

Public anonymous email subscription list for sub-processor change
notifications (Art. 28.2 GDPR transparency). No project_id, no auth —
unique constraint on lowercased email.

Revision ID: sane_mb9bis_subs_001
Revises: sane_mb9bis_monitor_001
Create Date: 2026-05-12
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "sane_mb9bis_subs_001"
down_revision = "sane_mb9bis_monitor_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sub_processor_subscribers",
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
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column(
            "consent_given_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
        ),
        sa.Column("unsubscribed_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_notified_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
    )
    # unique=True on the email column already creates a UNIQUE constraint
    # with a backing index (sub_processor_subscribers_email_key). No
    # separate op.create_index needed — would create a duplicate.
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON sub_processor_subscribers "
        "TO fulkro_app"
    )


def downgrade() -> None:
    op.drop_table("sub_processor_subscribers")
