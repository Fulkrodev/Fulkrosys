"""WhatsApp OTP hardening: hash (widen col) + attempts lockout column.

El OTP de verificacion WhatsApp se guardaba EN CLARO (String(8)) y sin contador
de intentos (brute-force del espacio 10^6 dentro del TTL). Ahora se guarda como
SHA-256 hex (64 chars) y se anade un contador para lockout anti-brute-force.

Revision ID: whatsapp_otp_hash_attempts_001
Revises: lms_minutes_worm_attempts_001
Create Date: 2026-06-16
"""
from alembic import op
import sqlalchemy as sa


revision = "whatsapp_otp_hash_attempts_001"
down_revision = "lms_minutes_worm_attempts_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # OTP ahora SHA-256 hex (64) en vez de en claro (8).
    op.alter_column(
        "client_users",
        "whatsapp_verification_otp",
        type_=sa.String(64),
        existing_type=sa.String(8),
        existing_nullable=True,
    )
    # Contador de intentos · lockout anti-brute-force.
    op.add_column(
        "client_users",
        sa.Column(
            "whatsapp_otp_attempts",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("client_users", "whatsapp_otp_attempts")
    op.alter_column(
        "client_users",
        "whatsapp_verification_otp",
        type_=sa.String(8),
        existing_type=sa.String(64),
        existing_nullable=True,
    )
