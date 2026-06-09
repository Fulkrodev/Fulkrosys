"""mb11_aepd_notifications

SAN-C MB-11.2 · Tabla aepd_notifications RGPD art.33-34 (deadline 72h).

Revision ID: mb11_aepd
Revises: mb11_bia_aware
Create Date: 2026-05-05 (SAN-C MB-11.2)
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "mb11_aepd"
down_revision: Union[str, None] = "mb11_bia_aware"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "aepd_notifications",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            primary_key=True, server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "project_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id"), nullable=False,
        ),
        sa.Column(
            "incident_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("incidents.id"), nullable=True,
        ),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("requires_notification", sa.Boolean, nullable=False),
        sa.Column(
            "notify_subjects", sa.Boolean,
            server_default=sa.text("false"), nullable=False,
        ),
        sa.Column("deadline_hours", sa.Integer, nullable=True),
        sa.Column("decision_tree_path", postgresql.JSONB, nullable=True),
        sa.Column(
            "notification_status", sa.String(20),
            server_default=sa.text("'pending'"), nullable=False,
        ),
        sa.Column("aepd_reference", sa.String(100), nullable=True),
        sa.Column("detected_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_aepd_notifications_project_id",
        "aepd_notifications",
        ["project_id"],
    )
    op.create_index(
        "ix_aepd_notifications_incident_id",
        "aepd_notifications",
        ["incident_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_aepd_notifications_incident_id", table_name="aepd_notifications",
    )
    op.drop_index(
        "ix_aepd_notifications_project_id", table_name="aepd_notifications",
    )
    op.drop_table("aepd_notifications")
