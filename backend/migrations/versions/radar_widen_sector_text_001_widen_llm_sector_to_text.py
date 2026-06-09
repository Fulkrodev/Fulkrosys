"""radar: widen LLM free-text sector columns String(50) -> Text

Fix de raíz del crash del pipeline `run-radar --full` (paso extract /
ens_combiner): el clasificador LLM de tratamiento de datos (haiku) devuelve
`sector_sugerido` en TEXTO LIBRE (p.ej. "Sector III - Servicios de Consultoría
y Selección de Personal", 61 chars), que desbordaba las dos columnas que lo
reciben, ambas VARCHAR(50):

  - data_treatment_cache.sector_sugerido  (persistido en get_or_classify_data_treatment)
  - tenders.sector                        (pipeline.py: tender.sector = combined.sector)

→ psycopg2 StringDataRightTruncation → PendingRollbackError → pipeline.failed.

Ambas pasan a Text (igual que `motivo`, `inference_reasoning`, `pliego_excerpt`):
campo de texto libre LLM = Text, nunca String(N) arbitrario. Cambio no
destructivo (solo ensancha). El ORM (db/models.py) ya quedó alineado a Text.

NOTA despliegue limpio (Hetzner): este merge/upgrade hereda la deuda
`Future-1.E.radar.alembic-version-num-widen` (alembic_version.version_num
VARCHAR(32) debe ensancharse a >=33 por revision ids largos preexistentes).
En el entorno dev actual el cambio se aplicó por DDL directo porque la BD no
está al head de scripts (3 filas alembic_version vs head de merge); este
fichero es el artefacto reproducible para deploy limpio.

Revision ID: radar_widen_sector_text_001
Revises: merge_heads_radar_magerit_001
Create Date: 2026-05-29 09:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'radar_widen_sector_text_001'
down_revision: Union[str, None] = 'merge_heads_radar_magerit_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'data_treatment_cache', 'sector_sugerido',
        existing_type=sa.String(length=50),
        type_=sa.Text(),
        existing_nullable=True,
    )
    op.alter_column(
        'tenders', 'sector',
        existing_type=sa.String(length=50),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    # Reversión a VARCHAR(50) — truncaría valores largos preexistentes; USING
    # explícito evita el error de cast text->varchar(50) con datos que excedan.
    op.alter_column(
        'tenders', 'sector',
        existing_type=sa.Text(),
        type_=sa.String(length=50),
        existing_nullable=True,
        postgresql_using='LEFT(sector, 50)',
    )
    op.alter_column(
        'data_treatment_cache', 'sector_sugerido',
        existing_type=sa.Text(),
        type_=sa.String(length=50),
        existing_nullable=True,
        postgresql_using='LEFT(sector_sugerido, 50)',
    )
