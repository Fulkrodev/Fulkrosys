"""golden_eval_runs_1e1b3e_001 · sub-atom 1.E.1.B.3.E.

NEW table golden_eval_runs · admin trigger + historical runs tracking
para golden datasets eval harness UI `/admin/llm-observability/golden-eval/`.

Justified scope NEW (ADR-025 sostained · 18ª aplicación):
  - llm_interaction_log existing tracks LLM calls (Anthropic API) per agent
  - ai_act_transparency_events tracks AI Act art.50 decisions externalized
  - golden_eval_runs (NEW) tracks regression eval RUNS metadata (NOT
    individual LLM calls · NOT decisions) · scope diferente · NO duplica

Diseño:
  - admin-only platform-global (NO project_id · NO RLS · mismo cement
    m_compliance_monitor)
  - triggered_by user_id audit trail
  - status lifecycle: queued → running → completed | failed
  - regression_score + severity nullable hasta run completes
  - failed_entry_ids JSONB para drill-down
  - metadata JSONB extensibility (cli args · environment · git sha · etc)
  - indexes (agent_name, triggered_at DESC) + (status) para filtering

Revision ID: golden_eval_runs_1e1b3e_001
Revises: ai_act_transparency_1e1b2_001
Create Date: 2026-05-23
"""
from typing import Sequence, Union

from alembic import op


revision: str = "golden_eval_runs_1e1b3e_001"
down_revision: Union[str, None] = "ai_act_transparency_1e1b2_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE golden_eval_runs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            agent_name VARCHAR(64) NOT NULL,
            dataset_version VARCHAR(32) NOT NULL DEFAULT 'v1',
            triggered_by_user_id UUID,
            triggered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            completed_at TIMESTAMPTZ,
            status VARCHAR(20) NOT NULL DEFAULT 'queued',
            regression_score DOUBLE PRECISION,
            severity VARCHAR(20),
            entries_in_dataset INTEGER NOT NULL DEFAULT 0,
            entries_evaluated INTEGER NOT NULL DEFAULT 0,
            entries_passed INTEGER NOT NULL DEFAULT 0,
            entries_failed INTEGER NOT NULL DEFAULT 0,
            failed_entry_ids JSONB,
            error_message TEXT,
            metadata JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at TIMESTAMPTZ
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_golden_eval_runs_agent_triggered "
        "ON golden_eval_runs (agent_name, triggered_at DESC)"
    )
    op.execute(
        "CREATE INDEX ix_golden_eval_runs_status "
        "ON golden_eval_runs (status)"
    )
    op.execute(
        "ALTER TABLE golden_eval_runs OWNER TO fulkro_migrate"
    )
    # Platform-global · admin-only · NO RLS (mismo cement m_compliance_monitor)
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON golden_eval_runs "
        "TO fulkro_app"
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION golden_eval_runs_set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_golden_eval_runs_updated_at
        BEFORE UPDATE ON golden_eval_runs
        FOR EACH ROW
        EXECUTE FUNCTION golden_eval_runs_set_updated_at()
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_golden_eval_runs_updated_at "
        "ON golden_eval_runs"
    )
    op.execute(
        "DROP FUNCTION IF EXISTS golden_eval_runs_set_updated_at()"
    )
    op.execute("DROP INDEX IF EXISTS ix_golden_eval_runs_status")
    op.execute("DROP INDEX IF EXISTS ix_golden_eval_runs_agent_triggered")
    op.execute("DROP TABLE IF EXISTS golden_eval_runs")
