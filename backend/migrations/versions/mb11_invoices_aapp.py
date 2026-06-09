"""mb11_invoices_aapp

SAN-C MB-11.3 · Tabla invoices_aapp para Facturae 3.2.x + DIR3 + Ley 3/2004.

Revision ID: mb11_invaapp
Revises: mb11_aepd
Create Date: 2026-05-05 (SAN-C MB-11.3)
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "mb11_invaapp"
down_revision: Union[str, None] = "mb11_aepd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "invoices_aapp",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            primary_key=True, server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "project_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id"), nullable=False,
        ),
        sa.Column("invoice_number", sa.String(50), nullable=False),
        sa.Column("amount_eur", sa.Numeric(12, 2), nullable=False),
        sa.Column("dir3_oficina_contable", sa.String(20), nullable=False),
        sa.Column("dir3_organo_gestor", sa.String(20), nullable=False),
        sa.Column("dir3_unidad_tramitadora", sa.String(20), nullable=False),
        sa.Column("facturae_xml", sa.Text(), nullable=True),
        sa.Column("facturae_xml_signed", sa.Text(), nullable=True),
        sa.Column("submitted_to_face_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("face_reference", sa.String(100), nullable=True),
        sa.Column("payment_due_date", sa.Date(), nullable=True),
        sa.Column("paid_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("interest_owed_eur", sa.Numeric(12, 2), nullable=True),
        sa.Column(
            "status", sa.String(20),
            server_default=sa.text("'draft'"), nullable=False,
        ),
    )
    op.create_index(
        "ix_invoices_aapp_project_id", "invoices_aapp", ["project_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_invoices_aapp_project_id", table_name="invoices_aapp")
    op.drop_table("invoices_aapp")
