"""Sesión 3B-2B.8 CLUSTER 6 Phase 6A · MFA TOTP cliente tables.

ADD client_user_totp_secrets + client_user_backup_codes tables + mfa_enabled
column on client_users.

Filosofía cliente-mínimo: cliente PUEDE opt-in MFA voluntary · NO obligatory
· protege portal acceso (8% deal-breaker MEDIA piloto · ROI security).

OPS-045 57ª manifestation · audit reveals admin auth_totp_secrets canonical
shape (60% schema reusable) + pyotp lib + totp_svc.py helpers existing.

Mirror admin auth_totp_secrets pattern · 1 secret per client_user (unique
FK) · verified boolean activates MFA gate at login.

Backup codes: 10 generated post-confirm · hashed SHA-256 (bcrypt overkill
single-use limit) · displayed ONCE · cliente downloads notes.

Revision ID: cluster6_client_mfa_001
Revises: c5_notif_prefs_extend_001
Create Date: 2026-05-27
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "cluster6_client_mfa_001"
down_revision: Union[str, None] = "c5_notif_prefs_extend_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # client_users.mfa_enabled column
    op.add_column(
        "client_users",
        sa.Column(
            "mfa_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # client_user_totp_secrets table (mirror auth_totp_secrets shape)
    op.create_table(
        "client_user_totp_secrets",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "client_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("client_users.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("secret", sa.String(64), nullable=False),
        sa.Column(
            "verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            # OPS-046: FullMixin NO setea updated_at en INSERT (solo onupdate),
            # y el ORM emite updated_at=NULL explícito · NOT NULL rompía el
            # enrolamiento MFA en BD construida desde migraciones (latente para
            # deploy fresco Hetzner FASE J). Canónico = nullable (== live dev).
            # Ejecutable 8 Pasada 16 · DB-DRIFT-02.
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "deleted_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "confirmed_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "last_used_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )

    # client_user_backup_codes table (10 codes single-use)
    op.create_table(
        "client_user_backup_codes",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "client_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("client_users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column(
            "used_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_client_user_backup_codes_unused",
        "client_user_backup_codes",
        ["client_user_id"],
        postgresql_where=sa.text("used_at IS NULL"),
    )

    # GRANTs for fulkro_app runtime role (RLS pattern existing motors)
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON "
        "client_user_totp_secrets TO fulkro_app"
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON "
        "client_user_backup_codes TO fulkro_app"
    )


def downgrade() -> None:
    op.drop_index(
        "ix_client_user_backup_codes_unused",
        table_name="client_user_backup_codes",
    )
    op.drop_table("client_user_backup_codes")
    op.drop_table("client_user_totp_secrets")
    op.drop_column("client_users", "mfa_enabled")
