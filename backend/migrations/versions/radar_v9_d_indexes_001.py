"""indexes_performance_v9 · sub-atom RADAR-V9 Phase D.

V9-ready performance indexes per spec §6 observabilidad + queries
esperadas pre-feature-prompt activations (eInforma + AEAT + LLM detector
+ vence_pronto tier + outbound).

14 indexes target (per briefing):
- radar_leads · 5 indexes (temperatura+score · estado_contacto ·
  scored_at DESC · best_pliego partial · company FK already UNIQUE existing)
- companies · 5 indexes (ccaa · en_registro_ccn · is_pyme partial ·
  fecha_caducidad_ccn partial · cif already UNIQUE existing)
- tenders · 6 indexes (source_platform · estado · ccaa · cpv ·
  fecha_fin_presentacion partial open · categoria_requerida partial detected)
- decision_makers · 1 extra (email partial NOT NULL · company_id index
  already created Phase A)

Empirical adjustments vs briefing literal:
- radar_leads.created_at NOT exists · uses scored_at (DateTime existing)
- companies.cif already has uq_companies_cif UNIQUE constraint (acts as
  index) · skip duplicate
- radar_leads.company_id already has uq_radar_leads_company_id UNIQUE
  constraint (acts as index) · skip duplicate
- decision_makers.company_id already indexed Phase A · skip duplicate
- tenders.cpv (legacy name · NOT cpv_principal · spec rename Future-X)
- tenders.estado live values divergen spec (10 values vs 6) · partial
  index uses live 'publicado' + 'preanuncio' + 'en_evaluacion' como
  proxy for "still open for bids" semantic

Total indexes effectively created: ~14 net (some duplicates skipped per
audit-first empirical reality).

EXPLAIN ANALYZE sample queries verified post-upgrade:
- radar_leads temperatura+score scan (frontend dashboard)
- tenders fin_presentacion close-soon scan (vence_pronto tier Future-X)
- companies CCN registry scan (filter sin certificar)

Revision: radar_v9_d_indexes_001
Revises: radar_v9_c_lead_001
Create: 2026-05-25
"""
from typing import Sequence, Union

from alembic import op


revision: str = "radar_v9_d_indexes_001"
down_revision: Union[str, None] = "radar_v9_c_lead_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── radar_leads (4 new indexes · company_id ya UNIQUE existing) ──
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_radar_leads_temperatura_score "
        "ON radar_leads (temperatura, score DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_radar_leads_estado_contacto "
        "ON radar_leads (estado_contacto)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_radar_leads_scored_at_desc "
        "ON radar_leads (scored_at DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_radar_leads_best_pliego "
        "ON radar_leads (best_pliego_id) "
        "WHERE best_pliego_id IS NOT NULL"
    )

    # ── companies (4 new indexes · cif ya UNIQUE existing) ───────────
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_companies_ccaa "
        "ON companies (ccaa)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_companies_en_registro_ccn "
        "ON companies (en_registro_ccn)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_companies_pyme "
        "ON companies (is_pyme) WHERE is_pyme = true"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_companies_caducidad_ccn "
        "ON companies (fecha_caducidad_ccn) "
        "WHERE fecha_caducidad_ccn IS NOT NULL"
    )

    # ── tenders (6 indexes) ──────────────────────────────────────────
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_tenders_source_platform "
        "ON tenders (source_platform)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_tenders_estado "
        "ON tenders (estado)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_tenders_ccaa "
        "ON tenders (ccaa)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_tenders_cpv "
        "ON tenders (cpv)"
    )
    # Partial index "open for bids" · live values: publicado/preanuncio/
    # en_evaluacion (spec spec semánticamente 'abierto') · Future-X
    # tender-estado-enum-normalize reconcile mapping
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_tenders_fin_presentacion_open "
        "ON tenders (fecha_fin_presentacion) "
        "WHERE estado IN ('publicado', 'preanuncio', 'en_evaluacion')"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_tenders_categoria_requerida "
        "ON tenders (categoria_requerida) "
        "WHERE explicit_in_pliego = true OR inferred_by_llm = true"
    )

    # ── decision_makers (1 extra · company_id ya indexed Phase A) ────
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_decision_makers_email "
        "ON decision_makers (email) WHERE email IS NOT NULL"
    )


def downgrade() -> None:
    # Reverse order · DROP IF EXISTS idempotent
    op.execute("DROP INDEX IF EXISTS idx_decision_makers_email")
    op.execute("DROP INDEX IF EXISTS idx_tenders_categoria_requerida")
    op.execute("DROP INDEX IF EXISTS idx_tenders_fin_presentacion_open")
    op.execute("DROP INDEX IF EXISTS idx_tenders_cpv")
    op.execute("DROP INDEX IF EXISTS idx_tenders_ccaa")
    op.execute("DROP INDEX IF EXISTS idx_tenders_estado")
    op.execute("DROP INDEX IF EXISTS idx_tenders_source_platform")
    op.execute("DROP INDEX IF EXISTS idx_companies_caducidad_ccn")
    op.execute("DROP INDEX IF EXISTS idx_companies_pyme")
    op.execute("DROP INDEX IF EXISTS idx_companies_en_registro_ccn")
    op.execute("DROP INDEX IF EXISTS idx_companies_ccaa")
    op.execute("DROP INDEX IF EXISTS idx_radar_leads_best_pliego")
    op.execute("DROP INDEX IF EXISTS idx_radar_leads_scored_at_desc")
    op.execute("DROP INDEX IF EXISTS idx_radar_leads_estado_contacto")
    op.execute("DROP INDEX IF EXISTS idx_radar_leads_temperatura_score")
