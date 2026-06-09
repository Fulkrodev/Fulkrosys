"""san_e_mb4_bis3_client_notifications

SAN-E v3.MB-4.bis3 · ADR-020 IMPLEMENTED FULLY:
- NEW table client_notifications (substitute para magic_link cliente)
- Reuso column client_users.must_change_password EXISTING para PRIMER_ACCESO_CLIENTE
  refactor (NO se añade columna nueva · ya existe `must_change_password` desde
  cleanup M21 single-user-RW).

Revision ID: b8e1d4f7a3c5
Revises: a7c5b9e2d1f8
Create Date: 2026-05-10
"""
from typing import Sequence, Union

from alembic import op


revision: str = "b8e1d4f7a3c5"
down_revision: Union[str, None] = "a7c5b9e2d1f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS client_notifications (
            id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            project_id          uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            client_user_id      uuid NOT NULL REFERENCES client_users(id) ON DELETE CASCADE,
            type                varchar(64) NOT NULL,
            title               varchar(255) NOT NULL,
            body                text,
            target_url          varchar(512) NOT NULL,
            priority            varchar(16) NOT NULL DEFAULT 'normal',
            payload_json        jsonb,
            emitted_by_motor    varchar(32) NOT NULL,
            read_at             timestamptz,
            dismissed_at        timestamptz,
            actioned_at         timestamptz,
            expires_at          timestamptz,
            created_at          timestamptz NOT NULL DEFAULT now()
        );
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_client_notif_project "
        "ON client_notifications (project_id);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_client_notif_user "
        "ON client_notifications (client_user_id);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_client_notif_type "
        "ON client_notifications (type);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_client_notif_unread "
        "ON client_notifications (client_user_id, read_at);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_client_notif_created "
        "ON client_notifications (created_at);"
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE ON TABLE client_notifications "
        "TO fulkro_app;"
    )

    # NOTA: NO se añade columna requires_password_change · reuso
    # column existing client_users.must_change_password (M21 cleanup).


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_client_notif_created;")
    op.execute("DROP INDEX IF EXISTS ix_client_notif_unread;")
    op.execute("DROP INDEX IF EXISTS ix_client_notif_type;")
    op.execute("DROP INDEX IF EXISTS ix_client_notif_user;")
    op.execute("DROP INDEX IF EXISTS ix_client_notif_project;")
    op.execute("DROP TABLE IF EXISTS client_notifications;")
