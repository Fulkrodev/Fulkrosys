"""seed_admin_email_marcosmata_001 · rota el email del admin sembrado

La migración ``a7f1e4b8c2d5`` siembra el único usuario admin (owner) con email
``marcos@fulkro.es``. Marcos rotó su email de login/identidad a
``marcosmata@fulkro.es`` (alineado con ``config.marcos_admin_email`` y
``fulkro_identity.FULKRO_EMAIL``). Esta migración renombra la fila sembrada para
que un despliegue fresco (Hetzner) o una BD de test recién construida nazcan con
el email correcto.

Idempotente: el ``WHERE email = 'marcos@fulkro.es'`` no afecta nada si la fila ya
está renombrada (p.ej. la BD local ya corregida a mano). Solo-datos: NO toca
password_hash, TOTP, WebAuthn ni el resto de columnas, y NO altera la cadena de
hash de ``audit_log`` (R6 append-only intacto · es un UPDATE de auth_users).

Revision ID: seed_admin_email_marcosmata_001
Revises: oauth_state_rls_001
Create Date: 2026-06-09
"""
from typing import Sequence, Union

from alembic import op


revision: str = "seed_admin_email_marcosmata_001"
down_revision: Union[str, None] = "oauth_state_rls_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "UPDATE auth_users SET email = 'marcosmata@fulkro.es' "
        "WHERE email = 'marcos@fulkro.es'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE auth_users SET email = 'marcos@fulkro.es' "
        "WHERE email = 'marcosmata@fulkro.es'"
    )
