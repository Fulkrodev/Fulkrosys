"""tender_v9_extension · sub-atom RADAR-V9 Phase B.

V9-ready schema extension per spec §4 Tender + decisión D1/D6:
- ADD source_platform · CAST to tender_source_platform_enum con backfill
  empírico (placsp→PLACSP · cataluna→CAT · madrid_ccaa→MAD · test→OTHER
  · ELSE→OTHER seguro). Legacy `source` VARCHAR(50) KEPT alive (pipeline
  + sources/*.py + scoring/*.py consumen tender.source · refactor scope
  expansion ~2-3h capturable Future-1.E.radar.tender-source-deprecate
  cuando pipeline migra read-path a source_platform). Doble columna durante
  transición · pattern análogo Phase A legacy *_ens vs V9 *_ccn.
- ADD 14 cols flat (queryable per D1) + 2 JSONB meta cols
- ADD 3 new enums (tender_source_platform · organismo_tipo · tipo_procedimiento)
- Reuse ens_categoria_enum (Phase A) para categoria_requerida
- D6 `ccaa` columna materializada flat (backend derive desde organismo
  o ubicación · poblada feature-prompt scoring rerun)

Honesty path · decisiones explícitas:
- estado VARCHAR(50) LEFT INTACT (legacy 6 values divergen de spec 6 ·
  unión = 10 values · capture Future-1.E.radar.tender-estado-enum-normalize
  ~1-2h cuando pipeline reconcile en_evaluacion/resuelto/publicado/preanuncio
  mapping AAPP normalize)
- fecha_publicacion + fecha_fin_presentacion + fecha_adjudicacion +
  fecha_formalizacion LEFT INTACT como timestamp (spec quiere Date · cast
  pierde info time-of-day · Future-X type rename si demand-driven)
- importe DOUBLE LEFT INTACT · ADD importe_adjudicado nullable distinct
  spec (importe_estimado field NO add · capture Future-X rename)
- Legacy raw_data JSON LEFT INTACT como source-of-truth fuente original

Backward compat preserved firmísimo:
- 102685 rows tenders existing · 0 destructive
- source rename via ADD source_platform + UPDATE backfill + DROP source ·
  pipeline reading `source` continúa funcionando hasta refactor (FK Future-X)

Revision: radar_v9_b_tender_001
Revises: radar_v9_a_company_001
Create: 2026-05-25
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "radar_v9_b_tender_001"
down_revision: Union[str, None] = "radar_v9_a_company_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Enums NEW (3) ─────────────────────────────────────────────
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE tender_source_platform_enum AS ENUM (
                'PLACSP', 'TED', 'CAT', 'EUS', 'GAL', 'MAD', 'NAV',
                'RIO', 'OTHER'
            );
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE organismo_tipo_enum AS ENUM (
                'estatal', 'autonomico', 'local',
                'instrumental', 'universitario'
            );
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE tipo_procedimiento_enum AS ENUM (
                'abierto', 'restringido', 'negociado',
                'SARA', 'menor', 'simplificado'
            );
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
        """
    )

    # ── 2. ADD source_platform · keep legacy source (Future-X drop) ──
    # 2.a Add new column nullable temporal
    op.add_column(
        "tenders",
        sa.Column(
            "source_platform",
            postgresql.ENUM(
                name="tender_source_platform_enum",
                create_type=False,
            ),
            nullable=True,
        ),
    )
    # 2.b Backfill empirical mapping (audit reveals 4 distinct values
    # · pipeline + sources/*.py + scoring/*.py continue reading legacy
    # `source` VARCHAR · Future-X refactor read-path a source_platform)
    op.execute(
        """
        UPDATE tenders
        SET source_platform = CASE
            WHEN source = 'placsp' THEN 'PLACSP'::tender_source_platform_enum
            WHEN source = 'cataluna' THEN 'CAT'::tender_source_platform_enum
            WHEN source = 'madrid_ccaa' THEN 'MAD'::tender_source_platform_enum
            WHEN source = 'test' THEN 'OTHER'::tender_source_platform_enum
            ELSE 'OTHER'::tender_source_platform_enum
        END
        """
    )
    # 2.c Enforce NOT NULL post-backfill (102685 rows mapped 100%)
    op.alter_column(
        "tenders", "source_platform", nullable=False
    )
    # NOTE: legacy `source` VARCHAR(50) intentionally KEPT alive
    # Future-1.E.radar.tender-source-deprecate captures DROP cuando
    # pipeline read-path migra a source_platform.

    # ── 3. Tender V9 cols flat (14 nuevas) ───────────────────────────
    # ubicacion derived (D6 ccaa)
    op.add_column("tenders", sa.Column(
        "ccaa", sa.String(length=50), nullable=True))

    # organismo (nested spec §4 → flat per D1 queryable)
    op.add_column("tenders", sa.Column(
        "organismo_nif", sa.String(length=50), nullable=True))
    op.add_column("tenders", sa.Column(
        "organismo_tipo",
        postgresql.ENUM(name="organismo_tipo_enum", create_type=False),
        nullable=True,
    ))

    # cpv secundarios array
    op.add_column("tenders", sa.Column(
        "cpv_secundarios", postgresql.ARRAY(sa.String()), nullable=True))

    # importes V9 (distinct adjudicado)
    op.add_column("tenders", sa.Column(
        "importe_adjudicado", sa.Numeric(15, 2), nullable=True))

    # tipo procedimiento
    op.add_column("tenders", sa.Column(
        "tipo_procedimiento",
        postgresql.ENUM(name="tipo_procedimiento_enum", create_type=False),
        nullable=True,
    ))

    # fecha apertura (briefing critical · nueva)
    op.add_column("tenders", sa.Column(
        "fecha_apertura", sa.DateTime(timezone=False), nullable=True))

    # ens_requirement flat (4 cols · briefing literal)
    op.add_column("tenders", sa.Column(
        "explicit_in_pliego", sa.Boolean(),
        nullable=False, server_default=sa.text("false")))
    op.add_column("tenders", sa.Column(
        "inferred_by_llm", sa.Boolean(),
        nullable=False, server_default=sa.text("false")))
    op.add_column("tenders", sa.Column(
        "categoria_requerida",
        postgresql.ENUM(name="ens_categoria_enum", create_type=False),
        nullable=True,
    ))
    op.add_column("tenders", sa.Column(
        "detection_confidence", sa.Float(), nullable=True))

    # estructura lote/UTE
    op.add_column("tenders", sa.Column(
        "is_ute", sa.Boolean(), nullable=False,
        server_default=sa.text("false")))
    op.add_column("tenders", sa.Column(
        "is_lote", sa.Boolean(), nullable=False,
        server_default=sa.text("false")))
    op.add_column("tenders", sa.Column(
        "parent_tender_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_tenders_parent_tender_id",
        "tenders", "tenders",
        ["parent_tender_id"], ["id"],
        ondelete="SET NULL",
    )

    # ── 4. JSONB metadata (D1 · campos no-queryables) ────────────────
    op.add_column("tenders", sa.Column(
        "organismo_meta", postgresql.JSONB(), nullable=True))
    op.add_column("tenders", sa.Column(
        "ens_requirement_meta", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    # ── 4. JSONB DROP ────────────────────────────────────────────────
    op.drop_column("tenders", "ens_requirement_meta")
    op.drop_column("tenders", "organismo_meta")

    # ── 3. Tender V9 cols DROP (reverse) ─────────────────────────────
    op.drop_constraint(
        "fk_tenders_parent_tender_id", "tenders", type_="foreignkey"
    )
    op.drop_column("tenders", "parent_tender_id")
    op.drop_column("tenders", "is_lote")
    op.drop_column("tenders", "is_ute")
    op.drop_column("tenders", "detection_confidence")
    op.drop_column("tenders", "categoria_requerida")
    op.drop_column("tenders", "inferred_by_llm")
    op.drop_column("tenders", "explicit_in_pliego")
    op.drop_column("tenders", "fecha_apertura")
    op.drop_column("tenders", "tipo_procedimiento")
    op.drop_column("tenders", "importe_adjudicado")
    op.drop_column("tenders", "cpv_secundarios")
    op.drop_column("tenders", "organismo_tipo")
    op.drop_column("tenders", "organismo_nif")
    op.drop_column("tenders", "ccaa")

    # ── 2. source_platform DROP (legacy source remains intact) ───────
    op.drop_column("tenders", "source_platform")

    # ── 1. Enums DROP ────────────────────────────────────────────────
    op.execute("DROP TYPE IF EXISTS tipo_procedimiento_enum")
    op.execute("DROP TYPE IF EXISTS organismo_tipo_enum")
    op.execute("DROP TYPE IF EXISTS tender_source_platform_enum")
