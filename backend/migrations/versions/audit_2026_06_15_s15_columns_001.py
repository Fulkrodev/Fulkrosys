"""audit_2026_06_15_s15_columns_001 · §1.5/§2.2 additive columns + FK

Campaña fix/audit-2026-06-15 · 3 cambios aditivos (seguros · backward-compat):

1. §1.5 M07 · evidence.firma_timestamp (VARCHAR(40) NULL) — guarda el timestamp
   ISO usado en el payload firmado para poder RE-VERIFICAR la firma Ed25519
   (antes signature_valid=None porque no se conservaba el payload original).
   Filas existentes → NULL → signature_valid=None (graceful · sin romper nada).

2. §1.5 M12 · magic_links.otp_expires_at (TIMESTAMPTZ NULL) — expiración propia
   corta del OTP, independiente del TTL del link (antes el OTP vivía lo que el
   link, hasta 120 días). Links existentes → NULL → sin expiración propia.

3. §2.2 · FK diagnosis_runs.project_id → projects.id (ondelete CASCADE). La
   columna ya era NOT NULL + indexada y siempre apunta a un proyecto real; sólo
   faltaba la constraint (inconsistente con el resto de tablas project-scoped).

Revision ID: audit_2026_06_15_s15_columns_001
Revises: client_messages_rls_failclosed_001
Create Date: 2026-06-15
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "audit_2026_06_15_s15_columns_001"
down_revision: Union[str, None] = "client_messages_rls_failclosed_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. evidence.firma_timestamp
    op.add_column(
        "evidence",
        sa.Column("firma_timestamp", sa.String(length=40), nullable=True),
    )
    # 2. magic_links.otp_expires_at
    op.add_column(
        "magic_links",
        sa.Column(
            "otp_expires_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )
    # 3. FK diagnosis_runs.project_id → projects.id
    op.create_foreign_key(
        "fk_diagnosis_runs_project_id",
        "diagnosis_runs",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_diagnosis_runs_project_id", "diagnosis_runs", type_="foreignkey",
    )
    op.drop_column("magic_links", "otp_expires_at")
    op.drop_column("evidence", "firma_timestamp")
