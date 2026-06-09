"""radar_v9_perfect_i_001 · Bloque I incremental scrape checkpoints.

Mega-Atom RADAR-V9-PERFECT Fase 1.B · Marcos approve cement Option A
(2026-05-26 · extend SourceRun model · NO new sources_state table per
OPS-045 audit-first preserve existing).

Extends `sources_runs` audit log table per Marcos D1 directive:

- last_external_id_seen VARCHAR(120)
    Top tender external_id procesado en este run (típicamente el most
    recent en Pattern A · or any sentinel en Pattern B/C). Usado para
    early-exit en próximo run + display dashboard "last cursor".

- tenders_skipped_dedup INT DEFAULT 0
    Counter cuántos tenders skipped por ya existir en DB (no DB write ·
    no LLM cost). Dashboard cost-saving visibility per source.

- cost_usd_per_source NUMERIC(10,4) DEFAULT 0
    Cost LLM tracked per-source per-run. Cumulative reporting +
    optimization input (qué source consume más LLM).

- idx_sources_runs_source_finished PARTIAL INDEX status='success'
    Acelera query "last successful run per source" usada por
    IncrementalScraperHelper.get_last_successful_at() (dashboard load +
    pre-launch modal estimates).

Backward compatible: todas columnas nullable o default 0. Sin migration
data backfill (cero rows tienen sentido NULL hasta primer incremental run).

Pattern Marcos cement (OPS-045 audit-first reveals existing):
  · NO new sources_state table (Marcos's spec literal aspiracional)
  · sources_runs ya contiene rango_desde/rango_hasta/finished_at suficient
    para derive last_scraped_at via MAX(finished_at) WHERE status='success'.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "radar_v9_perfect_i_001"
down_revision = "radar_v9_perfect_g_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Checkpoint columns per Marcos D1 cement (extend SourceRun)
    op.add_column(
        "sources_runs",
        sa.Column("last_external_id_seen", sa.String(120), nullable=True),
    )
    op.add_column(
        "sources_runs",
        sa.Column(
            "tenders_skipped_dedup",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "sources_runs",
        sa.Column(
            "cost_usd_per_source",
            sa.Numeric(10, 4),
            nullable=False,
            server_default="0",
        ),
    )

    # Partial index acelera "last successful run per source" query patron
    # usado por IncrementalScraperHelper.get_last_successful_at().
    op.create_index(
        "idx_sources_runs_source_finished",
        "sources_runs",
        ["source_id", sa.text("finished_at DESC")],
        postgresql_where=sa.text("status = 'success'"),
    )


def downgrade() -> None:
    op.drop_index("idx_sources_runs_source_finished", table_name="sources_runs")
    op.drop_column("sources_runs", "cost_usd_per_source")
    op.drop_column("sources_runs", "tenders_skipped_dedup")
    op.drop_column("sources_runs", "last_external_id_seen")
