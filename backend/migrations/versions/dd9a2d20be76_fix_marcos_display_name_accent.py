"""fix_marcos_display_name_accent

Corrige el typo histórico en el seed de marcos@fulkro.es: el display_name
canónico es "Marcos Mata García" (con tilde). La migration original
a7f1e4b8c2d5 lo introdujo sin tilde y se mantiene intacta por
auditabilidad. Esta migration aplica un UPDATE idempotente para que
cualquier despliegue contra una BD limpia (alembic upgrade head desde
cero) tenga el valor correcto.

Revision ID: dd9a2d20be76
Revises: b7e4c9f2d834
Create Date: 2026-04-26 20:08:02.538238
"""
from typing import Sequence, Union

from alembic import op


revision: str = "dd9a2d20be76"
down_revision: Union[str, None] = "b7e4c9f2d834"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "UPDATE auth_users "
        "SET display_name = 'Marcos Mata García' "
        "WHERE email = 'marcos@fulkro.es' "
        "AND display_name = 'Marcos Mata Garcia'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE auth_users "
        "SET display_name = 'Marcos Mata Garcia' "
        "WHERE email = 'marcos@fulkro.es' "
        "AND display_name = 'Marcos Mata García'"
    )
