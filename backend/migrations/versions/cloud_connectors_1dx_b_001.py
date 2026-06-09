"""cloud_connectors_1dx_b_001 · sub-atom 1.D.X.B (cloud connectors unified).

Crea 4 tablas project-scoped para layer cloud-first:
  - cloud_connectors · link M16 ConnectorConfig + cloud metadata
  - cloud_resources · recursos detectados (users · vms · storage · etc)
  - cloud_gaps · diagnostic gap engine results
  - cloud_sync_jobs · tracking sync jobs lifecycle

Diseño:
  - project_id NOT NULL FK projects(id) ON DELETE CASCADE en TODAS las tablas
  - m16_connector_config_id FK ON DELETE SET NULL (NO duplicar OAuth ADR-025)
  - UNIQUE constraints idempotency
  - RLS project-scoped (LECCION-OPS-008 sostenido · pattern departments + live_records)
  - JSONB attributes flexible per resource_type
  - GIN index attributes JSONB para queries fast

R23 sostener · NO global cross-cliente. ADR-014 read-only OAuth.
ADR-025 sostener · reuse M16 ConnectorConfig + token_encryption existing.

Revision ID: cloud_connectors_1dx_b_001
Revises: contacts_dept_fk_1c_f_3_001
Create Date: 2026-05-21
"""
from typing import Sequence, Union

from alembic import op


revision: str = "cloud_connectors_1dx_b_001"
down_revision: Union[str, None] = "contacts_dept_fk_1c_f_3_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_table_with_rls(
    table_name: str,
    create_sql: str,
    extra_indexes: list[str] | None = None,
) -> None:
    """Helper · create table + RLS project-scoped + grants + updated_at trigger."""
    op.execute(create_sql)
    if extra_indexes:
        for idx_sql in extra_indexes:
            op.execute(idx_sql)
    op.execute(f"ALTER TABLE {table_name} OWNER TO fulkro_migrate")
    op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY {table_name}_project_isolation ON {table_name}
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
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table_name} TO fulkro_app"
    )
    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION {table_name}_set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        f"""
        CREATE TRIGGER trg_{table_name}_updated_at
        BEFORE UPDATE ON {table_name}
        FOR EACH ROW
        EXECUTE FUNCTION {table_name}_set_updated_at()
        """
    )


def upgrade() -> None:
    # ============= cloud_connectors =============
    _create_table_with_rls(
        "cloud_connectors",
        """
        CREATE TABLE cloud_connectors (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            provider VARCHAR(40) NOT NULL,
            status VARCHAR(30) NOT NULL DEFAULT 'pending_oauth',
            m16_connector_config_id UUID REFERENCES connector_configs(id) ON DELETE SET NULL,
            scopes VARCHAR(500),
            last_sync_at TIMESTAMPTZ,
            last_sync_resources_count INTEGER NOT NULL DEFAULT 0,
            created_by_user_id UUID,
            revoked_at TIMESTAMPTZ,
            metadata_extra JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at TIMESTAMPTZ,
            CONSTRAINT uq_cloud_connectors_project_provider
                UNIQUE (project_id, provider)
        )
        """,
        [
            "CREATE INDEX ix_cloud_connectors_project_status ON cloud_connectors (project_id, status)",
        ],
    )

    # ============= cloud_resources =============
    _create_table_with_rls(
        "cloud_resources",
        """
        CREATE TABLE cloud_resources (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            connector_id UUID NOT NULL REFERENCES cloud_connectors(id) ON DELETE CASCADE,
            resource_type VARCHAR(60) NOT NULL,
            resource_external_id VARCHAR(255) NOT NULL,
            resource_name VARCHAR(255),
            attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
            checksum VARCHAR(64),
            detected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at TIMESTAMPTZ,
            CONSTRAINT uq_cloud_resources_external_id
                UNIQUE (connector_id, resource_external_id, resource_type)
        )
        """,
        [
            "CREATE INDEX ix_cloud_resources_connector_type ON cloud_resources (connector_id, resource_type)",
            "CREATE INDEX ix_cloud_resources_project ON cloud_resources (project_id)",
            "CREATE INDEX ix_cloud_resources_attributes_gin ON cloud_resources USING gin (attributes)",
        ],
    )

    # ============= cloud_gaps =============
    _create_table_with_rls(
        "cloud_gaps",
        """
        CREATE TABLE cloud_gaps (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            connector_id UUID REFERENCES cloud_connectors(id) ON DELETE SET NULL,
            gap_type VARCHAR(40) NOT NULL,
            severity VARCHAR(20) NOT NULL,
            ens_measure_code VARCHAR(50) NOT NULL,
            title VARCHAR(255) NOT NULL,
            explanation_es TEXT,
            suggested_action TEXT,
            estimated_effort_days INTEGER,
            auto_fixable BOOLEAN NOT NULL DEFAULT FALSE,
            cliente_can_see BOOLEAN NOT NULL DEFAULT TRUE,
            resolved_at TIMESTAMPTZ,
            resolved_by_user_id UUID,
            resolution_note TEXT,
            evidence_link_id UUID,
            detected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            raw_evidence JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at TIMESTAMPTZ
        )
        """,
        [
            "CREATE INDEX ix_cloud_gaps_project_severity ON cloud_gaps (project_id, severity)",
            "CREATE INDEX ix_cloud_gaps_measure ON cloud_gaps (ens_measure_code)",
            "CREATE INDEX ix_cloud_gaps_resolved ON cloud_gaps (project_id, resolved_at)",
        ],
    )

    # ============= cloud_sync_jobs =============
    _create_table_with_rls(
        "cloud_sync_jobs",
        """
        CREATE TABLE cloud_sync_jobs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            connector_id UUID NOT NULL REFERENCES cloud_connectors(id) ON DELETE CASCADE,
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            completed_at TIMESTAMPTZ,
            resources_count INTEGER NOT NULL DEFAULT 0,
            errors_jsonb JSONB,
            triggered_by VARCHAR(40) NOT NULL DEFAULT 'manual',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at TIMESTAMPTZ
        )
        """,
        [
            "CREATE INDEX ix_cloud_sync_jobs_connector ON cloud_sync_jobs (connector_id, started_at)",
            "CREATE INDEX ix_cloud_sync_jobs_status ON cloud_sync_jobs (status)",
        ],
    )


def _drop_table_with_rls(table_name: str) -> None:
    op.execute(f"DROP TRIGGER IF EXISTS trg_{table_name}_updated_at ON {table_name}")
    op.execute(f"DROP FUNCTION IF EXISTS {table_name}_set_updated_at()")
    op.execute(f"DROP POLICY IF EXISTS {table_name}_project_isolation ON {table_name}")
    op.execute(f"DROP TABLE IF EXISTS {table_name}")


def downgrade() -> None:
    _drop_table_with_rls("cloud_sync_jobs")
    _drop_table_with_rls("cloud_gaps")
    _drop_table_with_rls("cloud_resources")
    _drop_table_with_rls("cloud_connectors")
