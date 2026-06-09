"""radar_v9_perfect_f_001 · Bloque F pliego defectuoso TACPC Canarias 131/2025.

Mega-Atom RADAR-V9-PERFECT Fase 2.B · Marcos approve cement 2026-05-27.
Doctrina TACPC Canarias 131/2025 (19 agosto 2025): pliegos sin
categorización ENS son anulables. Detector v1 pragmatic con confidence
MEDIUM (limitation pliego_excerpt 0.5% corpus actual).

Esquema additive:

tenders extension (4 cols):
- pliego_defectuoso BOOLEAN DEFAULT FALSE · flag detector v1
- pliego_defectuoso_confidence NUMERIC(3,2) NULL · 0.60-0.75 MEDIUM (v1)
- pliego_defectuoso_razon TEXT NULL · human-readable criterios matched
- pliego_defectuoso_detected_at TIMESTAMP WITH TIME ZONE NULL · timestamp

radar_leads extension (1 col):
- angulo_comercial VARCHAR(50) NULL · enum {pliego_defectuoso ·
  renovacion_proxima · standard · NULL}

2 partial indexes:
- idx_tenders_pliego_defectuoso · WHERE pliego_defectuoso=TRUE · acelera
  dashboard query "all pliegos defectuosos active"
- idx_radar_leads_angulo_comercial · WHERE angulo_comercial IS NOT NULL ·
  acelera frontend filter "Solo pliegos defectuosos"

Backward compatible · all cols nullable/defaults · NO data backfill.
Detector v1 batch run post-migration popula columns empirically.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "radar_v9_perfect_f_001"
down_revision = "radar_v9_perfect_i_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # tenders · 4 cols pliego_defectuoso
    op.add_column(
        "tenders",
        sa.Column(
            "pliego_defectuoso",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "tenders",
        sa.Column(
            "pliego_defectuoso_confidence",
            sa.Numeric(3, 2),
            nullable=True,
        ),
    )
    op.add_column(
        "tenders",
        sa.Column("pliego_defectuoso_razon", sa.Text(), nullable=True),
    )
    op.add_column(
        "tenders",
        sa.Column(
            "pliego_defectuoso_detected_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    # radar_leads · angulo_comercial enum-like VARCHAR (NO CHECK constraint
    # para agilidad iterativa post-v1 detector · Future-X migrate VARCHAR→
    # enum una vez cement valores empíricos)
    op.add_column(
        "radar_leads",
        sa.Column(
            "angulo_comercial", sa.String(50), nullable=True,
        ),
    )

    # Partial indexes · acelera frontend queries
    op.create_index(
        "idx_tenders_pliego_defectuoso",
        "tenders",
        ["pliego_defectuoso"],
        postgresql_where=sa.text("pliego_defectuoso = true"),
    )
    op.create_index(
        "idx_radar_leads_angulo_comercial",
        "radar_leads",
        ["angulo_comercial"],
        postgresql_where=sa.text("angulo_comercial IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "idx_radar_leads_angulo_comercial", table_name="radar_leads"
    )
    op.drop_index(
        "idx_tenders_pliego_defectuoso", table_name="tenders"
    )
    op.drop_column("radar_leads", "angulo_comercial")
    op.drop_column("tenders", "pliego_defectuoso_detected_at")
    op.drop_column("tenders", "pliego_defectuoso_razon")
    op.drop_column("tenders", "pliego_defectuoso_confidence")
    op.drop_column("tenders", "pliego_defectuoso")
