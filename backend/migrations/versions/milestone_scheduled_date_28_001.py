"""#28 Ola8: contract_milestones.scheduled_date (calendario de pagos)

Revision ID: milestone_scheduled_date_28_001
Revises: annual_review_e4_001
Create Date: 2026-06-05

Anade la fecha prevista de cobro/factura por hito (el enum VALID_BILLING_TRIGGERS
ya contemplaba 'scheduled_date' pero faltaba la columna). Permite el calendario
de pagos (cliente ve que toca pagar y cuando). Columna additive nullable · no
rompe los hitos disparados por phase_complete existentes.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "milestone_scheduled_date_28_001"
down_revision: Union[str, None] = "annual_review_e4_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "contract_milestones",
        sa.Column("scheduled_date", sa.Date(), nullable=True),
    )
    op.create_index(
        "ix_contract_milestones_scheduled_date",
        "contract_milestones", ["scheduled_date"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_contract_milestones_scheduled_date",
        table_name="contract_milestones",
    )
    op.drop_column("contract_milestones", "scheduled_date")
