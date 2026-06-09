"""ENS Radar schema widening · Sub-atom E.FIX Bug #1 + Weakness #2.

Audit-first E.C reveló truncation risks empíricos en el test PLACSP real:

Bug #1 · companies.cif String(20) → String(50):
  El pipeline genera CIFs sintéticos ``SIN_CIF_<norm[:30]>`` (hasta 38 chars)
  cuando una empresa licitadora no tiene CIF en el feed PLACSP. La columna
  String(20) los rechazaba con psycopg2.errors.StringDataRightTruncation
  (3478 ocurrencias en el run f23a54b8). Real CIFs caben en 9 chars · el
  placeholder semántico necesita más ancho.

Weakness #2 · radar_leads.temperatura String(20) → String(30):
  El valor ``vence_pronto_oferta`` (19 chars) deja 1 char de margen sobre
  String(20). Frágil ante futuros niveles de temperatura. String(30) da
  holgura sin coste.

Ownership: companies + radar_leads owned by ``fulkro``. El usuario de
migración ``fulkro_migrate`` es miembro de ``fulkro`` → SET ROLE fulkro
permite el ALTER (rol se resetea al cierre de la transacción Alembic).

Widening VARCHAR es operación segura en Postgres: no reescribe la tabla,
no afecta unique constraint de cif, no afecta datos existentes.

Revision ID: sane_ens_radar_schema_widen_001
Revises: sane_mb10_ff_overrides_001
Create Date: 2026-05-14
"""
from alembic import op
import sqlalchemy as sa


revision = "sane_ens_radar_schema_widen_001"
down_revision = "sane_mb10_ff_overrides_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # companies + radar_leads owned by fulkro · fulkro_migrate ∈ fulkro.
    op.execute("SET ROLE fulkro")

    op.alter_column(
        "companies",
        "cif",
        existing_type=sa.String(20),
        type_=sa.String(50),
        existing_nullable=False,
    )
    op.alter_column(
        "radar_leads",
        "temperatura",
        existing_type=sa.String(20),
        type_=sa.String(30),
        existing_nullable=False,
    )

    op.execute("RESET ROLE")


def downgrade() -> None:
    op.execute("SET ROLE fulkro")

    op.alter_column(
        "radar_leads",
        "temperatura",
        existing_type=sa.String(30),
        type_=sa.String(20),
        existing_nullable=False,
    )
    op.alter_column(
        "companies",
        "cif",
        existing_type=sa.String(50),
        type_=sa.String(20),
        existing_nullable=False,
    )

    op.execute("RESET ROLE")
