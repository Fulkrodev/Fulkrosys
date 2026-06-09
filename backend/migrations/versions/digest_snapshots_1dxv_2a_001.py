"""digest_snapshots_1dxv_2a_001 · sub-atom 1.D.X.VERIFY commit 2a.

Crea 1 tabla project-scoped para persistir snapshots digest mensuales:
  - cloud_digest_snapshots · persist {compliance_score, gaps_by_severity,
    snapshot_jsonb, triggered_by, generated_at}

Diseño:
  - project_id NOT NULL FK projects(id) ON DELETE CASCADE
  - RLS project-scoped (LECCION-OPS-008 sostenido · pattern m_cloud_connectors B)
  - Index (project_id, generated_at DESC) para query "latest" eficiente
  - triggered_by string: 'celery_monthly' | 'admin_manual' (audit context)
  - snapshot_jsonb almacena resumen completo · UI cliente y admin consumen

Trend MoM (commit 2b cliente) requiere histórico ≥2 snapshots · esto lo permite.

Revision ID: digest_snapshots_1dxv_2a_001
Revises: cloud_connectors_1dx_b_001
Create Date: 2026-05-21
"""
from typing import Sequence, Union

from alembic import op


revision: str = "digest_snapshots_1dxv_2a_001"
down_revision: Union[str, None] = "cloud_connectors_1dx_b_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE cloud_digest_snapshots (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            triggered_by VARCHAR(40) NOT NULL DEFAULT 'celery_monthly',
            triggered_by_user_id UUID,
            compliance_score INTEGER NOT NULL DEFAULT 100,
            open_gaps_total INTEGER NOT NULL DEFAULT 0,
            open_gaps_by_severity JSONB NOT NULL DEFAULT '{}'::jsonb,
            snapshot_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at TIMESTAMPTZ
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_cloud_digest_snapshots_project_generated "
        "ON cloud_digest_snapshots (project_id, generated_at DESC)"
    )
    op.execute(
        "CREATE INDEX ix_cloud_digest_snapshots_triggered_by "
        "ON cloud_digest_snapshots (triggered_by)"
    )
    op.execute("ALTER TABLE cloud_digest_snapshots OWNER TO fulkro_migrate")
    op.execute(
        "ALTER TABLE cloud_digest_snapshots ENABLE ROW LEVEL SECURITY"
    )
    op.execute(
        """
        CREATE POLICY cloud_digest_snapshots_project_isolation
        ON cloud_digest_snapshots
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
        "GRANT SELECT, INSERT, UPDATE, DELETE ON cloud_digest_snapshots "
        "TO fulkro_app"
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION cloud_digest_snapshots_set_updated_at()
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
        CREATE TRIGGER trg_cloud_digest_snapshots_updated_at
        BEFORE UPDATE ON cloud_digest_snapshots
        FOR EACH ROW
        EXECUTE FUNCTION cloud_digest_snapshots_set_updated_at()
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_cloud_digest_snapshots_updated_at "
        "ON cloud_digest_snapshots"
    )
    op.execute(
        "DROP FUNCTION IF EXISTS cloud_digest_snapshots_set_updated_at()"
    )
    op.execute(
        "DROP POLICY IF EXISTS cloud_digest_snapshots_project_isolation "
        "ON cloud_digest_snapshots"
    )
    op.execute("DROP TABLE IF EXISTS cloud_digest_snapshots")
