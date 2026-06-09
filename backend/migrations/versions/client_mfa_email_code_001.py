"""client_mfa_email_code_001 · MFA cliente por CÓDIGO AL EMAIL (sustituye TOTP)

Directiva Marcos (2026-06-09): para los clientes el segundo factor debe ser un
código que se les envía (al email · entregable hoy sin gateway SMS) y teclean,
en vez de la app autenticadora TOTP ("más rollo"). Añade a ``client_users``:

  - mfa_method               VARCHAR(10) NOT NULL DEFAULT 'email'  ('email'|'totp')
  - mfa_email_code_hash       VARCHAR(64) NULL   (sha256 del código · nunca claro)
  - mfa_email_code_expires_at TIMESTAMPTZ NULL
  - mfa_email_code_attempts   INTEGER NOT NULL DEFAULT 0
  - mfa_email_code_sent_at    TIMESTAMPTZ NULL   (rate-limit del reenvío)

Additive · idempotente (IF NOT EXISTS) · nullable/con-default → seguro sobre BD
con filas. NO toca TOTP existente (compat method='totp'). NO altera audit_log
(R6 intacto).

Revision ID: client_mfa_email_code_001
Revises: seed_admin_email_marcosmata_001
Create Date: 2026-06-09
"""
from typing import Sequence, Union

from alembic import op


revision: str = "client_mfa_email_code_001"
down_revision: Union[str, None] = "seed_admin_email_marcosmata_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE client_users "
        "ADD COLUMN IF NOT EXISTS mfa_method VARCHAR(10) NOT NULL DEFAULT 'email', "
        "ADD COLUMN IF NOT EXISTS mfa_email_code_hash VARCHAR(64), "
        "ADD COLUMN IF NOT EXISTS mfa_email_code_expires_at TIMESTAMPTZ, "
        "ADD COLUMN IF NOT EXISTS mfa_email_code_attempts INTEGER NOT NULL DEFAULT 0, "
        "ADD COLUMN IF NOT EXISTS mfa_email_code_sent_at TIMESTAMPTZ"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE client_users "
        "DROP COLUMN IF EXISTS mfa_method, "
        "DROP COLUMN IF EXISTS mfa_email_code_hash, "
        "DROP COLUMN IF EXISTS mfa_email_code_expires_at, "
        "DROP COLUMN IF EXISTS mfa_email_code_attempts, "
        "DROP COLUMN IF EXISTS mfa_email_code_sent_at"
    )
