"""Radar v3 FASE 1: placsp_adjudicaciones (skinny) + participations.cif_norm.

Híbrido (decisión Marcos): tabla skinny para el backfill masivo PLACSP
2021→2026 (solo adjudicaciones, sin hidratar tenders/companies) + columna
cif_norm en las participations existentes (poblada desde companies.cif) para
que el lead v3 cruce por cif_norm contra ccn_certificados y placsp_adjudicaciones.

Reversible (up/down). NO toca ccn_certificados.

Revision ID: radar_v3_placsp_adjud_001
Revises: create_audit_accompaniment_tables_001
"""
from alembic import op
import sqlalchemy as sa


revision = "radar_v3_placsp_adjud_001"
down_revision = "create_audit_accompaniment_tables_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Tabla skinny placsp_adjudicaciones ──────────────────────────────
    op.create_table(
        "placsp_adjudicaciones",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("cif_norm", sa.String(length=20), nullable=False),
        sa.Column("razon_social", sa.String(length=500), nullable=True),
        sa.Column("expediente", sa.String(length=200), nullable=False),
        sa.Column("organismo", sa.String(length=500), nullable=True),
        sa.Column("fecha_adjudicacion", sa.DateTime(), nullable=True),
        sa.Column("importe", sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column("external_id", sa.String(length=250), nullable=True),
        sa.Column(
            "source",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'placsp_opendata'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "cif_norm", "expediente", name="uq_placsp_adj_cif_exp"
        ),
    )
    op.create_index(
        "ix_placsp_adj_cif_norm", "placsp_adjudicaciones", ["cif_norm"]
    )
    op.create_index(
        "ix_placsp_adj_fecha", "placsp_adjudicaciones", ["fecha_adjudicacion"]
    )

    # ── participations.cif_norm (additive, nullable) ────────────────────
    op.add_column(
        "participations",
        sa.Column("cif_norm", sa.String(length=20), nullable=True),
    )
    op.create_index(
        "ix_participations_cif_norm", "participations", ["cif_norm"]
    )

    # Data backfill: normalize companies.cif → participations.cif_norm.
    # Replica normalize_cif: upper + quitar no-alfanuméricos; NULL para
    # placeholders sintéticos SIN_CIF_/UNKNOWN (no son CIFs reales).
    op.execute(
        """
        UPDATE participations p
        SET cif_norm = regexp_replace(upper(c.cif), '[^A-Z0-9]', '', 'g')
        FROM companies c
        WHERE p.company_id = c.id
          AND upper(c.cif) !~ '^(SIN_CIF|UNKNOWN)'
          AND length(
              regexp_replace(upper(c.cif), '[^A-Z0-9]', '', 'g')
          ) BETWEEN 1 AND 20
        """
    )

    # GRANTs al rol runtime NOSUPERUSER (mirror de las tablas radar
    # existentes). La migración corre como fulkro_migrate, cuyos objetos NO
    # heredan las default privileges definidas para el rol fulkro, así que el
    # GRANT debe ser explícito. Guard DO: no falla si el rol no existe.
    op.execute(
        """
        DO $$ BEGIN
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'fulkro_app') THEN
            GRANT INSERT, SELECT, UPDATE, DELETE
              ON placsp_adjudicaciones TO fulkro_app;
            GRANT USAGE, SELECT
              ON SEQUENCE placsp_adjudicaciones_id_seq TO fulkro_app;
          END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.drop_index("ix_participations_cif_norm", table_name="participations")
    op.drop_column("participations", "cif_norm")
    op.drop_index("ix_placsp_adj_fecha", table_name="placsp_adjudicaciones")
    op.drop_index("ix_placsp_adj_cif_norm", table_name="placsp_adjudicaciones")
    op.drop_table("placsp_adjudicaciones")
