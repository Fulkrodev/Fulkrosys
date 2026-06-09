"""san_e_mb3_cleanup_invalidate_legacy_client_sessions

ADR-013 v3 SAN-E.MB-3.cleanup polish · invalida sesiones cliente legacy
con JWT claims.role = 'rseg|lectura_solo|director_ti|...' (8 valores
multi-role pre-cleanup).

Razón: post commit 4 frontend, isClientRole(role) solo acepta 'rw'
(CLIENT_PORTAL_SCOPE). Sesiones activas con claims.role legacy
caen a redirect /login con mensaje 'session expired' inexplicable
para el user. Mejor: revocarlas explicitamente · forzar re-login
limpio que emite JWT con claims.role = 'rw'.

Tabla: client_sessions (NO auth_client_sessions). Schema: solo columna
revoked_at (no revoked_reason · simpler que briefing).

Idempotente: 0 sesiones activas actualmente (183 totales · todas
expiradas o revoked). Esta migration es salvaguarda · si Marcos hace
upgrade tras tener sesiones activas pre-cleanup las revoca atomicamente.

Revision ID: e8b1f4d7a2c5
Revises: d7e9a3b5c1f4
Create Date: 2026-05-08
"""
from typing import Sequence, Union

from alembic import op


revision: str = "e8b1f4d7a2c5"
down_revision: Union[str, None] = "d7e9a3b5c1f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Revoca sesiones cliente activas pre-cleanup · 0 UX confusion."""
    op.execute(
        """
        UPDATE client_sessions
        SET revoked_at = NOW()
        WHERE revoked_at IS NULL
          AND expires_at > NOW()
          AND deleted_at IS NULL;
        """
    )


def downgrade() -> None:
    """No-op deliberate · sessions revoked legacy NO se restauran.

    Re-running upgrade tras downgrade es idempotente (sessions ya revocadas
    NO se re-revocan · WHERE revoked_at IS NULL filtra).
    """
    pass
