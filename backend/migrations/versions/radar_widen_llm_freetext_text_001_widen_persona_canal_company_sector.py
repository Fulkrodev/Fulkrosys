"""radar: widen LLM free-text columns -> Text (persona_contacto + canal + company sector)

Segundo barrido del mismo patrón que `radar_widen_sector_text_001`: columnas
`String(N)` que reciben TEXTO LIBRE del LLM (o gemelas semánticas de una que ya
desbordó) y que quedaban como deuda esperando el siguiente crash.

Crash de raíz que motivó este barrido (run a3897135, paso `dossier`):
  - radar_leads.persona_contacto_sugerida  VARCHAR(200) → Text
      El dossier LLM (sonnet) devuelve el rol a contactar en PROSA
      ("Director de Operaciones España o Responsable de Compliance/Calidad...
      con poder decisorio en cumplimiento normativo para contratos públicos",
      222 chars en el lead 2103 Elsevier B.V.) → write-back crudo en
      pipeline.py:1171/1212 → StringDataRightTruncation → pipeline.failed.

Barridas en el mismo ALTER (mismo patrón / consistencia):
  - radar_leads.canal_sugerido           VARCHAR(50)  → Text
      El prompt pide enum (email/linkedin/llamada/presencial) pero el campo NO
      está constreñido; el LLM puede devolver prosa → riesgo latente idéntico.
  - companies.sector                     VARCHAR(200) → Text
      Gemela de tenders.sector (ya Text en radar_widen_sector_text_001). Dejarla
      en String(200) era la misma inconsistencia esperando a morder.

Campo de texto libre LLM = Text, nunca String(N) arbitrario. Cambio no
destructivo (solo ensancha). El ORM (db/models.py) ya quedó alineado a Text.

NOTA despliegue limpio (Hetzner): hereda la misma deuda
`Future-1.E.radar.alembic-version-num-widen` que la migración de sector. En el
entorno dev actual el cambio se aplicó por DDL directo (la BD no está al head de
scripts por el tangle multi-head documentado); este fichero es el artefacto
reproducible para deploy limpio.

Revision ID: radar_widen_llm_freetext_text_001
Revises: radar_widen_sector_text_001
Create Date: 2026-05-30 14:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'radar_widen_llm_freetext_text_001'
down_revision: Union[str, None] = 'radar_widen_sector_text_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'radar_leads', 'persona_contacto_sugerida',
        existing_type=sa.String(length=200),
        type_=sa.Text(),
        existing_nullable=True,
    )
    op.alter_column(
        'radar_leads', 'canal_sugerido',
        existing_type=sa.String(length=50),
        type_=sa.Text(),
        existing_nullable=True,
    )
    op.alter_column(
        'companies', 'sector',
        existing_type=sa.String(length=200),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    # Reversión a VARCHAR — USING LEFT(...) explícito evita el error de cast
    # text->varchar(N) con datos preexistentes que excedan la longitud.
    op.alter_column(
        'companies', 'sector',
        existing_type=sa.Text(),
        type_=sa.String(length=200),
        existing_nullable=True,
        postgresql_using='LEFT(sector, 200)',
    )
    op.alter_column(
        'radar_leads', 'canal_sugerido',
        existing_type=sa.Text(),
        type_=sa.String(length=50),
        existing_nullable=True,
        postgresql_using='LEFT(canal_sugerido, 50)',
    )
    op.alter_column(
        'radar_leads', 'persona_contacto_sugerida',
        existing_type=sa.Text(),
        type_=sa.String(length=200),
        existing_nullable=True,
        postgresql_using='LEFT(persona_contacto_sugerida, 200)',
    )
