"""lead_to_project_7_0_lead_conversion_cols

Revision ID: lead_to_project_7_0_001
Revises: fiscal_settings_admin_001
Create Date: 2026-06-03

Punto #7 (conversión lead ganado→proyecto · Fase 7.0). Migración **additive**
y **nullable** (segura sobre filas existentes) que formaliza la traza
lead↔onboarding↔proyecto y habilita el dedup robusto:

- ``onboarding_sessions.lead_id`` (FK leads.id, nullable) → mata la dependencia
  frágil del ``project_id`` compartido como único nexo lead↔onboarding (de la que
  depende #6). Las sesiones in-portal post-firma siguen sin lead → nullable.
- ``leads.cif_norm`` + ``clients.cif_norm`` (nullable, indexadas) → CIF normalizado
  como clave de dedup (evita proyectos duplicados por formato de CIF distinto entre
  ``Lead.empresa_cif`` y la respuesta ``q-cif`` del cuestionario).
- ``leads.papel_aapp`` + ``projects.papel_aapp`` (nullable) → papel ante la AAPP
  capturado en ``q-papel_aapp``; criterio de categorización tipado. En Lead se usa
  ya en fase embudo; se arrastra a Project en la promoción.

Scope-only (política TODO-DB-DRIFT-001 · sin autogenerate): conserva SOLO estas
operaciones. Todo nullable → ``fulkro_app`` hereda el GRANT de tabla. Reversible.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "lead_to_project_7_0_001"
down_revision: Union[str, None] = "fiscal_settings_admin_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # onboarding_sessions.lead_id (FK leads.id, nullable) + índice
    op.add_column(
        "onboarding_sessions",
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_onboarding_sessions_lead_id",
        "onboarding_sessions", "leads",
        ["lead_id"], ["id"],
    )
    op.create_index(
        "ix_onboarding_sessions_lead_id", "onboarding_sessions", ["lead_id"],
    )

    # leads.cif_norm + papel_aapp
    op.add_column("leads", sa.Column("cif_norm", sa.String(length=20), nullable=True))
    op.create_index("ix_leads_cif_norm", "leads", ["cif_norm"])
    op.add_column("leads", sa.Column("papel_aapp", sa.String(length=40), nullable=True))

    # clients.cif_norm
    op.add_column("clients", sa.Column("cif_norm", sa.String(length=20), nullable=True))
    op.create_index("ix_clients_cif_norm", "clients", ["cif_norm"])

    # projects.papel_aapp
    op.add_column("projects", sa.Column("papel_aapp", sa.String(length=40), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "papel_aapp")
    op.drop_index("ix_clients_cif_norm", table_name="clients")
    op.drop_column("clients", "cif_norm")
    op.drop_column("leads", "papel_aapp")
    op.drop_index("ix_leads_cif_norm", table_name="leads")
    op.drop_column("leads", "cif_norm")
    op.drop_index("ix_onboarding_sessions_lead_id", table_name="onboarding_sessions")
    op.drop_constraint(
        "fk_onboarding_sessions_lead_id", "onboarding_sessions", type_="foreignkey",
    )
    op.drop_column("onboarding_sessions", "lead_id")
