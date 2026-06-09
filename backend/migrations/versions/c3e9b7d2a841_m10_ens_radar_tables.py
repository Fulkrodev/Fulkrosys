"""M10 ENS Radar — 8 tablas para el radar de licitaciones ENS.

Tablas creadas:
- tenders              licitaciones extraídas de PLACSP y portales CCAA
- ens_analysis         resultado de detección ENS por pliego
- companies            empresas detectadas (licitadoras / adjudicatarias)
- participations       relación empresa ↔ licitación
- radar_leads          leads del radar (renombrado para no colisionar con
                       ``leads`` de M13 Commercial)
- ccn_certificados     registro oficial de certificaciones ENS del CCN
- empresas_descartadas trazabilidad de filtros ICP
- sources_runs         auditoría de cada ejecución del pipeline

Los modelos viven en ``backend/app/motors/m10_ens_radar/db/models.py``.

Revision ID: c3e9b7d2a841
Revises: a7f1e4b8c2d5
Create Date: 2026-04-20 12:10:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c3e9b7d2a841"
down_revision: Union[str, None] = "a7f1e4b8c2d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tenders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("external_id", sa.String(length=200), nullable=False),
        sa.Column("expediente", sa.String(length=200), nullable=False),
        sa.Column("organismo", sa.String(length=500), nullable=False),
        sa.Column("titulo", sa.Text(), nullable=False),
        sa.Column("objeto", sa.Text(), nullable=True),
        sa.Column("importe", sa.Float(), nullable=True),
        sa.Column("cpv", sa.String(length=50), nullable=True),
        sa.Column("fecha_publicacion", sa.DateTime(), nullable=False),
        sa.Column("fecha_fin_presentacion", sa.DateTime(), nullable=True),
        sa.Column("fecha_adjudicacion", sa.DateTime(), nullable=True),
        sa.Column("fecha_formalizacion", sa.DateTime(), nullable=True),
        sa.Column("url_pliego", sa.String(length=1000), nullable=True),
        sa.Column("url_expediente", sa.String(length=1000), nullable=True),
        sa.Column("estado", sa.String(length=50), nullable=False),
        sa.Column("raw_data", postgresql.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("external_id", name="uq_tenders_external_id"),
    )
    op.create_index("ix_tenders_source", "tenders", ["source"])
    op.create_index("ix_tenders_fecha_publicacion", "tenders", ["fecha_publicacion"])
    op.create_index("ix_tenders_estado", "tenders", ["estado"])

    op.create_table(
        "ens_analysis",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tender_id",
            sa.Integer(),
            sa.ForeignKey("tenders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("exige_ens", sa.Boolean(), nullable=False),
        sa.Column("nivel", sa.String(length=20), nullable=True),
        sa.Column("tipo_requisito", sa.String(length=50), nullable=True),
        sa.Column("cita_textual", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("model_used", sa.String(length=50), nullable=False),
        sa.Column(
            "analyzed_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("tender_id", name="uq_ens_analysis_tender_id"),
    )

    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cif", sa.String(length=20), nullable=False),
        sa.Column("razon_social", sa.String(length=500), nullable=False),
        sa.Column("nombre_normalizado", sa.String(length=500), nullable=True),
        sa.Column("nombre_comercial", sa.String(length=500), nullable=True),
        sa.Column("domicilio", sa.String(length=500), nullable=True),
        sa.Column("provincia", sa.String(length=100), nullable=True),
        sa.Column("cnae", sa.String(length=20), nullable=True),
        sa.Column("sector", sa.String(length=200), nullable=True),
        sa.Column("empleados", sa.Integer(), nullable=True),
        sa.Column("facturacion", sa.Float(), nullable=True),
        sa.Column("anno_fundacion", sa.Integer(), nullable=True),
        sa.Column("website", sa.String(length=500), nullable=True),
        sa.Column("tiene_ens_vigente", sa.Boolean(), nullable=True),
        sa.Column("nivel_ens_certificado", sa.String(length=20), nullable=True),
        sa.Column("fecha_certificacion_ens", sa.DateTime(), nullable=True),
        sa.Column("fecha_caducidad_ens", sa.DateTime(), nullable=True),
        sa.Column("enriched_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("cif", name="uq_companies_cif"),
    )
    op.create_index("ix_companies_nombre_normalizado", "companies", ["nombre_normalizado"])
    op.create_index("ix_companies_provincia", "companies", ["provincia"])
    op.create_index("ix_companies_cnae", "companies", ["cnae"])

    op.create_table(
        "participations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tender_id",
            sa.Integer(),
            sa.ForeignKey("tenders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "company_id",
            sa.Integer(),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("rol", sa.String(length=50), nullable=False),
        sa.Column("importe_ofertado", sa.Float(), nullable=True),
        sa.Column("fecha", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("tender_id", "company_id", "rol", name="uq_participation"),
    )
    op.create_index("ix_participations_company_id", "participations", ["company_id"])

    op.create_table(
        "radar_leads",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "company_id",
            sa.Integer(),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("temperatura", sa.String(length=20), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("icp_fit", sa.Boolean(), nullable=False),
        sa.Column(
            "icp_passed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("icp_reason", sa.Text(), nullable=True),
        sa.Column(
            "ccn_checked",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "num_licitaciones_ens",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "num_adjudicaciones_ens",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("urgencia_dias", sa.Integer(), nullable=True),
        sa.Column("dolor_especifico", sa.Text(), nullable=True),
        sa.Column("persona_contacto_sugerida", sa.String(length=200), nullable=True),
        sa.Column("canal_sugerido", sa.String(length=50), nullable=True),
        sa.Column("mensaje_primer_contacto", sa.Text(), nullable=True),
        sa.Column("taller_recomendado", sa.String(length=20), nullable=True),
        sa.Column("taller_pitch", sa.Text(), nullable=True),
        sa.Column("dossier_completo", sa.Text(), nullable=True),
        sa.Column("llm_model_used", sa.String(length=50), nullable=True),
        sa.Column(
            "confianza_lead",
            sa.Float(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "estado",
            sa.String(length=50),
            nullable=False,
            server_default="nuevo",
        ),
        sa.Column("notas_marcos", sa.Text(), nullable=True),
        sa.Column(
            "scored_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("company_id", name="uq_radar_leads_company_id"),
    )
    op.create_index("ix_radar_leads_temperatura", "radar_leads", ["temperatura"])
    op.create_index("ix_radar_leads_score", "radar_leads", ["score"])
    op.create_index("ix_radar_leads_ccn_checked", "radar_leads", ["ccn_checked"])

    op.create_table(
        "ccn_certificados",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cif", sa.String(length=20), nullable=True),
        sa.Column("razon_social", sa.String(length=500), nullable=False),
        sa.Column("nombre_normalizado", sa.String(length=500), nullable=False),
        sa.Column("nivel", sa.String(length=20), nullable=False),
        sa.Column("fecha_certificacion", sa.DateTime(), nullable=True),
        sa.Column("fecha_vencimiento", sa.DateTime(), nullable=True),
        sa.Column("entidad_certificadora", sa.String(length=200), nullable=True),
        sa.Column(
            "vigente",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("snapshot_fecha", sa.DateTime(), nullable=False),
        sa.Column("raw_data", postgresql.JSON(), nullable=True),
    )
    op.create_index("idx_ccn_cif", "ccn_certificados", ["cif"])
    op.create_index("idx_ccn_nombre_norm", "ccn_certificados", ["nombre_normalizado"])
    op.create_index("idx_ccn_snapshot", "ccn_certificados", ["snapshot_fecha"])

    op.create_table(
        "empresas_descartadas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "company_id",
            sa.Integer(),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("motivo", sa.String(length=50), nullable=False),
        sa.Column("capa", sa.String(length=30), nullable=False),
        sa.Column("raw_match", sa.Text(), nullable=True),
        sa.Column(
            "descartada_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("idx_descarte_motivo", "empresas_descartadas", ["motivo"])

    op.create_table(
        "sources_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.String(length=50), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "tenders_ingested",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "tenders_with_ens",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("rango_desde", sa.DateTime(), nullable=True),
        sa.Column("rango_hasta", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_sources_runs_source_id", "sources_runs", ["source_id"])
    op.create_index("ix_sources_runs_started_at", "sources_runs", ["started_at"])


def downgrade() -> None:
    op.drop_index("ix_sources_runs_started_at", "sources_runs")
    op.drop_index("ix_sources_runs_source_id", "sources_runs")
    op.drop_table("sources_runs")

    op.drop_index("idx_descarte_motivo", "empresas_descartadas")
    op.drop_table("empresas_descartadas")

    op.drop_index("idx_ccn_snapshot", "ccn_certificados")
    op.drop_index("idx_ccn_nombre_norm", "ccn_certificados")
    op.drop_index("idx_ccn_cif", "ccn_certificados")
    op.drop_table("ccn_certificados")

    op.drop_index("ix_radar_leads_ccn_checked", "radar_leads")
    op.drop_index("ix_radar_leads_score", "radar_leads")
    op.drop_index("ix_radar_leads_temperatura", "radar_leads")
    op.drop_table("radar_leads")

    op.drop_index("ix_participations_company_id", "participations")
    op.drop_table("participations")

    op.drop_index("ix_companies_cnae", "companies")
    op.drop_index("ix_companies_provincia", "companies")
    op.drop_index("ix_companies_nombre_normalizado", "companies")
    op.drop_table("companies")

    op.drop_table("ens_analysis")

    op.drop_index("ix_tenders_estado", "tenders")
    op.drop_index("ix_tenders_fecha_publicacion", "tenders")
    op.drop_index("ix_tenders_source", "tenders")
    op.drop_table("tenders")
