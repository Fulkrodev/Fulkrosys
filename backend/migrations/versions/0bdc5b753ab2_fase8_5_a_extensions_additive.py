"""FASE 8.5 C2 (8.5.A) — extensiones additive ENSAnalysis + RadarLead + PipelineRun.

Adopcion blueprint ENS Radar Portal vía Opcion D híbrido (ADR-027):
NO se rompen schemas Sesion C1, se extienden con campos workflow comercial v2.

ENSAnalysis (+3): plazo_cee_meses, es_compromiso_futuro, nivel_inferido
RadarLead (+9): cluster_id, plazo_cee_meses_pliego, dias_hasta_vencimiento_cee,
                fecha_fin_oferta_proxima, es_lead_excluido_ens, contactable,
                estado_contacto (CHECK 8 estados), notas_privadas, email_redactado
PipelineRun (+11): tenders_ingested, tenders_with_ens, leads_created,
                   leads_updated, current_step_progress_pct,
                   current_step_message, summary_json, triggered_by,
                   triggered_via, since_date, until_date

Revision ID: 0bdc5b753ab2
Revises: cb9c8416b68a
Create Date: 2026-04-30 16:04:24.272459
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0bdc5b753ab2"
down_revision: Union[str, None] = "cb9c8416b68a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── ENSAnalysis +3 cols ──────────────────────────────────────────
    op.add_column(
        "ens_analysis",
        sa.Column("plazo_cee_meses", sa.Integer(), nullable=True),
    )
    op.add_column(
        "ens_analysis",
        sa.Column(
            "es_compromiso_futuro",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "ens_analysis",
        sa.Column(
            "nivel_inferido",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # ── RadarLead +9 cols + CHECK constraint + 2 indexes ─────────────
    op.add_column(
        "radar_leads",
        sa.Column("cluster_id", sa.String(length=100), nullable=True),
    )
    op.create_index(
        "ix_radar_leads_cluster_id", "radar_leads", ["cluster_id"]
    )
    op.add_column(
        "radar_leads",
        sa.Column("plazo_cee_meses_pliego", sa.Integer(), nullable=True),
    )
    op.add_column(
        "radar_leads",
        sa.Column(
            "dias_hasta_vencimiento_cee", sa.Integer(), nullable=True
        ),
    )
    op.create_index(
        "ix_radar_leads_dias_hasta_vencimiento_cee",
        "radar_leads",
        ["dias_hasta_vencimiento_cee"],
    )
    op.add_column(
        "radar_leads",
        sa.Column(
            "fecha_fin_oferta_proxima",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "radar_leads",
        sa.Column(
            "es_lead_excluido_ens",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "radar_leads",
        sa.Column(
            "contactable",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.add_column(
        "radar_leads",
        sa.Column(
            "estado_contacto",
            sa.String(length=30),
            nullable=False,
            server_default="nuevo",
        ),
    )
    op.add_column(
        "radar_leads",
        sa.Column("notas_privadas", sa.Text(), nullable=True),
    )
    op.add_column(
        "radar_leads",
        sa.Column("email_redactado", sa.Text(), nullable=True),
    )
    op.create_check_constraint(
        "radar_leads_estado_contacto_check",
        "radar_leads",
        (
            "estado_contacto IN ('nuevo', 'enviado', 'respondio', "
            "'reunion_agendada', 'propuesta_enviada', 'ganado', "
            "'descartado', 'no_interesa')"
        ),
    )

    # ── PipelineRun +11 cols ─────────────────────────────────────────
    op.add_column(
        "radar_pipeline_runs",
        sa.Column(
            "tenders_ingested",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "radar_pipeline_runs",
        sa.Column(
            "tenders_with_ens",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "radar_pipeline_runs",
        sa.Column(
            "leads_created",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "radar_pipeline_runs",
        sa.Column(
            "leads_updated",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "radar_pipeline_runs",
        sa.Column(
            "current_step_progress_pct",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "radar_pipeline_runs",
        sa.Column(
            "current_step_message",
            sa.String(length=500),
            nullable=True,
        ),
    )
    op.add_column(
        "radar_pipeline_runs",
        sa.Column(
            "summary_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "radar_pipeline_runs",
        sa.Column(
            "triggered_by",
            sa.String(length=100),
            nullable=False,
            server_default="marcos",
        ),
    )
    op.add_column(
        "radar_pipeline_runs",
        sa.Column(
            "triggered_via",
            sa.String(length=20),
            nullable=False,
            server_default="api",
        ),
    )
    op.add_column(
        "radar_pipeline_runs",
        sa.Column(
            "since_date", sa.DateTime(timezone=True), nullable=True
        ),
    )
    op.add_column(
        "radar_pipeline_runs",
        sa.Column(
            "until_date", sa.DateTime(timezone=True), nullable=True
        ),
    )


def downgrade() -> None:
    # PipelineRun rollback
    op.drop_column("radar_pipeline_runs", "until_date")
    op.drop_column("radar_pipeline_runs", "since_date")
    op.drop_column("radar_pipeline_runs", "triggered_via")
    op.drop_column("radar_pipeline_runs", "triggered_by")
    op.drop_column("radar_pipeline_runs", "summary_json")
    op.drop_column("radar_pipeline_runs", "current_step_message")
    op.drop_column("radar_pipeline_runs", "current_step_progress_pct")
    op.drop_column("radar_pipeline_runs", "leads_updated")
    op.drop_column("radar_pipeline_runs", "leads_created")
    op.drop_column("radar_pipeline_runs", "tenders_with_ens")
    op.drop_column("radar_pipeline_runs", "tenders_ingested")

    # RadarLead rollback
    op.drop_constraint(
        "radar_leads_estado_contacto_check",
        "radar_leads",
        type_="check",
    )
    op.drop_column("radar_leads", "email_redactado")
    op.drop_column("radar_leads", "notas_privadas")
    op.drop_column("radar_leads", "estado_contacto")
    op.drop_column("radar_leads", "contactable")
    op.drop_column("radar_leads", "es_lead_excluido_ens")
    op.drop_column("radar_leads", "fecha_fin_oferta_proxima")
    op.drop_index(
        "ix_radar_leads_dias_hasta_vencimiento_cee", "radar_leads"
    )
    op.drop_column("radar_leads", "dias_hasta_vencimiento_cee")
    op.drop_column("radar_leads", "plazo_cee_meses_pliego")
    op.drop_index("ix_radar_leads_cluster_id", "radar_leads")
    op.drop_column("radar_leads", "cluster_id")

    # ENSAnalysis rollback
    op.drop_column("ens_analysis", "nivel_inferido")
    op.drop_column("ens_analysis", "es_compromiso_futuro")
    op.drop_column("ens_analysis", "plazo_cee_meses")
