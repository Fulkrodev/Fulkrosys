"""drop_ens_radar · retira por completo el subsistema ENS Radar (M10b)

Revision ID: drop_ens_radar_001
Revises: rls_tenant_hardening_p0_001
Create Date: 2026-06-07

El subsistema ENS Radar (motor m10_ens_radar + frontend (radar) + scrapers +
scoring + outreach + auth ens_radar_owner) se retira del producto. Esta
migración elimina las tablas del árbol RADAR y la columna vestigial
``leads.radar_lead_id`` (tracking radar->comercial, sin FK).

Seguro: verificado que NINGUNA tabla no-radar tiene FK entrante hacia las tablas
radar (information_schema), por lo que ``DROP TABLE ... CASCADE`` no afecta al
ciclo comercial (leads/proposals/contracts) ni a ningún otro motor.

Forward-only: el subsistema fue retirado; ``downgrade`` es no-op (no se recrea).
"""
from typing import Sequence, Union

from alembic import op

revision: str = "drop_ens_radar_001"
down_revision: Union[str, None] = "rls_tenant_hardening_p0_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Unión de todos los nombres de tabla que el árbol RADAR creó a lo largo de su
# historia (v2 + v3 + v9 + perfect). ``IF EXISTS`` hace la migración idempotente
# sobre cualquier estado de BD (los nombres legacy que ya no existan se ignoran).
_RADAR_TABLES: tuple[str, ...] = (
    "radar_pipeline_runs",
    "radar_leads",
    "decision_makers",
    "participations",
    "excluded_leads",
    "empresas_descartadas",
    "tenders",
    "companies",
    "placsp_adjudicaciones",
    "cnae6203_raw",
    "empresa_6203",
    "ccn_certificados",
    "sources_runs",
    "ens_analysis",
    "data_treatment_cache",
    "sources_state",
    "radar_runs",
    "radar_companies",
    "radar_participations",
)


def upgrade() -> None:
    # Columnas vestigiales de tracking radar (sin FK) en tablas comerciales.
    op.execute("ALTER TABLE leads DROP COLUMN IF EXISTS radar_lead_id")
    op.execute("ALTER TABLE clients DROP COLUMN IF EXISTS lead_radar_id")
    for table in _RADAR_TABLES:
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")


def downgrade() -> None:
    # Forward-only · el subsistema ENS Radar fue retirado del producto.
    pass
