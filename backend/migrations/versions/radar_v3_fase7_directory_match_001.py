"""Radar v3 FASE 7: empresa_6203 importe/probable_grande + leads_v3 sin filtro tamaño.

FASE 7 (vía 100% gratis · datos propios): el universo 6203 viene del directorio
eInforma (solo nombres) y el CIF + historial se recupera por match local contra
placsp_adjudicaciones. NO hay fuente de nº de empleados → ``tramo_empleados``
queda NULL, así que la vista leads_v3 NO puede filtrar por tamaño (excluiría
todo). El tamaño se gestiona con el flag ``probable_grande`` para triaje manual.

up: ALTER empresa_6203 (+importe_total, max_importe_contrato, probable_grande) +
    redefine leads_v3 sin el filtro tramo_empleados IN (...).
down: revierte (vista con filtro tamaño + drop columnas).

Revision ID: radar_v3_fase7_directory_match_001
Revises: radar_v3_profile_tables_001
"""
from alembic import op
import sqlalchemy as sa


revision = "radar_v3_fase7_directory_match_001"
down_revision = "radar_v3_profile_tables_001"
branch_labels = None
depends_on = None


_VIEW_V3_FASE7 = """
CREATE VIEW leads_v3 AS
SELECT
    cif_norm, razon_social, cnae, cnae_desc, tramo_empleados, tramo_ventas,
    estado, web, requiere_verificacion, ha_concursado, n_expedientes,
    ultima_fecha, ultimo_organismo, ens_estado,
    importe_total, max_importe_contrato, probable_grande,
    CASE WHEN ens_estado = 'lead_recert' THEN 'recert' ELSE 'lead' END
        AS tipo_lead
FROM empresa_6203
WHERE es_candidato IS TRUE
  AND estado = 'activa'
  AND ha_concursado IS TRUE
  AND ens_estado IN ('lead', 'lead_recert')
"""

_VIEW_V3_OLD = """
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


def upgrade() -> None:
    op.add_column(
        "empresa_6203",
        sa.Column("importe_total", sa.Numeric(15, 2), nullable=True),
    )
    op.add_column(
        "empresa_6203",
        sa.Column("max_importe_contrato", sa.Numeric(15, 2), nullable=True),
    )
    op.add_column(
        "empresa_6203",
        sa.Column(
            "probable_grande", sa.Boolean(), nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.execute("DROP VIEW IF EXISTS leads_v3")
    op.execute(_VIEW_V3_FASE7)
    op.execute(
        """
        DO $$ BEGIN
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'fulkro_app') THEN
            GRANT SELECT ON leads_v3 TO fulkro_app;
          END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS leads_v3")
    op.execute(_VIEW_V3_OLD)
    op.execute(
        """
        DO $$ BEGIN
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'fulkro_app') THEN
            GRANT SELECT ON leads_v3 TO fulkro_app;
          END IF;
        END $$;
        """
    )
    op.drop_column("empresa_6203", "probable_grande")
    op.drop_column("empresa_6203", "max_importe_contrato")
    op.drop_column("empresa_6203", "importe_total")
