"""revoke_active_client_sessions_mf35

Revision ID: 76ecc899510d
Revises: c2af9c86c95d
Create Date: 2026-04-28 11:17:11.521751

Mini-Fase 3.5 unifica auth cliente bajo cookie httpOnly + CSRF
triple binding (BLOQUES 1-7). Sesiones cliente activas pre-MF3.5
fueron emitidas con un JWT que carece del claim ``role`` (añadido
en BLOQUE 7, commit 33f78a9). Esos tokens son incompatibles con
el middleware Next.js refactorizado: el dispatcher por
``claims.role`` los ve como ``role=undefined`` y los redirecta
fuera de cualquier portal.

Esta migración revoca todas las sesiones cliente activas para
forzar re-login con un JWT post-BLOQUE 7 (con role claim).

Patrón:
- ``UPDATE ... SET revoked_at = now() WHERE revoked_at IS NULL``
- Audit trail preservado (no DELETE; ``revoked_at`` queda
  registrado, fila histórica intacta para forensia / ENS
  trazabilidad accesos)
- Idempotente: sesiones ya revocadas no se tocan
- Schema ``client_sessions`` no tiene columna ``revoke_reason``
  — la justificación queda en este docstring + commit message

En staging/prod (Sesión 12 deploy a Hetzner): aplicar tras
deploy del refactor backend + frontend con ``alembic upgrade
head``. Clientes activos verán login screen al siguiente
request — UX correcta (mejor que redirect loop por JWT
incompatible).

Pre-migración dev: 9 sesiones activas (audit BLOQUE 8).
Post-migración dev: 0.

Ver ADR-017 + ADR-018 + TODO-AUTH-UNIFY-001 + Mini-Fase 3.5.
"""
from typing import Sequence, Union

from alembic import op


revision: str = '76ecc899510d'
down_revision: Union[str, None] = 'c2af9c86c95d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Revoca sesiones cliente activas para forzar re-login post-MF3.5."""
    op.execute(
        """
        UPDATE client_sessions
        SET revoked_at = now()
        WHERE revoked_at IS NULL
        """
    )


def downgrade() -> None:
    """Downgrade no-op: revocaciones no se deshacen.

    El audit trail es inmutable por diseño (ENS trazabilidad).
    Si se revierte el refactor, los clientes solo necesitarían
    re-login manual; resucitar sesiones revocadas sería peligroso
    (los tokens originales pueden haberse fugado en el intervalo).
    """
    pass
