"""m21-b: add report_data and report_paths to diagnosis_runs

Revision ID: 1b32bac44237
Revises: e09fe52908a7
Create Date: 2026-04-16 20:49:39.460289
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '1b32bac44237'
down_revision: Union[str, None] = 'e09fe52908a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('diagnosis_runs', sa.Column('report_data', sa.dialects.postgresql.JSONB(), nullable=True))
    op.add_column('diagnosis_runs', sa.Column('report_docx_path', sa.String(500), nullable=True))
    op.add_column('diagnosis_runs', sa.Column('report_pdf_path', sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column('diagnosis_runs', 'report_pdf_path')
    op.drop_column('diagnosis_runs', 'report_docx_path')
    op.drop_column('diagnosis_runs', 'report_data')
