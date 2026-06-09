"""Corrective: CHECK constraints for enum columns + NUMERIC accumulated columns.

Resolves TODO-1 (additional enum constraints) and TODO-3 (INTEGER → NUMERIC).

- Adds CHECK constraints for all remaining VARCHAR enum columns in MAGERIT tables
- Changes accumulated_d/i/c/a/t from INTEGER to NUMERIC(10,4) for quantitative precision

Revision ID: 96ac860fe680
Revises: f7461c35f119
Create Date: 2026-04-12
"""
from typing import Sequence, Union

from alembic import op

revision: str = '96ac860fe680'
down_revision: Union[str, None] = 'f7461c35f119'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- TODO-1 extension: CHECK constraints for remaining enum columns ---
    # Using op.execute with raw SQL to avoid silent failures from op.create_check_constraint

    # magerit_analysis.status
    op.execute(
        """ALTER TABLE magerit_analysis
        ADD CONSTRAINT ck_analysis_status
        CHECK (status IN ('draft', 'in_progress', 'completed', 'approved'))"""
    )

    # magerit_safeguard_deployment.status
    op.execute(
        """ALTER TABLE magerit_safeguard_deployment
        ADD CONSTRAINT ck_safeguard_deployment_status
        CHECK (status IN ('planned', 'partial', 'deployed', 'verified'))"""
    )

    # magerit_safeguard_deployment.effect_type
    op.execute(
        """ALTER TABLE magerit_safeguard_deployment
        ADD CONSTRAINT ck_safeguard_effect_type
        CHECK (effect_type IN ('preventive', 'palliative', 'both'))"""
    )

    # magerit_treatment_plan.treatment
    op.execute(
        """ALTER TABLE magerit_treatment_plan
        ADD CONSTRAINT ck_treatment_plan_treatment
        CHECK (treatment IN ('mitigar', 'transferir', 'aceptar', 'eliminar'))"""
    )

    # magerit_treatment_plan.status
    op.execute(
        """ALTER TABLE magerit_treatment_plan
        ADD CONSTRAINT ck_treatment_plan_status
        CHECK (status IN ('pending', 'in_progress', 'completed'))"""
    )

    # magerit_risk_calculation.dimension
    op.execute(
        """ALTER TABLE magerit_risk_calculation
        ADD CONSTRAINT ck_risk_calculation_dimension
        CHECK (dimension IN ('D', 'I', 'C', 'A', 'T'))"""
    )

    # --- TODO-3: Change accumulated_* from INTEGER to NUMERIC(10,4) ---
    for col in ('accumulated_d', 'accumulated_i', 'accumulated_c', 'accumulated_a', 'accumulated_t'):
        op.execute(
            f"""ALTER TABLE magerit_assets
            ALTER COLUMN {col} TYPE NUMERIC(10, 4)
            USING {col}::NUMERIC(10, 4)"""
        )


def downgrade() -> None:
    # Revert NUMERIC back to INTEGER
    for col in ('accumulated_d', 'accumulated_i', 'accumulated_c', 'accumulated_a', 'accumulated_t'):
        op.execute(
            f"""ALTER TABLE magerit_assets
            ALTER COLUMN {col} TYPE INTEGER
            USING ROUND({col})::INTEGER"""
        )

    # Drop CHECK constraints
    op.execute('ALTER TABLE magerit_risk_calculation DROP CONSTRAINT ck_risk_calculation_dimension')
    op.execute('ALTER TABLE magerit_treatment_plan DROP CONSTRAINT ck_treatment_plan_status')
    op.execute('ALTER TABLE magerit_treatment_plan DROP CONSTRAINT ck_treatment_plan_treatment')
    op.execute('ALTER TABLE magerit_safeguard_deployment DROP CONSTRAINT ck_safeguard_effect_type')
    op.execute('ALTER TABLE magerit_safeguard_deployment DROP CONSTRAINT ck_safeguard_deployment_status')
    op.execute('ALTER TABLE magerit_analysis DROP CONSTRAINT ck_analysis_status')
