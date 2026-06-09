"""ENS Radar · Sub-atom I · fix ResultCode rol — data repair participations.

Audit-first OPS-026 reveló: `pipeline.py` mapeaba el rol de cada participación
con `result_code in ("1","2")` — pero los ResultCode CODICE de PLACSP para una
adjudicación son "8"/"9", nunca "1"/"2", y además son transitorios (no se
persisten en BD). Resultado: las 9664 participaciones — que `placsp.py` extrae
EXCLUSIVAMENTE de `<cac:WinningParty>` (es decir, son TODAS adjudicatarios) —
quedaron etiquetadas `licitador`, dejando `ardiendo`/`ardiendo_sostenido`
estructuralmente inalcanzables en el scoring de temperatura.

Esta migración repara los datos existentes: todas las participaciones eran
ganadores mal etiquetados → `rol = 'adjudicatario'`.

El fix de código (`pipeline.py` · `rol = "adjudicatario"` fijo) acompaña esta
migración en el mismo commit.

Downgrade: no-op intencional. El estado previo (`rol='licitador'` universal)
era el bug — revertir a él no tiene sentido semántico y además pisaría
cualquier participación legítimamente creada por runs posteriores al fix.

Revision ID: sane_ens_radar_rol_fix_001
Revises: sane_ens_radar_schema_widen_001
Create Date: 2026-05-14
"""
from alembic import op


revision = "sane_ens_radar_rol_fix_001"
down_revision = "sane_ens_radar_schema_widen_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # fulkro_migrate tiene UPDATE grant directo sobre participations.
    op.execute(
        "UPDATE participations SET rol = 'adjudicatario' "
        "WHERE rol = 'licitador'"
    )


def downgrade() -> None:
    # No-op intencional: el estado previo era el bug (ver docstring).
    pass
