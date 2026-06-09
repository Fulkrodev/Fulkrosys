"""sand_notif_prefs_001

SAN-D MB-16.1 · tabla notification_preferences per ClientUser
para NotificationOrchestrator (ADR-039).

Cliente decide canales (email · portal_sse) · DND timezone-aware
(IANA tz · ventana HH:MM local) · digest_mode (immediate MVP ·
hourly+daily diferidos MB-19+ DEC-MB16-DIGEST-MODE-IMMEDIATE-ONLY).

UNIQUE constraint client_user_id garantiza 1 row per usuario.
Defaults conservadores: email + portal_sse enabled · sin DND ·
Europe/Madrid · digest immediate.

Revision ID: sand_notif_prefs_001
Revises: sand_notif_events_001
Create Date: 2026-05-06
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "sand_notif_prefs_001"
down_revision = "sand_notif_events_001"
branch_labels = None
depends_on = None


_VALID_DIGEST_MODES = ("immediate", "hourly", "daily")
_TIME_HHMM_REGEX = r"^([01][0-9]|2[0-3]):[0-5][0-9]$"


def upgrade() -> None:
    op.create_table(
        "notification_preferences",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "client_user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("client_users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "email_enabled",
            sa.Boolean,
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "portal_sse_enabled",
            sa.Boolean,
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "dnd_start_local",
            sa.String(5),
            nullable=True,
        ),
        sa.Column(
            "dnd_end_local",
            sa.String(5),
            nullable=True,
        ),
        sa.Column(
            "timezone",
            sa.String(50),
            nullable=False,
            server_default="Europe/Madrid",
        ),
        sa.Column(
            "digest_mode",
            sa.String(20),
            nullable=False,
            server_default="immediate",
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
            f"digest_mode IN {_VALID_DIGEST_MODES}",
            name="ck_notification_prefs_digest_mode",
        ),
        sa.CheckConstraint(
            f"dnd_start_local IS NULL OR "
            f"dnd_start_local ~ '{_TIME_HHMM_REGEX}'",
            name="ck_notification_prefs_dnd_start_format",
        ),
        sa.CheckConstraint(
            f"dnd_end_local IS NULL OR "
            f"dnd_end_local ~ '{_TIME_HHMM_REGEX}'",
            name="ck_notification_prefs_dnd_end_format",
        ),
        sa.CheckConstraint(
            "(dnd_start_local IS NULL AND dnd_end_local IS NULL) OR "
            "(dnd_start_local IS NOT NULL AND dnd_end_local IS NOT NULL)",
            name="ck_notification_prefs_dnd_pair",
        ),
    )
    op.create_index(
        "ix_notification_preferences_client_user",
        "notification_preferences",
        ["client_user_id"],
    )

    op.execute(
        "ALTER TABLE notification_preferences ENABLE ROW LEVEL SECURITY"
    )
    op.execute(
        """
        CREATE POLICY notification_preferences_isolation
            ON notification_preferences
            FOR ALL TO fulkro_app
            USING (
                client_user_id::text = current_setting(
                    'app.current_client_user_id', true
                )
                OR current_setting('app.current_role_pool', true) = 'marcos'
            )
            WITH CHECK (
                client_user_id::text = current_setting(
                    'app.current_client_user_id', true
                )
                OR current_setting('app.current_role_pool', true) = 'marcos'
            )
        """,
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE ON notification_preferences "
        "TO fulkro_app"
    )


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS notification_preferences_isolation "
        "ON notification_preferences"
    )
    op.drop_index(
        "ix_notification_preferences_client_user",
        table_name="notification_preferences",
    )
    op.drop_table("notification_preferences")
