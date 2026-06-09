"""Sub-atom Phase 6 · audit_log auditor portal event_type canonical namespace.

Sesión 3B-2B.6 CLUSTER 2 Phase 6 · formaliza naming convention auditor portal
acciones via DB COMMENT (NO CHECK constraint · backward-compat preserved).

Decisión arquitectural (Phase 0 audit Phase 6.0):
- audit_log.accion VARCHAR(60) post Sub-atom 5.A widen migration
  (audit_log_accion_widen_001)
- Cross-motor existing acciones varían enormemente ("marked" · "approve" ·
  "evidence.upload" · "client_review.ok" · etc) · CHECK constraint whitelist
  rompería 13 tracked tables fn_audit_track + existing emit sites
- Solución: canonical namespace enforcement at code level via
  ``backend/app/motors/m09_audit_prep/audit_events.py`` constants module
  + COMMENT ON COLUMN documentando convention
- Hash chain inviolable R6 preserved (trigger fn_audit_log_hash_chain NO afectado)

Revision ID: audit_log_auditor_events_001
Revises: audit_log_accion_widen_001
Create Date: 2026-05-26
"""
from typing import Sequence, Union

from alembic import op


revision: str = "audit_log_auditor_events_001"
down_revision: Union[str, None] = "audit_log_accion_widen_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Document canonical namespace via COMMENT ON COLUMN.

    Convention enforcement at code level (audit_events.py constants).
    Hash chain trigger NO afectado.
    """
    op.execute(
        "COMMENT ON COLUMN audit_log.accion IS "
        "'Action verb. Auditor portal canonical namespace (CLUSTER 2 Phase 6): "
        "auditor.session.* (start/refresh/end) · auditor.view.* (9 sections) · "
        "auditor.download.* (9 asset types) · auditor.search.* (evidence + meta). "
        "Pre-CLUSTER 2 legacy values (e.g. ''marked'' · ''approve'' · "
        "''evidence.upload'') remain backward-compat valid. See "
        "backend/app/motors/m09_audit_prep/audit_events.py for constants.'"
    )


def downgrade() -> None:
    op.execute("COMMENT ON COLUMN audit_log.accion IS NULL")
