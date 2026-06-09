"""M21 Portal Cliente — client_users + client_sessions + client_user_audit.

Revision ID: c9a3b7f5d201
Revises: f8e2a4b5c301
Create Date: 2026-04-22 13:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "c9a3b7f5d201"
down_revision = "f8e2a4b5c301"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── client_users ─────────────────────────────────────────────────
    op.create_table(
        "client_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("client_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("clients.id"),
                  nullable=False, index=True),
        sa.Column("email", sa.String(255), nullable=False, index=True),
        sa.Column("password_hash", sa.String(100), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("dni", sa.String(20), nullable=True),
        sa.Column("role", sa.String(40), nullable=False,
                  server_default=sa.text("'lectura_solo'"), index=True),
        sa.Column("custom_role_description", sa.Text(), nullable=True),
        sa.Column("scopes_jsonb", postgresql.JSONB(astext_type=sa.Text()),
                  nullable=True),
        sa.Column("totp_secret_encrypted", sa.LargeBinary(), nullable=True),
        sa.Column("totp_enabled", sa.Boolean(),
                  nullable=False, server_default=sa.text("false")),
        sa.Column("must_change_password", sa.Boolean(),
                  nullable=False, server_default=sa.text("true")),
        sa.Column("last_login", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("password_changed_at", sa.TIMESTAMP(timezone=True),
                  nullable=True),
        sa.Column("locked_until", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("failed_attempts", sa.Integer(),
                  nullable=False, server_default="0"),
        sa.Column("created_by_marcos", sa.Boolean(),
                  nullable=False, server_default=sa.text("true")),
        sa.Column("deactivated_at", sa.TIMESTAMP(timezone=True),
                  nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("now()"),
                  onupdate=sa.text("now()"), nullable=True),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index(
        "uq_client_users_client_email",
        "client_users",
        ["client_id", "email"],
        unique=True,
    )

    # ── client_sessions ──────────────────────────────────────────────
    op.create_table(
        "client_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("client_user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("client_users.id"),
                  nullable=False, index=True),
        sa.Column("jwt_jti", sa.String(100),
                  nullable=False, unique=True, index=True),
        sa.Column("jwt_token_hash", sa.String(64), nullable=False),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True),
                  nullable=False, index=True),
        sa.Column("revoked_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_activity", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("now()"),
                  onupdate=sa.text("now()"), nullable=True),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )

    # ── client_user_audit ────────────────────────────────────────────
    op.create_table(
        "client_user_audit",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("client_user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("client_users.id"),
                  nullable=True, index=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True),
                  nullable=True, index=True),
        sa.Column("action", sa.String(50), nullable=False, index=True),
        sa.Column("metadata_jsonb", postgresql.JSONB(astext_type=sa.Text()),
                  nullable=True),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("client_user_audit")
    op.drop_table("client_sessions")
    op.drop_index("uq_client_users_client_email", table_name="client_users")
    op.drop_table("client_users")
