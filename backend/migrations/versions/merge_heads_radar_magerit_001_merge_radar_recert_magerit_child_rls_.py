"""merge radar_recert + magerit child rls heads

Une las 2 cabezas reales de Alembic (verificadas con `alembic heads`) en una
sola, para que `alembic upgrade head` sea inequívoco en un despliegue limpio
(Hetzner). Merge puro: sin DDL.

NOTA (deuda restante · Future-1.E.radar.alembic-version-num-widen): un upgrade
limpio sobre BD nueva ADEMÁS requiere ensanchar `alembic_version.version_num` a
>=33, porque varios revision id (p.ej. `sub_atom_5b_magerit_child_rls_001` y
`remediation_enhancement_b35_e_001`, 33 chars) superan el VARCHAR(32) por
defecto de Alembic. El merge resuelve la ambigüedad de cabezas, no el ancho.

Revision ID: merge_heads_radar_magerit_001
Revises: radar_recert_001, sub_atom_5b_magerit_child_rls_001
Create Date: 2026-05-28 23:00:06.817243
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'merge_heads_radar_magerit_001'
down_revision: Union[str, None] = ('radar_recert_001', 'sub_atom_5b_magerit_child_rls_001')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
