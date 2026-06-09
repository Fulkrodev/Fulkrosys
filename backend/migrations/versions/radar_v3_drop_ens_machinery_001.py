"""Radar v3 FASE 2: drop maquinaria de detección ENS sobre pliegos.

Elimina tablas y columnas asociadas al enfoque viejo (detección de qué pliego
exige ENS + scoring/detector pliego defectuoso), sustituido por el enfoque
profile-based v3. Reversible (down recrea estructura, NO datos).

NO toca: ccn_certificados, placsp_adjudicaciones, participations, companies,
radar_leads (salvo la columna angulo_comercial), tenders (salvo columnas de
detección ENS).

Revision ID: radar_v3_drop_ens_machinery_001
Revises: radar_v3_placsp_adjud_001
"""
from alembic import op
import sqlalchemy as sa


revision = "radar_v3_drop_ens_machinery_001"
down_revision = "radar_v3_placsp_adjud_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Columnas detector pliego defectuoso + excerpt (tenders)
    op.drop_column("tenders", "pliego_defectuoso_detected_at")
    op.drop_column("tenders", "pliego_defectuoso_razon")
    op.drop_column("tenders", "pliego_defectuoso_confidence")
    op.drop_column("tenders", "pliego_defectuoso")
    op.drop_column("tenders", "pliego_excerpt")
    # Ángulo comercial TACPC (radar_leads)
    op.drop_column("radar_leads", "angulo_comercial")
    # Tablas de la maquinaria ENS
    op.drop_table("data_treatment_cache")
    op.drop_table("ens_analysis")


def downgrade() -> None:
    # Recrea ens_analysis (estructura, sin datos).
    op.create_table(
        "ens_analysis",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tender_id", sa.Integer(), nullable=False),
        sa.Column("exige_ens", sa.Boolean(), nullable=False),
        sa.Column("nivel", sa.String(length=20), nullable=True),
        sa.Column("tipo_requisito", sa.String(length=50), nullable=True),
        sa.Column("cita_textual", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("model_used", sa.String(length=50), nullable=False),
        sa.Column("analyzed_at", sa.DateTime(), nullable=True),
        sa.Column("plazo_cee_meses", sa.Integer(), nullable=True),
        sa.Column(
            "es_compromiso_futuro", sa.Boolean(), nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "nivel_inferido", sa.Boolean(), nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("detection_source", sa.String(length=40), nullable=True),
        sa.ForeignKeyConstraint(
            ["tender_id"], ["tenders.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint("tender_id"),
    )
    # Recrea data_treatment_cache (estructura, sin datos).
    op.create_table(
        "data_treatment_cache",
        sa.Column("objeto_hash", sa.String(length=64), primary_key=True),
        sa.Column("data_treatment", sa.String(length=10), nullable=False),
        sa.Column("sector_sugerido", sa.Text(), nullable=True),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column("model", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    # Re-añade columnas a radar_leads + tenders.
    op.add_column(
        "radar_leads",
        sa.Column("angulo_comercial", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "tenders", sa.Column("pliego_excerpt", sa.Text(), nullable=True)
    )
    op.add_column(
        "tenders",
        sa.Column(
            "pliego_defectuoso", sa.Boolean(), nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "tenders",
        sa.Column(
            "pliego_defectuoso_confidence", sa.Numeric(3, 2), nullable=True
        ),
    )
    op.add_column(
        "tenders",
        sa.Column("pliego_defectuoso_razon", sa.Text(), nullable=True),
    )
    op.add_column(
        "tenders",
        sa.Column(
            "pliego_defectuoso_detected_at",
            sa.DateTime(timezone=True), nullable=True,
        ),
    )
