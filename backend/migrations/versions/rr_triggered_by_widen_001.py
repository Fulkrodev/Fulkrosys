"""widen chk_rr_triggered_by con 'remediation_chain' (IMPL-5 retest encadenado)

El re-test quirúrgico que se dispara AUTOMÁTICAMENTE tras una remediación exitosa
(m_remediation → m08) es una categoría de disparo distinta de las existentes
('client_portal', 'marcos', 'scheduled'). Para que la traza que certifica el
auditor ENAC sea precisa (por qué corrió el re-test), añadimos el valor canónico
'remediation_chain'. Aditiva y reversible.

Revision ID: rr_triggered_by_widen_001
Revises: signable_type_widen_001
Create Date: 2026-06-14
"""
from alembic import op

revision = "rr_triggered_by_widen_001"
down_revision = "signable_type_widen_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "chk_rr_triggered_by", "remediation_retests", type_="check",
    )
    op.create_check_constraint(
        "chk_rr_triggered_by", "remediation_retests",
        "triggered_by IS NULL OR triggered_by IN "
        "('client_portal','marcos','scheduled','remediation_chain')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "chk_rr_triggered_by", "remediation_retests", type_="check",
    )
    op.create_check_constraint(
        "chk_rr_triggered_by", "remediation_retests",
        "triggered_by IS NULL OR triggered_by IN "
        "('client_portal','marcos','scheduled')",
    )
