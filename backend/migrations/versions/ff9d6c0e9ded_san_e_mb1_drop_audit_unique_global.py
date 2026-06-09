"""san_e_mb1_drop_audit_unique_global

ADR-046 v3 SAN-E.MB-1.1.D: drop UNIQUE GLOBAL en client_user_audit.current_hash.

Bug pre-existente diseño: constraint UNIQUE GLOBAL es incorrecto. La integridad
de la audit hash chain es semánticamente PER-PROJECT, gobernada por
audit_log_service.verify_chain_integrity() que escanea per project_id.

Refactor SAN-E.MB-1.1.C (TOTP off cliente) hizo el método de auth determinista
('password' siempre, antes 'password' o 'password+totp') · expuso colisiones
hash entre clientes distintos haciendo login inicial (chain_index=0).

Solución: drop UNIQUE GLOBAL · mantener integridad per-project via service layer.
Sin re-create de constraint en downgrade porque rows existentes pueden tener
duplicados que impedirían recreación.

Revision ID: ff9d6c0e9ded
Revises: a6d892162a67
Create Date: 2026-05-07 21:07:48.758494
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers · alembic
revision: str = "ff9d6c0e9ded"
down_revision: Union[str, None] = "a6d892162a67"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop UNIQUE GLOBAL · mantener performance via index non-unique.

    Idempotente: usa DROP CONSTRAINT IF EXISTS y CREATE INDEX IF NOT EXISTS
    porque downgrade NO recrea la constraint (intencional · rows post-MB-1.1.C
    pueden tener duplicados legítimos). Re-upgrade tras downgrade debe ser safe.
    """
    op.execute(
        "ALTER TABLE client_user_audit "
        "DROP CONSTRAINT IF EXISTS client_user_audit_current_hash_key"
    )

    # Crear index NON-UNIQUE para mantener performance búsquedas hash
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_client_user_audit_current_hash "
        "ON client_user_audit (current_hash)"
    )


def downgrade() -> None:
    """Drop index helper · NO re-create UNIQUE (rows pueden tener duplicados)."""
    op.execute(
        "DROP INDEX IF EXISTS idx_client_user_audit_current_hash"
    )

    # NO re-create UNIQUE GLOBAL · rows pueden tener duplicados legítimos
    # post-MB-1.1.C (mismo canonical payload "password" + chain_index=0 cross-project).
    # Si downgrade necesario y hay duplicados · primero deduplicar manualmente.
    # Comentado intencionalmente:
    # op.create_unique_constraint(
    #     "client_user_audit_current_hash_key",
    #     "client_user_audit",
    #     ["current_hash"],
    # )
