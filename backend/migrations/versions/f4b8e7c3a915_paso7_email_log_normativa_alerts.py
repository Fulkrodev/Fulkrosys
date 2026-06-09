"""Paso 7 — email_log + normativa_alerts.

Anade infra para operacion diaria:
- email_log: log completo de emails enviados via EmailSender (todos los
  backends convergen aqui para trazabilidad).
- normativa_alerts: alertas de Agente 15 Vigilancia Normativa con
  severity + affected_measures + affected_clients.

Revision ID: f4b8e7c3a915
Revises: e3f7a5b2d412
Create Date: 2026-04-22 17:30:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "f4b8e7c3a915"
down_revision = "e3f7a5b2d412"
branch_labels = None
depends_on = None


NORMATIVA_SOURCES = ("ccn_cert", "boe", "ccn_stic", "aepd", "enisa", "other")
NORMATIVA_SEVERITIES = ("low", "medium", "high", "critical")
NORMATIVA_STATUSES = ("detected", "classified", "notified", "archived")

EMAIL_BACKENDS = ("smtp", "postmark_api", "mock")
EMAIL_STATUSES = (
    "queued", "sent", "delivered", "bounced", "failed", "suppressed",
)


def upgrade() -> None:
    # ── email_log ────────────────────────────────────────────────────
    op.create_table(
        "email_log",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("recipient", sa.String(255), nullable=False, index=True),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("template_used", sa.String(120), nullable=True, index=True),
        sa.Column("body_html", sa.Text(), nullable=True),
        sa.Column("body_text", sa.Text(), nullable=True),
        sa.Column("backend_used", sa.String(30), nullable=False),
        sa.Column(
            "queued_at", sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.Column("sent_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "delivery_status", sa.String(30), nullable=False,
            server_default="queued",
        ),
        sa.Column("message_id", sa.String(255), nullable=True),
        sa.Column(
            "retry_count", sa.Integer(), nullable=False,
            server_default="0",
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "magic_link_id", postgresql.UUID(as_uuid=True),
            nullable=True, index=True,
        ),
        sa.Column(
            "client_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clients.id", ondelete="SET NULL"),
            nullable=True, index=True,
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
            "backend_used IN ("
            + ", ".join(f"'{b}'" for b in EMAIL_BACKENDS)
            + ")",
            name="ck_email_log_backend_used",
        ),
        sa.CheckConstraint(
            "delivery_status IN ("
            + ", ".join(f"'{s}'" for s in EMAIL_STATUSES)
            + ")",
            name="ck_email_log_delivery_status",
        ),
    )

    # ── normativa_alerts ─────────────────────────────────────────────
    op.create_table(
        "normativa_alerts",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("source", sa.String(30), nullable=False, index=True),
        sa.Column("source_url", sa.String(1000), nullable=True),
        sa.Column(
            "source_item_id", sa.String(500), nullable=True,
            doc="ID unico del item en el feed (guid, URL, etc.) "
                "para deteccion de duplicados",
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "published_at", sa.TIMESTAMP(timezone=True), nullable=True,
        ),
        sa.Column(
            "detected_at", sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.Column("severity", sa.String(20), nullable=False, index=True),
        sa.Column(
            "affected_measures_jsonb",
            postgresql.JSONB(astext_type=sa.Text()), nullable=True,
        ),
        sa.Column(
            "affected_clients_jsonb",
            postgresql.JSONB(astext_type=sa.Text()), nullable=True,
        ),
        sa.Column("summary_llm", sa.Text(), nullable=True),
        sa.Column(
            "classified_at", sa.TIMESTAMP(timezone=True), nullable=True,
        ),
        sa.Column(
            "notification_sent_at", sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "status", sa.String(30), nullable=False,
            server_default="detected", index=True,
        ),
        sa.Column(
            "metadata_jsonb",
            postgresql.JSONB(astext_type=sa.Text()), nullable=True,
        ),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.CheckConstraint(
            "source IN ("
            + ", ".join(f"'{s}'" for s in NORMATIVA_SOURCES)
            + ")",
            name="ck_normativa_alerts_source",
        ),
        sa.CheckConstraint(
            "severity IN ("
            + ", ".join(f"'{s}'" for s in NORMATIVA_SEVERITIES)
            + ")",
            name="ck_normativa_alerts_severity",
        ),
        sa.CheckConstraint(
            "status IN ("
            + ", ".join(f"'{s}'" for s in NORMATIVA_STATUSES)
            + ")",
            name="ck_normativa_alerts_status",
        ),
    )
    # Unique source + source_item_id para evitar duplicados
    op.create_unique_constraint(
        "uq_normativa_alerts_source_item",
        "normativa_alerts", ["source", "source_item_id"],
    )

    # email_log no lleva RLS — globalmente operado por Marcos + Celery.
    # normativa_alerts tampoco — son alerts globales, el filtrado por
    # cliente se hace en application-layer via affected_clients_jsonb.


def downgrade() -> None:
    op.drop_constraint(
        "uq_normativa_alerts_source_item",
        "normativa_alerts", type_="unique",
    )
    op.drop_table("normativa_alerts")
    op.drop_table("email_log")
