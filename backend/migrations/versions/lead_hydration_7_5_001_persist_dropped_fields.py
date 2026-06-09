"""lead_hydration_7_5_persist_dropped_fields

Revision ID: lead_hydration_7_5_001
Revises: lead_to_project_7_0_001
Create Date: 2026-06-03

Punto #7 (Fase 7.5 · hidratación del wizard desde lead + persistencia de los
campos que el wizard recoge pero hoy se descartan). Migración **additive** y
**nullable** (segura sobre filas existentes):

- ``clients.domicilio_fiscal`` + ``clients.web`` + ``clients.persona_contacto``
  → ``StepDatosCliente`` los recoge pero ``provision_project`` los tiraba
  (``clients`` no tenía columna). Necesarios consultables para el encabezado
  legal de los contratos (domicilio + persona de contacto) y los paquetes
  ENAC/CCN-STIC-809 (datos de la organización auditada) → columnas tipadas, NO
  JSONB (atributos de primera clase, estables y consultables).
- ``client_users.cargo`` → ``StepFirstUser`` lo recoge; ``ClientUser``
  persistía ``full_name`` pero no ``cargo`` (escalar del usuario del portal).

Scope-only (política TODO-DB-DRIFT-001 · sin autogenerate): conserva SOLO estas
operaciones. Todo nullable → ``fulkro_app`` hereda el GRANT de tabla. Reversible.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "lead_hydration_7_5_001"
down_revision: Union[str, None] = "lead_to_project_7_0_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "clients",
        sa.Column("domicilio_fiscal", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "clients",
        sa.Column("web", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "clients",
        sa.Column("persona_contacto", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "client_users",
        sa.Column("cargo", sa.String(length=150), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("client_users", "cargo")
    op.drop_column("clients", "persona_contacto")
    op.drop_column("clients", "web")
    op.drop_column("clients", "domicilio_fiscal")
