"""company_v9_extension · sub-atom RADAR-V9 Phase A.

V9-ready schema extension per spec §4 Company + decisión D1/D5/D6:
- ADD 22 cols flat (queryable per D1) + 3 JSONB meta cols
- ADD NEW table decision_makers (D5 · empty inicialmente · eInforma
  feature-prompt 2 poblará)
- ADD 3 shared enums (rol_decisional + decision_maker_fuente +
  ens_categoria · este último reuse Phase B Tender + Phase C RadarLead)
- D6 `ccaa` columna materializada flat (backend derive desde
  provincia o eInforma · poblada por feature-prompt scoring rerun)

Backward compat preserved:
- Legacy cols (tiene_ens_vigente, nivel_ens_certificado,
  fecha_certificacion_ens, fecha_caducidad_ens, empleados, website,
  facturacion double precision) INTACT · capture Future-X
  deprecation/rename cuando feature-prompts validen V9 cols
- 55103 rows existing 0 destructive · todos new cols nullable
  o con server_default seguros

Revision: radar_v9_a_company_001
Revises: golden_eval_runs_1e1b3e_001
Create: 2026-05-25

Note revision id shortened to 22 chars (was company_v9_extension_radar_v9_a_001
= 36 chars · exceeded alembic_version.version_num VARCHAR(32) limit · same
cause prevented b35 remediation_enhancement_b35_e_001 application empíricamente
en este DB · OPS-049 honesty path · b35 ALTER alembic_version fix capturable
separate Future-X chore).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "radar_v9_a_company_001"
down_revision: Union[str, None] = "golden_eval_runs_1e1b3e_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Shared enums (reuse Phase B + Phase C) ────────────────────
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE ens_categoria_enum AS ENUM ('BASICO', 'MEDIO', 'ALTO');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE rol_decisional_enum AS ENUM (
                'decisor', 'influencer', 'usuario'
            );
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE decision_maker_fuente_enum AS ENUM (
                'einforma', 'borme', 'linkedin', 'manual', 'outbound_response'
            );
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
        """
    )

    # ── 2. companies V9 extension (22 flat cols + 3 JSONB meta) ──────
    # ubicacion (D6 ccaa derived backend)
    op.add_column("companies", sa.Column(
        "cnae_secundarios", postgresql.ARRAY(sa.String()), nullable=True))
    op.add_column("companies", sa.Column(
        "ccaa", sa.String(length=50), nullable=True))
    op.add_column("companies", sa.Column(
        "municipio", sa.String(length=200), nullable=True))
    op.add_column("companies", sa.Column(
        "codigo_postal", sa.String(length=5), nullable=True))

    # size (plantilla coexists with legacy empleados · Future-X dedup)
    op.add_column("companies", sa.Column(
        "plantilla", sa.Integer(), nullable=True))
    op.add_column("companies", sa.Column(
        "capital_social", sa.Numeric(15, 2), nullable=True))
    op.add_column("companies", sa.Column(
        "is_pyme", sa.Boolean(), nullable=True))
    op.add_column("companies", sa.Column(
        "is_micro", sa.Boolean(), nullable=True))

    # estructura
    op.add_column("companies", sa.Column(
        "is_ute", sa.Boolean(), nullable=False,
        server_default=sa.text("false")))
    op.add_column("companies", sa.Column(
        "parent_company_id", sa.Integer(), nullable=True))
    op.add_column("companies", sa.Column(
        "grupo_empresarial", sa.String(length=200), nullable=True))
    op.create_foreign_key(
        "fk_companies_parent_company_id",
        "companies", "companies",
        ["parent_company_id"], ["id"],
        ondelete="SET NULL",
    )

    # ens_status V9 (_ccn suffix · coexist con legacy *_ens)
    op.add_column("companies", sa.Column(
        "en_registro_ccn", sa.Boolean(), nullable=False,
        server_default=sa.text("false")))
    op.add_column("companies", sa.Column(
        "nivel_certificado_ccn",
        postgresql.ENUM(name="ens_categoria_enum", create_type=False),
        nullable=True))
    op.add_column("companies", sa.Column(
        "fecha_certificacion_ccn", sa.Date(), nullable=True))
    op.add_column("companies", sa.Column(
        "fecha_caducidad_ccn", sa.Date(), nullable=True))
    op.add_column("companies", sa.Column(
        "auditor_ccn", sa.String(length=200), nullable=True))
    op.add_column("companies", sa.Column(
        "sistemas_alcance_ccn", sa.Text(), nullable=True))
    op.add_column("companies", sa.Column(
        "tiene_declaracion_basica", sa.Boolean(), nullable=False,
        server_default=sa.text("false")))

    # contactability (web coexists con legacy website · Future-X dedup)
    op.add_column("companies", sa.Column(
        "email_general", sa.String(length=255), nullable=True))
    op.add_column("companies", sa.Column(
        "telefono", sa.String(length=50), nullable=True))
    op.add_column("companies", sa.Column(
        "web", sa.String(length=500), nullable=True))
    op.add_column("companies", sa.Column(
        "direccion_fiscal", sa.String(length=500), nullable=True))

    # JSONB metadata (D1 · campos no-queryables nested ubicacion/ens/contact)
    op.add_column("companies", sa.Column(
        "ubicacion_meta", postgresql.JSONB(), nullable=True))
    op.add_column("companies", sa.Column(
        "ens_status_meta", postgresql.JSONB(), nullable=True))
    op.add_column("companies", sa.Column(
        "contactability_meta", postgresql.JSONB(), nullable=True))

    # ── 3. decision_makers NEW table (D5) ────────────────────────────
    op.execute(
        """
        CREATE TABLE decision_makers (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL
                REFERENCES companies(id) ON DELETE CASCADE,
            nombre VARCHAR(200) NOT NULL,
            cargo VARCHAR(200),
            email VARCHAR(255),
            telefono VARCHAR(50),
            linkedin_url VARCHAR(500),
            rol_decisional rol_decisional_enum,
            fuente decision_maker_fuente_enum,
            verified BOOLEAN NOT NULL DEFAULT false,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_decision_makers_company_id "
        "ON decision_makers (company_id)"
    )
    op.execute("ALTER TABLE decision_makers OWNER TO fulkro")
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON decision_makers "
        "TO fulkro_app"
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON decision_makers "
        "TO fulkro_migrate"
    )
    op.execute(
        "GRANT USAGE, SELECT ON SEQUENCE decision_makers_id_seq "
        "TO fulkro_app"
    )
    op.execute(
        "GRANT USAGE, SELECT ON SEQUENCE decision_makers_id_seq "
        "TO fulkro_migrate"
    )


def downgrade() -> None:
    # ── 3. decision_makers DROP ──────────────────────────────────────
    op.execute("DROP TABLE IF EXISTS decision_makers CASCADE")

    # ── 2. companies V9 cols DROP (reverse order) ────────────────────
    op.drop_constraint(
        "fk_companies_parent_company_id", "companies", type_="foreignkey"
    )
    op.drop_column("companies", "contactability_meta")
    op.drop_column("companies", "ens_status_meta")
    op.drop_column("companies", "ubicacion_meta")
    op.drop_column("companies", "direccion_fiscal")
    op.drop_column("companies", "web")
    op.drop_column("companies", "telefono")
    op.drop_column("companies", "email_general")
    op.drop_column("companies", "tiene_declaracion_basica")
    op.drop_column("companies", "sistemas_alcance_ccn")
    op.drop_column("companies", "auditor_ccn")
    op.drop_column("companies", "fecha_caducidad_ccn")
    op.drop_column("companies", "fecha_certificacion_ccn")
    op.drop_column("companies", "nivel_certificado_ccn")
    op.drop_column("companies", "en_registro_ccn")
    op.drop_column("companies", "grupo_empresarial")
    op.drop_column("companies", "parent_company_id")
    op.drop_column("companies", "is_ute")
    op.drop_column("companies", "is_micro")
    op.drop_column("companies", "is_pyme")
    op.drop_column("companies", "capital_social")
    op.drop_column("companies", "plantilla")
    op.drop_column("companies", "codigo_postal")
    op.drop_column("companies", "municipio")
    op.drop_column("companies", "ccaa")
    op.drop_column("companies", "cnae_secundarios")

    # ── 1. Shared enums DROP ─────────────────────────────────────────
    # Note: each enum DROP IF EXISTS · safe even if Phase B/C also
    # created them (idempotent · downgrade -1 from Phase A reverts only
    # Phase A · subsequent phases handle their own enum usage via
    # `create_type=False`).
    op.execute("DROP TYPE IF EXISTS decision_maker_fuente_enum")
    op.execute("DROP TYPE IF EXISTS rol_decisional_enum")
    op.execute("DROP TYPE IF EXISTS ens_categoria_enum")
