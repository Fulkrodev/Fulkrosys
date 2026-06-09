"""sand_notif_events_001

SAN-D MB-16.1 · tabla notification_events para audit immutable
del NotificationOrchestrator (ADR-039).

Persistencia per evento despachado: event_type · recipient ·
channels attempted/succeeded/failed · payload · template_used ·
status (queued · dispatching · delivered · failed · suppressed_dnd) ·
celery_task_id · timestamps lifecycle.

RLS por project_id cuando aplica · admin events sin project pasan
filtro via NULL project_id (Marcos owner ve todos).

Revision ID: sand_notif_events_001
Revises: sand_chat_threads_001
Create Date: 2026-05-06
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "sand_notif_events_001"
down_revision = "sand_chat_threads_001"
branch_labels = None
depends_on = None


_VALID_STATUSES = (
    "queued",
    "dispatching",
    "delivered",
    "failed",
    "suppressed_dnd",
)


def upgrade() -> None:
    op.create_table(
        "notification_events",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("event_type", sa.String(60), nullable=False),
        sa.Column(
            "recipient_user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("client_users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("recipient_email", sa.String(255), nullable=False),
        sa.Column(
            "project_id",
            UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "channels_attempted",
            JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "channels_succeeded",
            JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "channels_failed",
            JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "payload_jsonb",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("template_used", sa.String(100), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="queued",
        ),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column(
            "retry_count",
            sa.Integer,
            nullable=False,
            server_default="0",
        ),
        sa.Column("celery_task_id", sa.String(64), nullable=True),
        sa.Column(
            "email_log_id",
            UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "dispatched_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "delivered_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
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
            name="ck_notification_events_status",
        ),
    )
    op.create_index(
        "ix_notification_events_recipient_created",
        "notification_events",
        ["recipient_user_id", "created_at"],
    )
    op.create_index(
        "ix_notification_events_project_created",
        "notification_events",
        ["project_id", "created_at"],
    )
    op.create_index(
        "ix_notification_events_status_created",
        "notification_events",
        ["status", "created_at"],
    )
    op.create_index(
        "ix_notification_events_event_type_created",
        "notification_events",
        ["event_type", "created_at"],
    )

    op.execute(
        "ALTER TABLE notification_events ENABLE ROW LEVEL SECURITY"
    )
    op.execute(
        """
        CREATE POLICY notification_events_isolation ON notification_events
            FOR ALL TO fulkro_app
            USING (
                project_id IS NULL
                OR project_id::text = current_setting('app.current_project_id', true)
            )
            WITH CHECK (
                project_id IS NULL
                OR project_id::text = current_setting('app.current_project_id', true)
            )
        """,
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE ON notification_events TO fulkro_app"
    )


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS notification_events_isolation "
        "ON notification_events"
    )
    op.drop_index(
        "ix_notification_events_event_type_created",
        table_name="notification_events",
    )
    op.drop_index(
        "ix_notification_events_status_created",
        table_name="notification_events",
    )
    op.drop_index(
        "ix_notification_events_project_created",
        table_name="notification_events",
    )
    op.drop_index(
        "ix_notification_events_recipient_created",
        table_name="notification_events",
    )
    op.drop_table("notification_events")
