"""san_b_verification_runs_ssh_credentials

Revision ID: 75c6f519dab6
Revises: 1abd530a7869
Create Date: 2026-05-04 16:12:45.504935

Adds dedicated TEXT column ``verification_runs.ssh_credentials`` para
hostear SSH credentials cifradas con Fernet (formato URL-safe base64)
por run. NULL = run local; non-NULL = remote audit (Lynis SSH).

Format pre-encrypt JSON:
  {
    "host": "10.0.0.5",
    "port": 22,
    "user": "root",
    "auth_method": "key" | "password",
    "key_path_local": "/secure/path/cliente.pem"  # auth_method=key
    # OR "password": "..."                          # auth_method=password
  }

Cifrado: Fernet (AES-128-CBC + HMAC-SHA256) clave derivada de
``app_secret_key`` vía ``ssh_credentials_crypto.encrypt_credentials``.
Pattern replicado de m16_onboarding/token_encryption.py.

Refs: SAN-B.MB-3.bis.2 · cierre TODO-M8-G2 backlog formal
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '75c6f519dab6'
down_revision: Union[str, None] = '1abd530a7869'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "verification_runs",
        sa.Column("ssh_credentials", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("verification_runs", "ssh_credentials")
