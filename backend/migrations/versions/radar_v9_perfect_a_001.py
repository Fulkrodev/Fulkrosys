"""radar_v9_perfect_a_001 · Mega-Atom RADAR-V9-PERFECT Bloque A.1.

ALTER tenders ADD autonomic_id VARCHAR(255) NULL · spec §4 modelo datos
"source_id (id original en la fuente)" cuando es autonómica (gencat_*,
navarra_*, ted_*) y conviene preservar el ID nativo además del
external_id compuesto que ya usamos.

Notas decisión empírica:
- enum tender_source_platform_enum ya tiene 9 valores (PLACSP+TED+CAT+
  EUS+GAL+MAD+NAV+RIO+OTHER) · NO extend para ALA/BIZ/GIP (Future-X ·
  diputaciones forales defer per Marcos decision)
- source_url NO add new col · reuse url_pliego + url_expediente existing
- Migration intencionalmente small · resto bloques A→F cada uno migra
  sus cols dedicadas
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "radar_v9_perfect_a_001"
down_revision = "radar_v9_d_indexes_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenders",
        sa.Column("autonomic_id", sa.String(length=255), nullable=True),
    )
    op.create_index(
        "ix_tenders_autonomic_id",
        "tenders",
        ["autonomic_id"],
        unique=False,
        postgresql_where=sa.text("autonomic_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_tenders_autonomic_id", table_name="tenders")
    op.drop_column("tenders", "autonomic_id")
