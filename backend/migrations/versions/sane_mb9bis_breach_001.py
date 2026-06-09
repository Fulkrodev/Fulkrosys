"""SAN-E MB-9.bis atom 9.bis.2 · Breach (Art. 33) + Erasure (Art. 17) tables.

Two platform-global tables backing the GDPR data subject rights and
breach notification workflows exposed by ``m_compliance``:

- ``fulkro_breach_notifications`` · Art. 33 GDPR (72h SLA workflow)
- ``fulkro_erasure_requests``     · Art. 17 GDPR (cliente erasure)

Revision ID: sane_mb9bis_breach_001
Revises: sane_mb9bis_ropa_001
Create Date: 2026-05-12
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "sane_mb9bis_breach_001"
down_revision = "sane_mb9bis_ropa_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fulkro_breach_notifications",
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
        sa.Column("breach_code", sa.String(50), nullable=False, unique=True),
        sa.Column(
            "detected_at", postgresql.TIMESTAMP(timezone=True), nullable=False
        ),
        sa.Column("reported_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "notified_aepd_at", postgresql.TIMESTAMP(timezone=True), nullable=True
        ),
        sa.Column(
            "notified_clients_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column(
            "data_categories_affected",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("data_subjects_count", sa.Integer, nullable=True),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("root_cause", sa.Text, nullable=True),
        sa.Column("containment_actions", sa.Text, nullable=True),
        sa.Column("remediation_actions", sa.Text, nullable=True),
        sa.Column(
            "notification_status",
            sa.String(30),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "affected_client_user_ids",
            postgresql.ARRAY(sa.String()),
            nullable=True,
        ),
        sa.Column(
            "reporter_user_id", postgresql.UUID(as_uuid=True), nullable=True
        ),
        sa.Column("aepd_reference", sa.String(100), nullable=True),
        sa.CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name="ck_breach_severity",
        ),
        sa.CheckConstraint(
            "notification_status IN ('pending', 'aepd_notified', "
            "'clients_notified', 'closed_resolved', 'closed_no_action')",
            name="ck_breach_status",
        ),
    )
    op.create_index(
        "ix_fulkro_breach_notifications_detected_at",
        "fulkro_breach_notifications",
        ["detected_at"],
    )
    op.create_index(
        "ix_fulkro_breach_notifications_reported_at",
        "fulkro_breach_notifications",
        ["reported_at"],
    )
    op.create_index(
        "ix_fulkro_breach_notifications_notification_status",
        "fulkro_breach_notifications",
        ["notification_status"],
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON fulkro_breach_notifications "
        "TO fulkro_app"
    )

    op.create_table(
        "fulkro_erasure_requests",
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
            "client_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("client_users.id"),
            nullable=False,
        ),
        # Denormalized tenant for admin RLS-less lookup. Set at creation by
        # the cliente endpoint using the authenticated cliente.client_id.
        sa.Column(
            "tenant_client_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clients.id"),
            nullable=False,
        ),
        sa.Column(
            "requested_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("requester_reason", sa.Text, nullable=True),
        sa.Column(
            "status", sa.String(30), nullable=False, server_default="pending"
        ),
        sa.Column("processed_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("processed_by", sa.String(255), nullable=True),
        sa.Column("tombstone_data", postgresql.JSONB, nullable=True),
        sa.Column("rejection_reason", sa.Text, nullable=True),
        sa.Column(
            "audit_log_preserved",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'completed', "
            "'rejected_audit_retention')",
            name="ck_erasure_status",
        ),
    )
    op.create_index(
        "ix_fulkro_erasure_requests_client_user_id",
        "fulkro_erasure_requests",
        ["client_user_id"],
    )
    op.create_index(
        "ix_fulkro_erasure_requests_status",
        "fulkro_erasure_requests",
        ["status"],
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON fulkro_erasure_requests "
        "TO fulkro_app"
    )


def downgrade() -> None:
    op.drop_index(
        "ix_fulkro_erasure_requests_status",
        table_name="fulkro_erasure_requests",
    )
    op.drop_index(
        "ix_fulkro_erasure_requests_client_user_id",
        table_name="fulkro_erasure_requests",
    )
    op.drop_table("fulkro_erasure_requests")
    op.drop_index(
        "ix_fulkro_breach_notifications_notification_status",
        table_name="fulkro_breach_notifications",
    )
    op.drop_index(
        "ix_fulkro_breach_notifications_reported_at",
        table_name="fulkro_breach_notifications",
    )
    op.drop_index(
        "ix_fulkro_breach_notifications_detected_at",
        table_name="fulkro_breach_notifications",
    )
    op.drop_table("fulkro_breach_notifications")
