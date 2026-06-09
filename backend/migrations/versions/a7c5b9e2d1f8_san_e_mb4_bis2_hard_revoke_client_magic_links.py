"""san_e_mb4_bis2_hard_revoke_client_magic_links

SAN-E v3.MB-4.bis2 · ADR-020 v3 IMPLEMENTED FULLY:
- HARD-revoke todos los magic_links activos con deprecated_for_v3=true
- Sin nueva columna · usa revoked_at + revocado existing
- backup audit en progress/archive (commit MB-4.bis · 23 rows tracked)

SAN-E v3 está en desarrollo (NO producción · 0 clientes piloto activos con
links productivos en email) · soft-deprecation 30/60/90d = deuda disfrazada.
HARD coherente con cleanup M21 single-user-RW pattern.

Revision ID: a7c5b9e2d1f8
Revises: d4f8a2b6c3e9
Create Date: 2026-05-10
"""
from typing import Sequence, Union

from alembic import op


revision: str = "a7c5b9e2d1f8"
down_revision: Union[str, None] = "d4f8a2b6c3e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Hard-revoke todos los activos deprecated_for_v3=true
    op.execute("""
        UPDATE magic_links
        SET revoked_at = now(),
            revocado = true
        WHERE deprecated_for_v3 = true
          AND revoked_at IS NULL;
    """)


def downgrade() -> None:
    # NO restore · hard-deprecation deliberate · backup CSV archive existing
    # progress/archive/magic_links_client_pre_cleanup_2026-05-09.csv
    pass
