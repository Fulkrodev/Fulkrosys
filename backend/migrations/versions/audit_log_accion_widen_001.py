"""Sesión 3B-2B.6 CLUSTER 2 Phase 4 · widen audit_log.accion VARCHAR(20) → (60).

Audit log originally diseñado para INSERT/UPDATE/DELETE (≤6 chars). Auditor
portal CLUSTER 2 emits events con namespacing dotado · ej. 'auditor.session.start'
(21 chars) · 'auditor.view.audit_log' (22) · etc · supera límite VARCHAR(20).

Widen a VARCHAR(60) backward-compat · existing rows untouched · hash chain
trigger NO afectado (computes hash from value · agnostic de length).

Revision ID: audit_log_accion_widen_001
Revises: audit_log_rls_001
Create Date: 2026-05-26
"""
from typing import Sequence, Union

from alembic import op


revision: str = "audit_log_accion_widen_001"
down_revision: Union[str, None] = "audit_log_rls_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE audit_log ALTER COLUMN accion TYPE VARCHAR(60)"
    )


def downgrade() -> None:
    # Down: hard-truncate existing values > 20 chars · NO graceful
    # (debería revisarse manual antes ejecutar downgrade)
    op.execute(
        "ALTER TABLE audit_log ALTER COLUMN accion TYPE VARCHAR(20) "
        "USING substring(accion FROM 1 FOR 20)"
    )
