"""invoices.email_enviado_at · timestamp dedicado de envío al cliente (P1-7)

Additive · nullable. Campo DEDICADO para el timestamp del envío del
email/notificación de la factura al cliente. Antes ``send_invoice`` reutilizaba
``verifactu_enviado_at`` (semántica de la cadena VeriFactu MB-7, NO de email) →
mezclaba dos conceptos. Se separan.

Revision ID: invoice_email_enviado_at_001
Revises: change_request_code_unique_001
Create Date: 2026-06-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "invoice_email_enviado_at_001"
down_revision: Union[str, None] = "change_request_code_unique_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "invoices",
        sa.Column("email_enviado_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("invoices", "email_enviado_at")
