"""cloud_remediation_orchestrator_b35_001 · Bloque 3+5 cloud remediation orchestrator.

Extiende ``cloud_gaps`` table con 4 columns para lifecycle approval workflow +
crea tabla nueva ``cloud_remediation_approval_logs`` para audit trail inmutable
(state transitions · ENAC trazabilidad).

ADR-025 sostained · NO new "RemediationProposal" model · extend CloudGap existing
(audit Phase 0 Bloque 3+5 reveals CloudGap covers 80% proposal entity needs).

ADR-031 ENAC-ready · audit trail per state transition persisted en separate
inmutable log table (NO drop · NO update · solo INSERT).

Diseño:
  - cloud_gaps ALTER additive only (NO drop · NO constraint break)
  - approval_status DEFAULT 'detected' · backfill safe rows existing
  - cloud_remediation_approval_logs nueva con RLS project-scoped via gap JOIN
  - Indexes optimizados (gap_id + timestamp DESC para audit feed)

R23 sostener · RLS via gap.project_id matching app.current_project_id.

Revision ID: cloud_remediation_orchestrator_b35_001
Revises: golden_eval_runs_1e1b3e_001
Create Date: 2026-05-24
"""
from typing import Sequence, Union

from alembic import op


revision: str = "cloud_remediation_orchestrator_b35_001"
down_revision: Union[str, None] = "golden_eval_runs_1e1b3e_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ==================================================================
    # 1. Extend cloud_gaps · 4 nuevas columns lifecycle approval
    # ==================================================================
    op.execute(
        """
        ALTER TABLE cloud_gaps
            ADD COLUMN IF NOT EXISTS approval_status VARCHAR(30)
                NOT NULL DEFAULT 'detected',
            ADD COLUMN IF NOT EXISTS proposed_to_cliente_at TIMESTAMPTZ NULL,
            ADD COLUMN IF NOT EXISTS cliente_approval_at TIMESTAMPTZ NULL,
            ADD COLUMN IF NOT EXISTS cliente_approval_user_id UUID NULL
        """
    )

    # Index per approval_status filtering (cliente UI feed "pending_approval")
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_cloud_gaps_approval_status
            ON cloud_gaps (project_id, approval_status)
        """
    )

    # ==================================================================
    # 2. Crear cloud_remediation_approval_logs · audit trail inmutable
    # ==================================================================
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS cloud_remediation_approval_logs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            gap_id UUID NOT NULL REFERENCES cloud_gaps(id) ON DELETE CASCADE,
            project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            action VARCHAR(40) NOT NULL,
            actor_user_id UUID NULL,
            actor_type VARCHAR(20) NOT NULL,
            notes TEXT NULL,
            metadata_jsonb JSONB NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )

    # Indexes optimizados
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_cloud_remediation_logs_gap
            ON cloud_remediation_approval_logs (gap_id, created_at DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_cloud_remediation_logs_project
            ON cloud_remediation_approval_logs (project_id, created_at DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_cloud_remediation_logs_action
            ON cloud_remediation_approval_logs (action)
        """
    )

    # RLS project-scoped (pattern cloud_connectors existing)
    op.execute("ALTER TABLE cloud_remediation_approval_logs OWNER TO fulkro_migrate")
    op.execute(
        "ALTER TABLE cloud_remediation_approval_logs ENABLE ROW LEVEL SECURITY"
    )
    op.execute(
        """
        CREATE POLICY cloud_remediation_logs_project_isolation
            ON cloud_remediation_approval_logs
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
        """
        GRANT SELECT, INSERT ON cloud_remediation_approval_logs TO fulkro_app
        """
    )


def downgrade() -> None:
    # Drop audit log table primero (FK gap_id depends cloud_gaps)
    op.execute(
        "DROP TABLE IF EXISTS cloud_remediation_approval_logs"
    )

    # Drop nuevas columns cloud_gaps (additive · drop safe si NO rows tienen
    # approval_status distinct de 'detected')
    op.execute(
        "DROP INDEX IF EXISTS ix_cloud_gaps_approval_status"
    )
    op.execute(
        """
        ALTER TABLE cloud_gaps
            DROP COLUMN IF EXISTS cliente_approval_user_id,
            DROP COLUMN IF EXISTS cliente_approval_at,
            DROP COLUMN IF EXISTS proposed_to_cliente_at,
            DROP COLUMN IF EXISTS approval_status
        """
    )
