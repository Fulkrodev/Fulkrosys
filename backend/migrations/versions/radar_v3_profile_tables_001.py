"""Radar v3 FASE 3: tablas profile-based (cnae6203_raw, empresa_6203) + vista leads_v3.

Esqueleto del enfoque profile-based: directorio CNAE 6203 (raw) + empresa
cualificada con estado de lead precomputado (Pasos 2-4) + vista leads_v3 que
materializa la query del lead v3 (6203 ∩ activa ∩ PYME ∩ concursó ∩ sin ENS).

Reversible. NO toca ccn_certificados ni placsp_adjudicaciones.

Revision ID: radar_v3_profile_tables_001
Revises: radar_v3_drop_ens_machinery_001
"""
from alembic import op
import sqlalchemy as sa


revision = "radar_v3_profile_tables_001"
down_revision = "radar_v3_drop_ens_machinery_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cnae6203_raw",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("razon_social", sa.String(length=500), nullable=False),
        sa.Column("localidad", sa.String(length=200), nullable=True),
        sa.Column("provincia", sa.String(length=100), nullable=True),
        sa.Column("ficha_url", sa.String(length=1000), nullable=True),
        sa.Column(
            "scraped_at", sa.DateTime(), nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "empresa_6203",
        sa.Column("cif_norm", sa.String(length=20), primary_key=True),
        sa.Column("razon_social", sa.String(length=500), nullable=True),
        sa.Column("cnae", sa.String(length=20), nullable=True),
        sa.Column("cnae_desc", sa.Text(), nullable=True),
        sa.Column("tramo_empleados", sa.String(length=50), nullable=True),
        sa.Column("tramo_ventas", sa.String(length=50), nullable=True),
        sa.Column("estado", sa.String(length=50), nullable=True),
        sa.Column("web", sa.String(length=500), nullable=True),
        sa.Column("es_sig", sa.Boolean(), nullable=True),
        sa.Column(
            "es_candidato", sa.Boolean(), nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "requiere_verificacion", sa.Boolean(), nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("fuente", sa.String(length=50), nullable=True),
        sa.Column("enriquecido_at", sa.DateTime(), nullable=True),
        sa.Column(
            "ha_concursado", sa.Boolean(), nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "n_expedientes", sa.Integer(), nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("ultima_fecha", sa.DateTime(), nullable=True),
        sa.Column("ultimo_organismo", sa.String(length=500), nullable=True),
        sa.Column("ens_estado", sa.String(length=30), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_empresa_6203_candidato", "empresa_6203", ["es_candidato"])
    op.create_index("ix_empresa_6203_ens_estado", "empresa_6203", ["ens_estado"])

    # Vista leads_v3: 6203 ∩ activa ∩ PYME ∩ concursó ∩ sin ENS (o recert).
    op.execute(
        """
        CREATE VIEW leads_v3 AS
        SELECT
            cif_norm, razon_social, cnae, cnae_desc, tramo_empleados,
            tramo_ventas, estado, web, requiere_verificacion,
            ha_concursado, n_expedientes, ultima_fecha, ultimo_organismo,
            ens_estado,
            CASE WHEN ens_estado = 'lead_recert' THEN 'recert' ELSE 'lead' END
                AS tipo_lead
        FROM empresa_6203
        WHERE es_candidato IS TRUE
          AND estado = 'activa'
          AND tramo_empleados IN ('1-9', '10-49', '50-99')
          AND ha_concursado IS TRUE
          AND ens_estado IN ('lead', 'lead_recert')
        """
    )

    # GRANTs al rol runtime (mirror del resto de tablas radar).
    op.execute(
        """
        DO $$ BEGIN
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'fulkro_app') THEN
            GRANT INSERT, SELECT, UPDATE, DELETE
              ON cnae6203_raw, empresa_6203 TO fulkro_app;
            GRANT USAGE, SELECT ON SEQUENCE cnae6203_raw_id_seq TO fulkro_app;
            GRANT SELECT ON leads_v3 TO fulkro_app;
          END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS leads_v3")
    op.drop_index("ix_empresa_6203_ens_estado", table_name="empresa_6203")
    op.drop_index("ix_empresa_6203_candidato", table_name="empresa_6203")
    op.drop_table("empresa_6203")
    op.drop_table("cnae6203_raw")
