"""invoice correlative unique index · red de seguridad integridad fiscal (P0-3)

Additive · backward-compat. Crea un índice ÚNICO parcial sobre
``invoices.numero_correlativo`` para que un número de factura duplicado falle
ruidoso (IntegrityError) en vez de corromper en silencio la secuencia fiscal /
la cadena VeriFactu. Complementa el ``pg_advisory_xact_lock`` por (emisor, año)
añadido en ``billing_service.generate_invoice`` (que serializa la emisión y
evita la carrera COUNT(*)+1 entre los 3 entrypoints: admin, beat Celery m23 y
hito de contrato).

El número correlativo es global por emisor único (formato FULKRO-{año}-{NNNN}),
así que la unicidad es global. Se excluyen los NULL (facturas en borrador sin
número asignado todavía no consumen secuencia).

Revision ID: invoice_correlative_unique_001
Revises: m8_autopilot_canonical_001
Create Date: 2026-06-09
"""
from typing import Sequence, Union

from alembic import op


revision: str = "invoice_correlative_unique_001"
down_revision: Union[str, None] = "m8_autopilot_canonical_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_invoices_numero_correlativo
        ON invoices (numero_correlativo)
        WHERE numero_correlativo IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_invoices_numero_correlativo")
