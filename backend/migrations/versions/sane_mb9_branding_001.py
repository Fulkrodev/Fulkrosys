"""SAN-E MB-9 atom 9.1 · per-cliente branding columns.

Q1.B + Q2.C cement post audit [57/?]:
- clients.logo_path + logo_mime_type + logo_sha256 already existing
- ADD: primary_color + secondary_color (hex #RRGGBB) + footer_text (max 500)

CHECK constraints validate hex format + footer length.

Revision ID: sane_mb9_per_cliente_branding_001
Revises: sane_mb8_m31_whatsapp_001
Create Date: 2026-05-12
"""
from alembic import op
import sqlalchemy as sa


revision = "sane_mb9_branding_001"
down_revision = "sane_mb8_m31_whatsapp_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "clients",
        sa.Column("primary_color", sa.String(7), nullable=True),
    )
    op.add_column(
        "clients",
        sa.Column("secondary_color", sa.String(7), nullable=True),
    )
    op.add_column(
        "clients",
        sa.Column("footer_text", sa.Text(), nullable=True),
    )
    op.create_check_constraint(
        "ck_clients_primary_color_hex",
        "clients",
        "primary_color IS NULL OR primary_color ~ '^#[0-9A-Fa-f]{6}$'",
    )
    op.create_check_constraint(
        "ck_clients_secondary_color_hex",
        "clients",
        "secondary_color IS NULL OR secondary_color ~ '^#[0-9A-Fa-f]{6}$'",
    )
    op.create_check_constraint(
        "ck_clients_footer_text_length",
        "clients",
        "footer_text IS NULL OR char_length(footer_text) <= 500",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_clients_footer_text_length", "clients", type_="check",
    )
    op.drop_constraint(
        "ck_clients_secondary_color_hex", "clients", type_="check",
    )
    op.drop_constraint(
        "ck_clients_primary_color_hex", "clients", type_="check",
    )
    op.drop_column("clients", "footer_text")
    op.drop_column("clients", "secondary_color")
    op.drop_column("clients", "primary_color")
