"""radar_v9_perfect_c_001 · Mega-Atom RADAR-V9-PERFECT Bloque C.1.

Detector ENS doble (spec §3.C) · scalar fields para:
- tenders.pliego_excerpt TEXT  ·  fragmento literal PCAP/PPT que disparó
  Detector 1 regex (HABILITANTE/ADECUACION) o pasó a LLM Detector 2.
  Habilita auditoría manual + golden set Marcos labeling sin re-descargar
  pliego. Truncar a ~2000 chars (3-5 párrafos clave).
- tenders.inference_reasoning TEXT  ·  razón humana-legible del LLM
  Detector 2 (campo `razon` del JSON output) cuando inferred_by_llm=TRUE.
  Habilita explicabilidad UI + audit trail.
- ens_analysis.detection_source VARCHAR(40)  ·  rama del detector que firmó
  el resultado. Vocabulario controlado (NO enum por agilidad iterativa
  durante Bloque C exploration · Future-X to migrate VARCHAR→enum una vez
  cement los valores empíricos):
    * 'regex_habilitante'         · "ENS Categoría {Básica|Media|Alta}",
                                    "art. 65.2 LCSP", "obligatorio" · 0.95
    * 'regex_adecuacion'          · "declaración conformidad ENS",
                                    "RD 311/2022", "Anexo II", "CCN-STIC" · 0.85
    * 'cpv_whitelist'             · CPV 48/72/79/80/85/92 prefix · +0.15 boost
    * 'inferencia_art_2_3_llm'    · Detector 2 LLM real · sonnet-4-5
    * 'llm_tiebreaker'            · regex amb (conf 0.6-0.8) → LLM verdict
    * 'no_ens'                    · None of above · exige_ens=FALSE
    * 'ambiguous'                 · conflicting signals · manual review

Notas decisión empírica (OPS-045 audit-first reveals existing):
- tenders YA tiene: explicit_in_pliego BOOL, inferred_by_llm BOOL,
  categoria_requerida ens_categoria_enum, detection_confidence DOUBLE,
  ens_requirement_meta JSONB · NO duplicar (ADR-025 firmísimo).
- ens_categoria_enum existing: BASICO/MEDIO/ALTO · reused.
- ens_requirement_meta JSONB existing pero populated=0/132,230 · scalar
  fields adoptados para query performance + UI explanability sin
  ->> 'reasoning' path expressions.
- Index parcial sobre detection_source · WHERE NOT NULL (sparse field
  durante migration window).
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "radar_v9_perfect_c_001"
down_revision = "copilot_rls_client_isolation_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # tenders · scalar fields para audit + UI explanability
    op.add_column(
        "tenders",
        sa.Column("pliego_excerpt", sa.Text(), nullable=True),
    )
    op.add_column(
        "tenders",
        sa.Column("inference_reasoning", sa.Text(), nullable=True),
    )

    # ens_analysis · detection_source explicit
    op.add_column(
        "ens_analysis",
        sa.Column("detection_source", sa.String(length=40), nullable=True),
    )
    op.create_index(
        "ix_ens_analysis_detection_source",
        "ens_analysis",
        ["detection_source"],
        unique=False,
        postgresql_where=sa.text("detection_source IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ens_analysis_detection_source",
        table_name="ens_analysis",
    )
    op.drop_column("ens_analysis", "detection_source")
    op.drop_column("tenders", "inference_reasoning")
    op.drop_column("tenders", "pliego_excerpt")
