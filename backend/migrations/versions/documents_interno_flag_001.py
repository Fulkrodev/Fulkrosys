"""documents.interno · flag de visibilidad (documento solo-interno)

Additive · NOT NULL DEFAULT false → los documentos existentes siguen visibles
para el cliente (comportamiento actual preservado). Marcos puede marcar un
documento como ``interno=true`` para que el portal cliente deje de mostrarlo
(borradores, notas de trabajo, documentos internos del consultor).

Revision ID: documents_interno_flag_001
Revises: invoice_email_enviado_at_001
Create Date: 2026-06-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "documents_interno_flag_001"
down_revision: Union[str, None] = "invoice_email_enviado_at_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column(
            "interno", sa.Boolean(),
            server_default=sa.text("false"), nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("documents", "interno")
