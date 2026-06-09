"""Add legal_obligations_catalog seed table.

Tabla CATALOGO MAESTRO de obligaciones legales (RGPD/LOPDGDD/NIS2/DORA/AI_Act)
compartida globalmente (sin project_id, sin RLS, readonly por convencion).

SEPARADA de la tabla operacional `legal_obligations` preexistente (per-project,
RLS forzada, workflow tracking via M21 Diagnosis). El catalogo aqui es el
source-of-truth de las obligaciones; M21 A24 cross-compliance creara instancias
per-cliente en la operacional a partir del catalogo.

Coherencia con las otras 5 tablas catalogo seeded:
- magerit_safeguards (98 entries · Libro II Cap.6)
- magerit_threats (57 entries · Libro II Cap.5)
- ens_measures (73 medidas Anexo II)
- ens_measure_guias_ccn (mapping medidas->CCN-STIC primarias)
- ens_measure_refuerzos (R1-R5)

Revision ID: add_legal_obl_catalog_001
Revises: sane_ens_radar_rol_fix_001
Create Date: 2026-05-17
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "add_legal_obl_catalog_001"
down_revision = "sane_ens_radar_rol_fix_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "legal_obligations_catalog",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("codigo", sa.String(length=50), nullable=False),
        sa.Column("regulacion", sa.String(length=30), nullable=False),
        sa.Column("articulo", sa.String(length=50), nullable=True),
        sa.Column("titulo", sa.String(length=255), nullable=False),
        sa.Column("obligacion", sa.Text(), nullable=False),
        sa.Column("sector_aplica", postgresql.JSONB(), nullable=True),
        sa.Column("ens_categoria_aplica", postgresql.JSONB(), nullable=True),
        sa.Column("evidencia_requerida", sa.Text(), nullable=True),
        sa.Column("vinculo_medida_ens", postgresql.JSONB(), nullable=True),
        sa.Column("fuente_url", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("codigo", name="legal_obligations_catalog_codigo_key"),
    )
    op.create_index(
        "ix_legal_obligations_catalog_regulacion",
        "legal_obligations_catalog",
        ["regulacion"],
    )
    # Catalog tables: fulkro_app NOSUPERUSER necesita SELECT para runtime
    # A24 cross-compliance (read-only consumer). fulkro_migrate (superuser)
    # ya tiene todos los privilegios via ownership.
    op.execute("GRANT SELECT ON legal_obligations_catalog TO fulkro_app")


def downgrade() -> None:
    op.drop_index(
        "ix_legal_obligations_catalog_regulacion",
        table_name="legal_obligations_catalog",
    )
    op.drop_table("legal_obligations_catalog")
