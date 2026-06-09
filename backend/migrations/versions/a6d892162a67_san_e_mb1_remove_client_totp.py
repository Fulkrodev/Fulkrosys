"""san_e_mb1_remove_client_totp

ADR-046 SAN-E.MB-1.1: cliente NO tiene TOTP/MFA. Solo magic link +
password opcional. Decisión Marcos: cliente piloto-friendly.

Admin (tabla auth_users + auth_totp_secrets) mantiene TOTP intacto.

BREAKING CHANGE: client_users con totp_enabled=true pierden 2FA al
upgrade. Acceso vía magic link sigue funcionando · password también
si lo tenían configurado.

Revision ID: a6d892162a67
Revises: sand_magic_link_migration
Create Date: 2026-05-07
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers · alembic
revision: str = "a6d892162a67"
down_revision: Union[str, None] = "sand_magic_link_migration"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop TOTP columns from client_users.

    Confirmado live (atom 1.1.A-bis):
    - totp_secret_encrypted: LargeBinary (bytea) nullable
    - totp_enabled: Boolean NOT NULL default false

    NO toca client_sessions (sin columns MFA).
    NO toca auth_users / auth_totp_secrets (admin intacto).
    """
    op.drop_column("client_users", "totp_secret_encrypted")
    op.drop_column("client_users", "totp_enabled")


def downgrade() -> None:
    """Restore TOTP columns en client_users.

    Sin recovery de data · columns nullable o con default false.
    Clientes que tenían TOTP enrolled antes del upgrade NO se recuperan.
    """
    op.add_column(
        "client_users",
        sa.Column("totp_secret_encrypted", sa.LargeBinary(), nullable=True),
    )
    op.add_column(
        "client_users",
        sa.Column(
            "totp_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
