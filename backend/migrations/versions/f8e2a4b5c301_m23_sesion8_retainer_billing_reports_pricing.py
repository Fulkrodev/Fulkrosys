"""M23 Sesion 8 — retainer_billing_events + retainer_quarterly_reports + pricing_catalog.

Revision ID: f8e2a4b5c301
Revises: e6f1a4b8c30a
Create Date: 2026-04-22 12:30:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "f8e2a4b5c301"
down_revision = "e6f1a4b8c30a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── retainer_billing_events ──────────────────────────────────────
    op.create_table(
        "retainer_billing_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("retainer_contract_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("retainer_contracts.id"),
                  nullable=False, index=True),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True),
                  nullable=True, index=True),
        sa.Column("billing_period_start", sa.Date(), nullable=False),
        sa.Column("billing_period_end", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", sa.String(20), nullable=False,
                  server_default=sa.text("'emitted'")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("now()"),
                  onupdate=sa.text("now()"), nullable=True),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_retainer_billing_events_contract_period",
        "retainer_billing_events",
        ["retainer_contract_id", "billing_period_start"],
    )

    # ── retainer_quarterly_reports ───────────────────────────────────
    op.create_table(
        "retainer_quarterly_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("retainer_contract_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("retainer_contracts.id"),
                  nullable=False, index=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("projects.id"),
                  nullable=False, index=True),
        sa.Column("period_type", sa.String(20), nullable=False,
                  server_default=sa.text("'trimestral'")),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("activities_completed", sa.Integer(), server_default="0"),
        sa.Column("activities_pending", sa.Integer(), server_default="0"),
        sa.Column("activities_overdue", sa.Integer(), server_default="0"),
        sa.Column("incidents_detected", sa.Integer(), server_default="0"),
        sa.Column("normativa_changes_relevant", sa.Integer(), server_default="0"),
        sa.Column("vulns_critical", sa.Integer(), server_default="0"),
        sa.Column("rag_overall", sa.String(10), nullable=True),
        sa.Column("report_document_id", postgresql.UUID(as_uuid=True),
                  nullable=True, index=True),
        sa.Column("sent_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("sent_to_magic_link_id", postgresql.UUID(as_uuid=True),
                  nullable=True),
        sa.Column("summary_jsonb", postgresql.JSONB(astext_type=sa.Text()),
                  nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("now()"),
                  onupdate=sa.text("now()"), nullable=True),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_retainer_quarterly_reports_contract_period",
        "retainer_quarterly_reports",
        ["retainer_contract_id", "period_start"],
    )

    # ── pricing_catalog ──────────────────────────────────────────────
    op.create_table(
        "pricing_catalog",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("category", sa.String(30), nullable=False, index=True),
        sa.Column("tier_code", sa.String(30), nullable=False, index=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("base_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False,
                  server_default=sa.text("'EUR'")),
        sa.Column("billing_unit", sa.String(20), nullable=False,
                  server_default=sa.text("'mensual'")),
        sa.Column("extras_jsonb", postgresql.JSONB(astext_type=sa.Text()),
                  nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("version", sa.String(20),
                  server_default=sa.text("'2026-04-21'")),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("now()"),
                  onupdate=sa.text("now()"), nullable=True),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index(
        "uq_pricing_catalog_category_tier_active",
        "pricing_catalog",
        ["category", "tier_code", "effective_from"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_pricing_catalog_category_tier_active",
                  table_name="pricing_catalog")
    op.drop_table("pricing_catalog")
    op.drop_index("ix_retainer_quarterly_reports_contract_period",
                  table_name="retainer_quarterly_reports")
    op.drop_table("retainer_quarterly_reports")
    op.drop_index("ix_retainer_billing_events_contract_period",
                  table_name="retainer_billing_events")
    op.drop_table("retainer_billing_events")
