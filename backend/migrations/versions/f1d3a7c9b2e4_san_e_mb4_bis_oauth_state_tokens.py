"""san_e_mb4_bis_oauth_state_tokens

SAN-E v3.MB-4.2.bis · M16 portal extension Q2-A:
- NEW table oauth_state_tokens (anti-CSRF state per OAuth flow)
  · 10min TTL · 1-time use · client_user_id + project_id scope

Revision ID: f1d3a7c9b2e4
Revises: e8b1f4d7a2c5
Create Date: 2026-05-09
"""
from typing import Sequence, Union

from alembic import op


revision: str = "f1d3a7c9b2e4"
down_revision: Union[str, None] = "e8b1f4d7a2c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS oauth_state_tokens (
            id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            state_token     varchar(128) NOT NULL UNIQUE,
            client_user_id  uuid NOT NULL REFERENCES client_users(id) ON DELETE CASCADE,
            project_id      uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            connector_type  varchar(32) NOT NULL,
            redirect_uri    varchar(512) NOT NULL,
            code_verifier   varchar(128),
            expires_at      timestamptz NOT NULL,
            consumed_at     timestamptz,
            created_at      timestamptz NOT NULL DEFAULT now()
        );
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_oauth_state_expires "
        "ON oauth_state_tokens (expires_at);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_oauth_state_client_project "
        "ON oauth_state_tokens (client_user_id, project_id);"
    )
    # GRANTs · fulkro_app role debe tener acceso (NOSUPERUSER · no hereda
    # privilegios automáticamente del owner fulkro_migrate).
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE oauth_state_tokens "
        "TO fulkro_app"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_oauth_state_client_project;")
    op.execute("DROP INDEX IF EXISTS ix_oauth_state_expires;")
    op.execute("DROP TABLE IF EXISTS oauth_state_tokens;")
