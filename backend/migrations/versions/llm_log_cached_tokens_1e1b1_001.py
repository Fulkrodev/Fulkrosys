"""llm_log_cached_tokens_1e1b1_001 · sub-atom 1.E.1.B.1.

ALTER llm_interaction_log ADD cached_input_tokens column.

Único delta funcional real post 1.E.1.A.1 audit-first recalibration
(Opción A approved · sostiene ADR-025 firmísimo).

Diseño:
  - cached_input_tokens BIGINT NOT NULL DEFAULT 0
  - Existing rows backfilled con 0 vía server_default
  - Index agregado para queries cache_stats efficient
  - Reversible · downgrade DROP column + index

Anthropic prompt caching tracking habilita:
  - hit_rate = cached / (prompt_tokens + cached_input_tokens) per agent
  - cost forecasting con descuento cached (cached ~90% cheaper Anthropic)
  - regression detection cuando cached drop tras prompt change

Revision ID: llm_log_cached_tokens_1e1b1_001
Revises: digest_snapshots_1dxv_2a_001
Create Date: 2026-05-22
"""
from typing import Sequence, Union

from alembic import op


revision: str = "llm_log_cached_tokens_1e1b1_001"
down_revision: Union[str, None] = "digest_snapshots_1dxv_2a_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE llm_interaction_log "
        "ADD COLUMN cached_input_tokens BIGINT NOT NULL DEFAULT 0"
    )
    op.execute(
        "CREATE INDEX ix_llm_interaction_log_cached_input_tokens "
        "ON llm_interaction_log (cached_input_tokens)"
    )


def downgrade() -> None:
    op.execute(
        "DROP INDEX IF EXISTS ix_llm_interaction_log_cached_input_tokens"
    )
    op.execute(
        "ALTER TABLE llm_interaction_log DROP COLUMN IF EXISTS cached_input_tokens"
    )
