"""san_e_mb6_atom2_dpc_anual_setup

Revision ID: 9f4153c49d44
Revises: bc70b4b0d8d0
Create Date: 2026-05-11

SAN-E v3.MB-6 atom 2 · DPC anual (Declaración Protección Continuidad)
CCN-STIC 806 · art.25 RD 311/2022 · anniversary-based annual workflow.

3 cambios concentrados (decisión Marcos Q1.A + Consideration A):

1. WIDEN ck_basic_declarations_type · add 'dpc_anual' al enum permitido.
   Pre-atom-2: ('initial', 'renewal', 'commitment_pre_certification')
   Post-atom-2: + 'dpc_anual'

2. ADD basic_declarations.anniversary_year (Integer · nullable)
   Permite múltiples DPC anuales per project · 1 por anniversary_year.
   NULL para declaration_type != 'dpc_anual' (initial/commitment NO usan year).

3. UNIQUE partial constraint (project_id, anniversary_year) WHERE
   declaration_type='dpc_anual' · evita multi-year stacking duplicate
   (Consideration A · audit findings).

4. WIDEN ck_alert_queue_category · add 'dpc_due' al enum permitido.
   Pre-atom-2: 12 categories (bienal_art31 · renewal_due · audit_due · etc.)
   Post-atom-2: + 'dpc_due' para Celery anniversary task alerts.

Reversible · downgrade restaura enums + drops cols + constraint.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '9f4153c49d44'
down_revision: Union[str, None] = 'bc70b4b0d8d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. WIDEN ck_basic_declarations_type · add 'dpc_anual'
    op.drop_constraint(
        'ck_basic_declarations_type',
        'basic_declarations',
        type_='check',
    )
    op.create_check_constraint(
        'ck_basic_declarations_type',
        'basic_declarations',
        "declaration_type IN ('initial', 'renewal', "
        "'commitment_pre_certification', 'dpc_anual')",
    )

    # 2. ADD anniversary_year column (Integer · nullable · solo DPC anual)
    op.add_column(
        'basic_declarations',
        sa.Column('anniversary_year', sa.Integer(), nullable=True),
    )

    # 3. UNIQUE partial (project_id, anniversary_year) WHERE declaration_type='dpc_anual'
    op.create_index(
        'uq_basic_declarations_dpc_anniversary',
        'basic_declarations',
        ['project_id', 'anniversary_year'],
        unique=True,
        postgresql_where=sa.text("declaration_type = 'dpc_anual'"),
    )

    # 4. WIDEN ck_alert_queue_category · add 'dpc_due'
    op.drop_constraint(
        'ck_alert_queue_category',
        'alert_queue',
        type_='check',
    )
    op.create_check_constraint(
        'ck_alert_queue_category',
        'alert_queue',
        "category IN ('bienal_art31', 'payment_overdue_aapp', "
        "'client_inactivity', 'evidence_stale', 'retainer_overdue', "
        "'milestone_due', 'workflow_blocked', 'audit_due', 'rgpd_72h', "
        "'contract_milestone', 'renewal_due', 'dpc_due', 'other')",
    )


def downgrade() -> None:
    # Reverse order
    op.drop_constraint(
        'ck_alert_queue_category',
        'alert_queue',
        type_='check',
    )
    op.create_check_constraint(
        'ck_alert_queue_category',
        'alert_queue',
        "category IN ('bienal_art31', 'payment_overdue_aapp', "
        "'client_inactivity', 'evidence_stale', 'retainer_overdue', "
        "'milestone_due', 'workflow_blocked', 'audit_due', 'rgpd_72h', "
        "'contract_milestone', 'renewal_due', 'other')",
    )

    op.drop_index(
        'uq_basic_declarations_dpc_anniversary',
        table_name='basic_declarations',
    )
    op.drop_column('basic_declarations', 'anniversary_year')

    op.drop_constraint(
        'ck_basic_declarations_type',
        'basic_declarations',
        type_='check',
    )
    op.create_check_constraint(
        'ck_basic_declarations_type',
        'basic_declarations',
        "declaration_type IN ('initial', 'renewal', "
        "'commitment_pre_certification')",
    )
