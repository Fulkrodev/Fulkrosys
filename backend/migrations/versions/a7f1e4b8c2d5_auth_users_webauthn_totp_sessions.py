"""Auth foundation: users, WebAuthn credentials, TOTP, sessions, login attempts.

Adds hard authentication for Marcos (single user). No RLS on auth_* tables.

Seeds one user (``marcos@fulkro.es``) with placeholder password
``changeme_on_first_login`` and ``must_change_password=true``.

Revision ID: a7f1e4b8c2d5
Revises: b5d2a81f4e93
Create Date: 2026-04-19 21:00:00.000000
"""
from typing import Sequence, Union

import bcrypt
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "a7f1e4b8c2d5"
down_revision: Union[str, None] = "b5d2a81f4e93"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SEED_EMAIL = "marcos@fulkro.es"
SEED_PASSWORD_PLACEHOLDER = "changeme_on_first_login"
SEED_DISPLAY_NAME = "Marcos Mata Garcia"


def _common_cols():
    return [
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "auth_users",
        *_common_cols(),
        sa.Column("deleted_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "failed_login_attempts",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("locked_until", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_login_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.UniqueConstraint("email", name="uq_auth_users_email"),
    )

    op.create_table(
        "auth_webauthn_credentials",
        *_common_cols(),
        sa.Column("deleted_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("auth_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("credential_id", sa.LargeBinary(), nullable=False),
        sa.Column("public_key", sa.LargeBinary(), nullable=False),
        sa.Column(
            "sign_count", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("transports", postgresql.JSONB(), nullable=True),
        sa.Column("device_name", sa.String(length=255), nullable=True),
        sa.Column("last_used_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "credential_id", name="uq_auth_webauthn_credentials_credential_id"
        ),
    )
    op.create_index(
        "ix_auth_webauthn_credentials_user_id",
        "auth_webauthn_credentials",
        ["user_id"],
    )

    op.create_table(
        "auth_totp_secrets",
        *_common_cols(),
        sa.Column("deleted_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("auth_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("secret", sa.String(length=64), nullable=False),
        sa.Column(
            "verified", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.UniqueConstraint("user_id", name="uq_auth_totp_secrets_user_id"),
    )

    op.create_table(
        "auth_sessions",
        *_common_cols(),
        sa.Column("deleted_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("auth_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("jti", sa.String(length=64), nullable=False),
        sa.Column(
            "issued_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "expires_at", postgresql.TIMESTAMP(timezone=True), nullable=False
        ),
        sa.Column("revoked_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.UniqueConstraint("jti", name="uq_auth_sessions_jti"),
    )
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])
    op.create_index("ix_auth_sessions_expires_at", "auth_sessions", ["expires_at"])

    op.create_table(
        "auth_login_attempts",
        *_common_cols(),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column(
            "success", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("reason", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
    )
    op.create_index(
        "ix_auth_login_attempts_ip_created",
        "auth_login_attempts",
        ["ip_address", "created_at"],
    )
    op.create_index(
        "ix_auth_login_attempts_email_created",
        "auth_login_attempts",
        ["email", "created_at"],
    )

    password_hash = bcrypt.hashpw(
        SEED_PASSWORD_PLACEHOLDER.encode("utf-8"), bcrypt.gensalt(rounds=12)
    ).decode("utf-8")
    op.execute(
        sa.text(
            """
            INSERT INTO auth_users (
                email, password_hash, display_name,
                is_active, must_change_password
            ) VALUES (
                :email, :password_hash, :display_name, true, true
            ) ON CONFLICT (email) DO NOTHING
            """
        ).bindparams(
            email=SEED_EMAIL,
            password_hash=password_hash,
            display_name=SEED_DISPLAY_NAME,
        )
    )


def downgrade() -> None:
    op.drop_index("ix_auth_login_attempts_email_created", "auth_login_attempts")
    op.drop_index("ix_auth_login_attempts_ip_created", "auth_login_attempts")
    op.drop_table("auth_login_attempts")

    op.drop_index("ix_auth_sessions_expires_at", "auth_sessions")
    op.drop_index("ix_auth_sessions_user_id", "auth_sessions")
    op.drop_table("auth_sessions")

    op.drop_table("auth_totp_secrets")

    op.drop_index(
        "ix_auth_webauthn_credentials_user_id", "auth_webauthn_credentials"
    )
    op.drop_table("auth_webauthn_credentials")

    op.drop_table("auth_users")
