"""ola2_contracts_a_alcance_snapshot_documento_sha256

Revision ID: ola2_contracts_a_001
Revises: lead_hydration_7_5_001
Create Date: 2026-06-03

Ola 2 (cierre comercial · FASE B/C). Migración **additive** y **nullable**
(segura sobre filas existentes):

- ``contracts.alcance_snapshot`` (JSONB) → congela el alcance COMERCIAL del
  contrato al generarlo (categoría + sistemas/sedes/exclusiones de la Proposal ·
  #10 B1) para trazabilidad legal/ENAC. Es el alcance contractual (§1), distinto
  del alcance ENS narrativo del E-155 (entregable post-firma · #10 B2).
- ``contracts.documento_sha256`` (VARCHAR 64) → hash SHA-256 sobre los BYTES del
  DOCX/PDF canónico del contrato (FASE C · #42). Lo consume #43 como
  ``document_hash_sha256`` del SigningIntent (m05 canvas Ed25519). Distinto del
  ``hash_sha256`` existente, que hashea campos ORM (NO los bytes del documento).

Scope-only (política TODO-DB-DRIFT-001 · sin autogenerate). Todo nullable →
``fulkro_app`` hereda el GRANT de tabla. Reversible.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "ola2_contracts_a_001"
down_revision: Union[str, None] = "lead_hydration_7_5_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "contracts",
        sa.Column(
            "alcance_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "contracts",
        sa.Column("documento_sha256", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("contracts", "documento_sha256")
    op.drop_column("contracts", "alcance_snapshot")
