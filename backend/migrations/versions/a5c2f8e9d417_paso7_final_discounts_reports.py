"""Paso 7 final — commercial_discounts + retainer_reports.

Anade infra para Parte 1 del Paso 7 final:
- commercial_discounts: quick scan -> C-001 descuento auto + manual
- retainer_reports: log de E-801 trimestrales + E-802 anuales

Revision ID: a5c2f8e9d417
Revises: f4b8e7c3a915
Create Date: 2026-04-22 18:30:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "a5c2f8e9d417"
down_revision = "f4b8e7c3a915"
branch_labels = None
depends_on = None


DISCOUNT_TYPES = (
    "quick_scan_to_implantacion",
    "referral_bonus",
    "campaign_special",
    "loyalty_retainer",
)
DISCOUNT_APPLICABLE = (
    "c001_implantacion",
    "c003_retainer",
    "any_implantacion",
    "any",
)
DISCOUNT_STATUSES = ("available", "used", "expired", "revoked")

REPORT_TYPES = ("E-801_quarterly", "E-802_annual")
REPORT_STATUSES = ("generated", "sent", "acknowledged", "failed")


def upgrade() -> None:
    # ── commercial_discounts ─────────────────────────────────────────
    op.create_table(
        "commercial_discounts",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "client_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clients.id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column("discount_type", sa.String(40), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("amount_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("applicable_to", sa.String(40), nullable=False),
        sa.Column(
            "granted_at", sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.Column("granted_by", sa.String(50), nullable=True),
        sa.Column("granted_reason", sa.Text(), nullable=True),
        sa.Column("used_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "used_in_contract_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("contracts.id", ondelete="SET NULL"),
            nullable=True, index=True,
        ),
        sa.Column(
            "expires_at", sa.TIMESTAMP(timezone=True), nullable=True, index=True,
        ),
        sa.Column(
            "status", sa.String(20), nullable=False,
            server_default="available",
        ),
        sa.Column(
            "source_invoice_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("invoices.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "metadata_jsonb", postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.CheckConstraint(
            "discount_type IN ("
            + ", ".join(f"'{t}'" for t in DISCOUNT_TYPES) + ")",
            name="ck_commercial_discounts_type",
        ),
        sa.CheckConstraint(
            "applicable_to IN ("
            + ", ".join(f"'{a}'" for a in DISCOUNT_APPLICABLE) + ")",
            name="ck_commercial_discounts_applicable",
        ),
        sa.CheckConstraint(
            "status IN ("
            + ", ".join(f"'{s}'" for s in DISCOUNT_STATUSES) + ")",
            name="ck_commercial_discounts_status",
        ),
        sa.CheckConstraint(
            "(amount IS NOT NULL) OR (amount_pct IS NOT NULL)",
            name="ck_commercial_discounts_amount_or_pct",
        ),
    )

    # ── retainer_reports ─────────────────────────────────────────────
    op.create_table(
        "retainer_reports",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "client_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clients.id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column(
            "project_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="SET NULL"),
            nullable=True, index=True,
        ),
        sa.Column("report_type", sa.String(30), nullable=False),
        sa.Column("periodo_year", sa.Integer(), nullable=False),
        sa.Column(
            "periodo_quarter", sa.Integer(), nullable=True,
            doc="1-4 si report_type == E-801_quarterly, NULL si anual",
        ),
        sa.Column("periodo_inicio", sa.Date(), nullable=False),
        sa.Column("periodo_fin", sa.Date(), nullable=False),
        sa.Column(
            "kpis_jsonb", postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "payload_jsonb", postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "generated_at", sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.Column("docx_path", sa.String(500), nullable=True),
        sa.Column("pdf_path", sa.String(500), nullable=True),
        sa.Column("signature_ed25519", sa.Text(), nullable=True),
        sa.Column("hash_sha256", sa.String(64), nullable=True),
        sa.Column(
            "sent_at", sa.TIMESTAMP(timezone=True), nullable=True,
        ),
        sa.Column(
            "magic_link_id", postgresql.UUID(as_uuid=True), nullable=True,
        ),
        sa.Column(
            "status", sa.String(20), nullable=False,
            server_default="generated",
        ),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.CheckConstraint(
            "report_type IN ("
            + ", ".join(f"'{t}'" for t in REPORT_TYPES) + ")",
            name="ck_retainer_reports_type",
        ),
        sa.CheckConstraint(
            "status IN ("
            + ", ".join(f"'{s}'" for s in REPORT_STATUSES) + ")",
            name="ck_retainer_reports_status",
        ),
    )
    op.create_unique_constraint(
        "uq_retainer_reports_client_periodo",
        "retainer_reports",
        ["client_id", "report_type", "periodo_year", "periodo_quarter"],
    )

    # Ninguna RLS — operacion central Marcos + Celery.


def downgrade() -> None:
    op.drop_constraint(
        "uq_retainer_reports_client_periodo",
        "retainer_reports", type_="unique",
    )
    op.drop_table("retainer_reports")
    op.drop_table("commercial_discounts")
