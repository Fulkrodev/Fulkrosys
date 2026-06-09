"""radar_lead_v9_alignment · sub-atom RADAR-V9 Phase C.

V9-ready alignment per spec §4 Lead + decisión Marcos D3 + D4.

D4: DROP radar_leads.estado duplicate col (consumers refactored cumulative
    en Phase C.2-C.4 · backend schemas + service + api + frontend zod schemas
    + pages + components + hooks · 435 rows preserved · estado_contacto V9
    canonical state machine)
D3: ALTER CHECK constraint estado_contacto 8 → 10 values spec §3.G
    · backfill renames: enviado→contactado · respondio→respondido (typo) ·
      reunion_agendada→discovery_scheduled · ganado→cerrado_ganado ·
      no_interesa+descartado collapse to descartado
    · all 435 rows current=nuevo empirically · mapping no-op safe

ADD V9 cols spec §4 Lead canonical:
- criterios intersection: c1_concursando + c2_pliego_exige_ens + c2_source
  enum + c3_no_certificada_ccn + c4_pattern_count + c4_pattern_type enum +
  c5_sweet_spot (7 cols total · feature-prompt scoring rerun populará)
- dolor_summary text (V9 LLM-generated · matches spec §4)
- best_pliego_id FK tenders ON DELETE SET NULL (most-relevant pliego pointer)
- jurisprudencia_citable JSONB default '{}' (informe_25_2025 · tarcja_451_2025 ·
  canarias_131_2025 flags · spec §2.5)
- feedback_score enum (cualificado | no_cualificado) · Marcos training
- timeline_json JSONB default '[]' (ordered events spec §3.G)

3 new shared enums (NOT reused otras tablas):
- c2_source_enum (explicit | inferred)
- c4_pattern_type_enum (multi_adj | licitacion_abierta)
- feedback_score_enum (cualificado | no_cualificado)

Backward compat:
- 435 rows preserved · 0 destructive
- estado_contacto invariants intact (all = nuevo · matches Path A 2026-05-25)
- temperatura distribution UNCHANGED (314/22/99 ardiendo/sostenido/caliente)

Revision: radar_v9_c_lead_001
Revises: radar_v9_b_tender_001
Create: 2026-05-25
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "radar_v9_c_lead_001"
down_revision: Union[str, None] = "radar_v9_b_tender_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. NEW enums (3) ─────────────────────────────────────────────
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE c2_source_enum AS ENUM ('explicit', 'inferred');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE c4_pattern_type_enum AS ENUM (
                'multi_adj', 'licitacion_abierta'
            );
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE feedback_score_enum AS ENUM (
                'cualificado', 'no_cualificado'
            );
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
        """
    )

    # ── 2. estado_contacto rename + CHECK 10 values (D3) ─────────────
    # 2.a Drop existing CHECK constraint (8 values)
    op.execute(
        "ALTER TABLE radar_leads DROP CONSTRAINT IF EXISTS "
        "radar_leads_estado_contacto_check"
    )
    # 2.b Backfill renames (all 435 rows = 'nuevo' empirically · no-op
    # safe · pero apply UPDATE for any future rows that may have been
    # added between audit and migration application)
    op.execute(
        """
        UPDATE radar_leads SET estado_contacto = CASE
            WHEN estado_contacto = 'enviado' THEN 'contactado'
            WHEN estado_contacto = 'respondio' THEN 'respondido'
            WHEN estado_contacto = 'reunion_agendada' THEN 'discovery_scheduled'
            WHEN estado_contacto = 'ganado' THEN 'cerrado_ganado'
            WHEN estado_contacto = 'no_interesa' THEN 'descartado'
            ELSE estado_contacto
        END
        """
    )
    # 2.c Add new CHECK constraint con spec §3.G 10 values
    op.execute(
        """
        ALTER TABLE radar_leads ADD CONSTRAINT
            radar_leads_estado_contacto_check
        CHECK (estado_contacto IN (
            'nuevo', 'contactado', 'respondido', 'discovery_scheduled',
            'discovery_realizada', 'propuesta_enviada', 'en_negociacion',
            'cerrado_ganado', 'cerrado_perdido', 'descartado'
        ))
        """
    )

    # ── 3. DROP radar_leads.estado duplicate (D4) ────────────────────
    # Consumers refactored cumulative en Phase C.2-C.4 commits
    op.drop_column("radar_leads", "estado")

    # ── 4. ADD criterios c1-c5 + scoring V9 cols ─────────────────────
    op.add_column("radar_leads", sa.Column(
        "c1_concursando", sa.Boolean(), nullable=True))
    op.add_column("radar_leads", sa.Column(
        "c2_pliego_exige_ens", sa.Boolean(), nullable=True))
    op.add_column("radar_leads", sa.Column(
        "c2_source",
        postgresql.ENUM(name="c2_source_enum", create_type=False),
        nullable=True))
    op.add_column("radar_leads", sa.Column(
        "c3_no_certificada_ccn", sa.Boolean(), nullable=True))
    op.add_column("radar_leads", sa.Column(
        "c4_pattern_count", sa.Integer(),
        nullable=False, server_default=sa.text("0")))
    op.add_column("radar_leads", sa.Column(
        "c4_pattern_type",
        postgresql.ENUM(name="c4_pattern_type_enum", create_type=False),
        nullable=True))
    op.add_column("radar_leads", sa.Column(
        "c5_sweet_spot", sa.Boolean(), nullable=True))

    # ── 5. dolor_summary + best_pliego + JSONB + feedback ────────────
    op.add_column("radar_leads", sa.Column(
        "dolor_summary", sa.Text(), nullable=True))
    op.add_column("radar_leads", sa.Column(
        "best_pliego_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_radar_leads_best_pliego_id",
        "radar_leads", "tenders",
        ["best_pliego_id"], ["id"],
        ondelete="SET NULL",
    )
    op.add_column("radar_leads", sa.Column(
        "jurisprudencia_citable", postgresql.JSONB(),
        nullable=False, server_default=sa.text("'{}'::jsonb")))
    op.add_column("radar_leads", sa.Column(
        "feedback_score",
        postgresql.ENUM(name="feedback_score_enum", create_type=False),
        nullable=True))
    op.add_column("radar_leads", sa.Column(
        "timeline_json", postgresql.JSONB(),
        nullable=False, server_default=sa.text("'[]'::jsonb")))


def downgrade() -> None:
    # ── 5/4. JSONB + criterios + best_pliego + feedback DROP ─────────
    op.drop_column("radar_leads", "timeline_json")
    op.drop_column("radar_leads", "feedback_score")
    op.drop_column("radar_leads", "jurisprudencia_citable")
    op.drop_constraint(
        "fk_radar_leads_best_pliego_id", "radar_leads", type_="foreignkey"
    )
    op.drop_column("radar_leads", "best_pliego_id")
    op.drop_column("radar_leads", "dolor_summary")
    op.drop_column("radar_leads", "c5_sweet_spot")
    op.drop_column("radar_leads", "c4_pattern_type")
    op.drop_column("radar_leads", "c4_pattern_count")
    op.drop_column("radar_leads", "c3_no_certificada_ccn")
    op.drop_column("radar_leads", "c2_source")
    op.drop_column("radar_leads", "c2_pliego_exige_ens")
    op.drop_column("radar_leads", "c1_concursando")

    # ── 3. estado restore (best-effort · lossy del collapse no_interesa) ─
    op.add_column(
        "radar_leads",
        sa.Column("estado", sa.String(length=50), nullable=True),
    )
    # Best-effort backfill estado from estado_contacto
    # (lossy · cannot recover discard/no_interesa from notas_marcos prefix)
    op.execute(
        """
        UPDATE radar_leads SET estado = CASE
            WHEN estado_contacto = 'contactado' THEN 'enviado'
            WHEN estado_contacto = 'respondido' THEN 'respondio'
            WHEN estado_contacto = 'discovery_scheduled' THEN 'reunion_agendada'
            WHEN estado_contacto = 'cerrado_ganado' THEN 'ganado'
            WHEN estado_contacto = 'descartado' THEN 'descartado'
            WHEN estado_contacto IN (
                'discovery_realizada', 'en_negociacion', 'cerrado_perdido'
            ) THEN 'nuevo'
            ELSE 'nuevo'
        END
        """
    )
    op.alter_column("radar_leads", "estado", nullable=False)

    # ── 2. estado_contacto CHECK restore (8 values legacy) ───────────
    op.execute(
        "ALTER TABLE radar_leads DROP CONSTRAINT IF EXISTS "
        "radar_leads_estado_contacto_check"
    )
    op.execute(
        """
        UPDATE radar_leads SET estado_contacto = CASE
            WHEN estado_contacto = 'contactado' THEN 'enviado'
            WHEN estado_contacto = 'respondido' THEN 'respondio'
            WHEN estado_contacto = 'discovery_scheduled' THEN 'reunion_agendada'
            WHEN estado_contacto = 'cerrado_ganado' THEN 'ganado'
            WHEN estado_contacto IN (
                'discovery_realizada', 'en_negociacion', 'cerrado_perdido'
            ) THEN 'nuevo'
            ELSE estado_contacto
        END
        """
    )
    op.execute(
        """
        ALTER TABLE radar_leads ADD CONSTRAINT
            radar_leads_estado_contacto_check
        CHECK (estado_contacto IN (
            'nuevo', 'enviado', 'respondio', 'reunion_agendada',
            'propuesta_enviada', 'ganado', 'descartado', 'no_interesa'
        ))
        """
    )

    # ── 1. Enums DROP ────────────────────────────────────────────────
    op.execute("DROP TYPE IF EXISTS feedback_score_enum")
    op.execute("DROP TYPE IF EXISTS c4_pattern_type_enum")
    op.execute("DROP TYPE IF EXISTS c2_source_enum")
