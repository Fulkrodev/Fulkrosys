"""Drop M8 v4.2 obsolete tables before v5.1 implementation.

Sesion 7 — demolicion controlada del Motor 8 v4.2.

Las 6 tablas v4.2 (las 5 que pidio Marcos + purple_team_results del
addendum M8-A) quedan obsoletas y se reemplazaran por las 5 nuevas
tablas v5.1 (verification_runs, verification_findings,
external_pentester_handoffs, false_positive_patterns,
remediation_retests) en la migration siguiente.

Pre-condicion verificada en Paso 0: las 6 tablas estaban a 0 filas.
No hay perdida de datos reales.

Revision ID: c4e8d2f5a108
Revises: b9d3e6f7a207
Create Date: 2026-04-21 14:00:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "c4e8d2f5a108"
down_revision: Union[str, None] = "b9d3e6f7a207"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Orden inverso de dependencias FK:
# purple_team_results, pentest_decisions, attack_graph_edges,
# attack_graph_nodes, pentest_findings → todas dependen de pentest_runs
_TABLES_TO_DROP = (
    "purple_team_results",
    "pentest_decisions",
    "attack_graph_edges",
    "attack_graph_nodes",
    "pentest_findings",
    "pentest_runs",
)


def upgrade() -> None:
    for table in _TABLES_TO_DROP:
        # IF EXISTS por seguridad ante repeticiones / entornos limpios.
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")


def downgrade() -> None:
    # M8 v4.2 queda obsoleto definitivamente. No hay rollback posible
    # sin la spec v4.2 entera, que no se mantiene en el repositorio.
    raise NotImplementedError(
        "M8 v4.2 tables are permanently replaced by v5.1; "
        "downgrade not supported."
    )
