"""fase_9_0_cleanup_ccn_stic_804_v2017_legacy

Eliminacion de 7 medidas fantasma heredadas de CCN-STIC-804 v2017 que ya
no existen en el RD 311/2022 ENS vigente:

  mp.com.9, mp.if.9, mp.info.9, mp.per.9, mp.s.8, mp.s.9, op.exp.11

Pre-flight (Sub-bloque 0.A Fase 1, sesion 11) verifico cero referencias
activas en dda_entries, obligations, controls. Solo existen 2 refuerzos
legacy huerfanos en ens_reinforcements (mp.info.9 R1, op.exp.11 R1) sin
referencias en dda_entries.refuerzos_aplicados.

Backup: var/backups/fase_9_0_pre_cleanup_20260502_1237.sql
Reporte: progress/session_11/fase_9_0/REPORT_0C.md (Sub-bloque 0.A Fase 1)

Revision ID: c6f5ff65d8be
Revises: f658961972a2
Create Date: 2026-05-02 12:38:47.461361
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text


revision: str = 'c6f5ff65d8be'
down_revision: Union[str, None] = 'f658961972a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


FANTASMA = (
    'mp.com.9', 'mp.if.9', 'mp.info.9', 'mp.per.9',
    'mp.s.8', 'mp.s.9', 'op.exp.11',
)


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Tablas hijas con measure_code (varchar)
    conn.execute(
        text("""
            DELETE FROM ens_measure_refuerzos
            WHERE measure_code = ANY(:codes)
        """),
        {'codes': list(FANTASMA)},
    )
    conn.execute(
        text("""
            DELETE FROM ens_measure_dimensiones
            WHERE measure_code = ANY(:codes)
        """),
        {'codes': list(FANTASMA)},
    )
    conn.execute(
        text("""
            DELETE FROM ens_measure_guias_ccn
            WHERE measure_code = ANY(:codes)
        """),
        {'codes': list(FANTASMA)},
    )

    # 2. ens_reinforcements legacy (FK measure_id UUID)
    conn.execute(
        text("""
            DELETE FROM ens_reinforcements
            WHERE measure_id IN (
                SELECT id FROM ens_measures WHERE codigo = ANY(:codes)
            )
        """),
        {'codes': list(FANTASMA)},
    )

    # 3. ens_measures (parent) - los 7 codigos fantasma
    conn.execute(
        text("""
            DELETE FROM ens_measures
            WHERE codigo = ANY(:codes)
        """),
        {'codes': list(FANTASMA)},
    )


def downgrade() -> None:
    # Rollback requiere restore manual desde backup pre-cleanup:
    #   var/backups/fase_9_0_pre_cleanup_20260502_1237.sql
    # Ver progress/session_11/fase_9_0/REPORT_0C.md (Sub-bloque 0.A Fase 1)
    # Los datos fantasma son v2017 obsoletos; reseed canonico llegara en Fase 2.
    pass
