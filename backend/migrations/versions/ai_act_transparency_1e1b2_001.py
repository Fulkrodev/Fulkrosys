"""ai_act_transparency_1e1b2_001 · sub-atom 1.E.1.B.2.

NEW table ai_act_transparency_events para AI Act art.50 compliance
(transparency obligations · audit trail decisiones IA publicadas).

Justified scope NEW (post 1.E.1.A.1 audit recalibration matrix · #5 NEW
genuine · NO infraestructura existing · ADR-025 sostenido):
  - llm_interaction_log existing tracks calls técnicos (tokens · cost)
  - ai_act_transparency_events tracks decisiones IA externalizadas
    (deliverable_generated · proposal_drafted · contract_clause · etc)
    con purpose statement cliente-readable + artifact link
  - retention_until computed: created_at + 6 years per AI Act guidance

Diseño:
  - project_id NOT NULL FK projects(id) ON DELETE CASCADE
  - client_id nullable FK clients(id) ON DELETE SET NULL (cross-project
    cliente queries · evita orphan rows si client deleted)
  - event_type · llm_provider · llm_model · agent_name · purpose strings
  - artifact_type + artifact_id optional (link deliverable/proposal/etc)
  - metadata JSONB para extensibility
  - retention_until Date NOT NULL (defensible audit retention boundary)
  - 3 indexes: (project_id, created_at DESC) · (client_id, created_at
    DESC) · event_type
  - RLS project-scoped (cliente NO ve cross-project · admin full access)

Revision ID: ai_act_transparency_1e1b2_001
Revises: llm_log_cached_tokens_1e1b1_001
Create Date: 2026-05-22
"""
from typing import Sequence, Union

from alembic import op


revision: str = "ai_act_transparency_1e1b2_001"
down_revision: Union[str, None] = "llm_log_cached_tokens_1e1b1_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE ai_act_transparency_events (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            client_id UUID REFERENCES clients(id) ON DELETE SET NULL,
            event_type VARCHAR(64) NOT NULL,
            llm_provider VARCHAR(32) NOT NULL,
            llm_model VARCHAR(128) NOT NULL,
            agent_name VARCHAR(64) NOT NULL,
            artifact_type VARCHAR(64),
            artifact_id UUID,
            purpose VARCHAR(256) NOT NULL,
            metadata JSONB,
            retention_until DATE NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at TIMESTAMPTZ
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_ai_act_transparency_project_created "
        "ON ai_act_transparency_events (project_id, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX ix_ai_act_transparency_client_created "
        "ON ai_act_transparency_events (client_id, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX ix_ai_act_transparency_event_type "
        "ON ai_act_transparency_events (event_type)"
    )
    op.execute(
        "ALTER TABLE ai_act_transparency_events OWNER TO fulkro_migrate"
    )
    op.execute(
        "ALTER TABLE ai_act_transparency_events ENABLE ROW LEVEL SECURITY"
    )
    op.execute(
        """
        CREATE POLICY ai_act_transparency_project_isolation
        ON ai_act_transparency_events
        FOR ALL TO fulkro_app
        USING (
            project_id::text = current_setting('app.current_project_id', true)
        )
        WITH CHECK (
            project_id::text = current_setting('app.current_project_id', true)
        )
        """
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON ai_act_transparency_events "
        "TO fulkro_app"
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION ai_act_transparency_set_updated_at()
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
        CREATE TRIGGER trg_ai_act_transparency_updated_at
        BEFORE UPDATE ON ai_act_transparency_events
        FOR EACH ROW
        EXECUTE FUNCTION ai_act_transparency_set_updated_at()
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_ai_act_transparency_updated_at "
        "ON ai_act_transparency_events"
    )
    op.execute(
        "DROP FUNCTION IF EXISTS ai_act_transparency_set_updated_at()"
    )
    op.execute(
        "DROP POLICY IF EXISTS ai_act_transparency_project_isolation "
        "ON ai_act_transparency_events"
    )
    op.execute("DROP INDEX IF EXISTS ix_ai_act_transparency_event_type")
    op.execute("DROP INDEX IF EXISTS ix_ai_act_transparency_client_created")
    op.execute("DROP INDEX IF EXISTS ix_ai_act_transparency_project_created")
    op.execute("DROP TABLE IF EXISTS ai_act_transparency_events")
