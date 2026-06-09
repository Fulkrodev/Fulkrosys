"""Ejecutable 7.7 · ALTER signing_events ADD canvas TIER 1 columns.

ADD columns:
- signature_canvas_dataurl TEXT NULL (base64 PNG · S3 migration Future-X FASE J)
- signed_name VARCHAR(120) NULL
- signed_surname VARCHAR(120) NULL

NO new table · extends existing m05_signing signing_events. Additive only ·
backwards-compat con OTP path · TIER 1 canvas path bypass OTP cuando fields
populated.

Revision: esignature_canvas_tier1_001
Down: 2ddffdcdddfc
"""
from __future__ import annotations

from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "esignature_canvas_tier1_001"
down_revision: Union[str, None] = "2ddffdcdddfc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "signing_events",
        sa.Column("signature_canvas_dataurl", sa.Text(), nullable=True),
    )
    op.add_column(
        "signing_events",
        sa.Column("signed_name", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "signing_events",
        sa.Column("signed_surname", sa.String(length=120), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("signing_events", "signed_surname")
    op.drop_column("signing_events", "signed_name")
    op.drop_column("signing_events", "signature_canvas_dataurl")
