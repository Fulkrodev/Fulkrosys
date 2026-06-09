"""add_unique_system_nombre_per_project

Revision ID: 8340982461b9
Revises: 7c63d18af556
Create Date: 2026-04-13 02:19:24.313779
"""
from typing import Sequence, Union

from alembic import op


revision: str = '8340982461b9'
down_revision: Union[str, None] = '7c63d18af556'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        'uq_systems_project_id_nombre',
        'systems',
        ['project_id', 'nombre']
    )


def downgrade() -> None:
    op.drop_constraint(
        'uq_systems_project_id_nombre',
        'systems',
        type_='unique'
    )
