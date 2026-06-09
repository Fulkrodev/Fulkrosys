"""Add MAGERIT risk matrix and calculation_mode.

- New table magerit_risk_matrix with 25 official MAGERIT v3 entries
  (Libro III, sec 2.1 "Análisis mediante tablas", p.7)
- New column magerit_analysis.calculation_mode (qualitative/quantitative/hybrid)
- Change magerit_threat_assessment.probability from INTEGER to VARCHAR(2)

Revision ID: f7461c35f119
Revises: af85d71528af
Create Date: 2026-04-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'f7461c35f119'
down_revision: Union[str, None] = 'af85d71528af'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Official MAGERIT v3 risk matrix from Libro III, sec 2.1, p.7
# Verified against PDF extraction with pdfplumber on 2026-04-11
RISK_MATRIX = [
    # (impact_level, probability_level, risk_level)
    ("MA", "MB", "A"),  ("MA", "B", "MA"), ("MA", "M", "MA"), ("MA", "A", "MA"), ("MA", "MA", "MA"),
    ("A",  "MB", "M"),  ("A",  "B", "A"),  ("A",  "M", "A"),  ("A",  "A", "MA"), ("A",  "MA", "MA"),
    ("M",  "MB", "B"),  ("M",  "B", "M"),  ("M",  "M", "M"),  ("M",  "A", "A"),  ("M",  "MA", "A"),
    ("B",  "MB", "MB"), ("B",  "B", "B"),  ("B",  "M", "B"),  ("B",  "A", "M"),  ("B",  "MA", "M"),
    ("MB", "MB", "MB"), ("MB", "B", "MB"), ("MB", "M", "MB"), ("MB", "A", "B"),  ("MB", "MA", "B"),
]


def upgrade() -> None:
    # 1. Create risk matrix table
    op.create_table(
        'magerit_risk_matrix',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('impact_level', sa.String(2), nullable=False),
        sa.Column('probability_level', sa.String(2), nullable=False),
        sa.Column('risk_level', sa.String(2), nullable=False),
        sa.UniqueConstraint('impact_level', 'probability_level', name='uq_risk_matrix_impact_prob'),
    )

    # Precarga las 25 filas de la matriz oficial
    risk_matrix_table = sa.table(
        'magerit_risk_matrix',
        sa.column('impact_level', sa.String),
        sa.column('probability_level', sa.String),
        sa.column('risk_level', sa.String),
    )
    op.bulk_insert(risk_matrix_table, [
        {"impact_level": imp, "probability_level": prob, "risk_level": risk}
        for imp, prob, risk in RISK_MATRIX
    ])

    # 2. Add calculation_mode to magerit_analysis
    op.add_column(
        'magerit_analysis',
        sa.Column(
            'calculation_mode',
            sa.String(20),
            nullable=False,
            server_default='qualitative',
        ),
    )
    op.create_check_constraint(
        'ck_analysis_calculation_mode',
        'magerit_analysis',
        "calculation_mode IN ('qualitative', 'quantitative', 'hybrid')",
    )

    # 3. Change probability column type from INTEGER to VARCHAR(2)
    # Drop old column and recreate (safest for type change)
    op.drop_column('magerit_threat_assessment', 'probability')
    op.add_column(
        'magerit_threat_assessment',
        sa.Column('probability', sa.String(2), nullable=False, server_default='M'),
    )
    op.create_check_constraint(
        'ck_threat_probability_level',
        'magerit_threat_assessment',
        "probability IN ('MB', 'B', 'M', 'A', 'MA')",
    )


def downgrade() -> None:
    op.drop_constraint('ck_threat_probability_level', 'magerit_threat_assessment')
    op.drop_column('magerit_threat_assessment', 'probability')
    op.add_column('magerit_threat_assessment', sa.Column('probability', sa.Integer(), nullable=False, server_default='3'))

    op.drop_constraint('ck_analysis_calculation_mode', 'magerit_analysis')
    op.drop_column('magerit_analysis', 'calculation_mode')

    op.drop_table('magerit_risk_matrix')
