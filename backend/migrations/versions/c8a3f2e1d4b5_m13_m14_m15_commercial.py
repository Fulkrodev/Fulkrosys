"""M13+M14+M15 Commercial / Contracts / Billing.

- Add project_id FK to proposals + contracts
- Add pricing_model_id, notas_marcos to proposals
- Add firmado_cliente_link_id to contracts; change plantilla_id to String
- Add verifactu_enviado_at to invoices; widen numero_correlativo to 30 chars
- Create pricing_models, invoice_lines, client_commitments, payment_reminders
- RLS: proposals/contracts (project_id), client_commitments (project_id),
  invoice_lines (client_id via join), payment_reminders (client_id via join)

Revision ID: c8a3f2e1d4b5
Revises: 36ea04ed33d0
Create Date: 2026-04-17 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c8a3f2e1d4b5"
down_revision: Union[str, None] = "36ea04ed33d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---- proposals: add project_id, pricing_model_id, notas_marcos ----
    op.add_column(
        "proposals",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_proposals_project_id", "proposals", "projects",
        ["project_id"], ["id"],
    )
    op.add_column("proposals", sa.Column("pricing_model_id", sa.String(length=50), nullable=True))
    op.add_column("proposals", sa.Column("notas_marcos", sa.Text(), nullable=True))

    # ---- contracts: add project_id, firmado_cliente_link_id ----
    op.add_column(
        "contracts",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_contracts_project_id", "contracts", "projects",
        ["project_id"], ["id"],
    )
    op.add_column(
        "contracts",
        sa.Column("firmado_cliente_link_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    # plantilla_id: in model, switch from UUID to String(20) (C-001..C-005).
    # Existing column is UUID — drop and recreate as String to match new type.
    op.drop_column("contracts", "plantilla_id")
    op.add_column("contracts", sa.Column("plantilla_id", sa.String(length=20), nullable=True))

    # ---- invoices: add verifactu_enviado_at, widen numero_correlativo ----
    op.add_column(
        "invoices",
        sa.Column("verifactu_enviado_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
    )
    op.alter_column(
        "invoices", "numero_correlativo",
        type_=sa.String(length=30), existing_type=sa.String(length=20), existing_nullable=True,
    )

    # ---- pricing_models ----
    op.create_table(
        "pricing_models",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("codigo", sa.String(length=50), nullable=False, unique=True),
        sa.Column("nombre", sa.String(length=255), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("aplicable_categoria", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("formula", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("rango_precio_min", sa.Numeric(12, 2), nullable=True),
        sa.Column("rango_precio_max", sa.Numeric(12, 2), nullable=True),
        sa.Column("hitos_pago", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )

    # ---- invoice_lines ----
    op.create_table(
        "invoice_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("invoices.id"), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("cantidad", sa.Numeric(10, 2), nullable=False, server_default=sa.text("1")),
        sa.Column("precio_unitario", sa.Numeric(12, 2), nullable=False),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("hito_asociado", sa.String(length=100), nullable=True),
        sa.Column("paron_asociado", sa.String(length=100), nullable=True),
        sa.Column("orden", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.create_index("ix_invoice_lines_invoice_id", "invoice_lines", ["invoice_id"])

    # ---- client_commitments ----
    op.create_table(
        "client_commitments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contracts.id"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("tipo", sa.String(length=100), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("parametro", sa.String(length=100), nullable=True),
        sa.Column("valor_esperado", sa.String(length=255), nullable=True),
        sa.Column("valor_actual", sa.String(length=255), nullable=True),
        sa.Column("cumplido", sa.Boolean(), nullable=True),
        sa.Column("ultima_verificacion_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index("ix_client_commitments_contract_id", "client_commitments", ["contract_id"])

    # ---- payment_reminders ----
    op.create_table(
        "payment_reminders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("invoices.id"), nullable=False),
        sa.Column("dias_vencida", sa.Integer(), nullable=False),
        sa.Column("template_usado", sa.String(length=100), nullable=True),
        sa.Column("enviado_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("canal", sa.String(length=50), nullable=True),
        sa.Column("contenido", sa.Text(), nullable=True),
    )
    op.create_index("ix_payment_reminders_invoice_id", "payment_reminders", ["invoice_id"])

    # ---- RLS policies ----
    # proposals / contracts / client_commitments: project_id with NULL allowed
    for table in ("proposals", "contracts", "client_commitments"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY project_isolation ON {table} "
            f"USING (project_id = current_project_id() OR project_id IS NULL)"
        )

    # invoice_lines / payment_reminders: inherit client_id via invoices
    # Simple policy — allow if parent invoice is visible under current RLS
    op.execute("ALTER TABLE invoice_lines ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE invoice_lines FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY client_isolation ON invoice_lines USING ("
        "EXISTS (SELECT 1 FROM invoices i WHERE i.id = invoice_lines.invoice_id "
        "AND i.client_id = current_client_id()))"
    )

    op.execute("ALTER TABLE payment_reminders ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE payment_reminders FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY client_isolation ON payment_reminders USING ("
        "EXISTS (SELECT 1 FROM invoices i WHERE i.id = payment_reminders.invoice_id "
        "AND i.client_id = current_client_id()))"
    )


def downgrade() -> None:
    for table in ("payment_reminders", "invoice_lines", "client_commitments", "contracts", "proposals"):
        op.execute(f"DROP POLICY IF EXISTS project_isolation ON {table}")
        op.execute(f"DROP POLICY IF EXISTS client_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    op.drop_index("ix_payment_reminders_invoice_id", table_name="payment_reminders")
    op.drop_table("payment_reminders")
    op.drop_index("ix_client_commitments_contract_id", table_name="client_commitments")
    op.drop_table("client_commitments")
    op.drop_index("ix_invoice_lines_invoice_id", table_name="invoice_lines")
    op.drop_table("invoice_lines")
    op.drop_table("pricing_models")

    op.alter_column(
        "invoices", "numero_correlativo",
        type_=sa.String(length=20), existing_type=sa.String(length=30), existing_nullable=True,
    )
    op.drop_column("invoices", "verifactu_enviado_at")

    op.drop_column("contracts", "plantilla_id")
    op.add_column("contracts", sa.Column("plantilla_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.drop_column("contracts", "firmado_cliente_link_id")
    op.drop_constraint("fk_contracts_project_id", "contracts", type_="foreignkey")
    op.drop_column("contracts", "project_id")

    op.drop_column("proposals", "notas_marcos")
    op.drop_column("proposals", "pricing_model_id")
    op.drop_constraint("fk_proposals_project_id", "proposals", type_="foreignkey")
    op.drop_column("proposals", "project_id")
