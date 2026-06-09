"""san_e_mb3_e_m28_role_drift

ADR-046 v3 SAN-E.MB-3.E:
- NEW table project_role_assignments (granular role per project)
- NEW materialized view mv_drift_summary_10x4 (agregada drift events)

Decision arquitectonica: vista materializada (NO tabla) para drift summary ·
0 duplicacion · refresh on-demand · 1 source of truth retainer_drift_events.

Revision ID: c2d4f6a8b1e3
Revises: b5e9c2a4d8f7
Create Date: 2026-05-08
"""
from typing import Sequence, Union

from alembic import op


revision: str = "c2d4f6a8b1e3"
down_revision: Union[str, None] = "b5e9c2a4d8f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── project_role_assignments ───
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS project_role_assignments (
            id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            project_id          uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            role_code           varchar(64) NOT NULL,
            contact_id          uuid REFERENCES client_contacts(id) ON DELETE SET NULL,
            is_required         boolean NOT NULL DEFAULT true,
            is_cross_compliance boolean NOT NULL DEFAULT false,
            assigned_at         timestamptz,
            assigned_by         varchar(255),
            notes               text,
            created_at          timestamptz NOT NULL DEFAULT now(),
            updated_at          timestamptz,
            deleted_at          timestamptz,
            CONSTRAINT uq_role_assignment_project_role UNIQUE (project_id, role_code)
        );
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_role_assignment_project "
        "ON project_role_assignments (project_id);"
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE "
        "ON project_role_assignments TO fulkro_app"
    )
    op.execute("ALTER TABLE project_role_assignments ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE project_role_assignments FORCE ROW LEVEL SECURITY;")
    op.execute(
        """
        DROP POLICY IF EXISTS project_isolation ON project_role_assignments;
        CREATE POLICY project_isolation ON project_role_assignments
            USING (project_id = current_project_id());
        """
    )
    op.execute(
        """
        DROP TRIGGER IF EXISTS tg_audit_role_assignments ON project_role_assignments;
        CREATE TRIGGER tg_audit_role_assignments
            AFTER INSERT OR UPDATE OR DELETE ON project_role_assignments
            FOR EACH ROW EXECUTE FUNCTION fn_audit_track();
        """
    )

    # ─── mv_drift_summary_10x4 ───
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_drift_summary_10x4;")
    op.execute(
        """
        CREATE MATERIALIZED VIEW mv_drift_summary_10x4 AS
        SELECT
            project_id,
            dimension,
            severidad,
            COUNT(*) FILTER (WHERE estado = 'open')   AS open_count,
            COUNT(*) FILTER (WHERE estado = 'closed') AS closed_count,
            COUNT(*) AS total_count,
            MAX(created_at) AS last_detected
        FROM retainer_drift_events
        WHERE deleted_at IS NULL
        GROUP BY project_id, dimension, severidad;
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_mv_drift_summary "
        "ON mv_drift_summary_10x4 (project_id, dimension, severidad);"
    )
    op.execute(
        "GRANT SELECT ON mv_drift_summary_10x4 TO fulkro_app"
    )
    # Owner = fulkro (superuser) para que _admin_setup en tests pueda REFRESH.
    # En produccion el job M28 jobs.py corre como fulkro_app · necesita
    # SECURITY DEFINER funcion (cableado en MB-7 con maintenance jobs).
    op.execute("ALTER MATERIALIZED VIEW mv_drift_summary_10x4 OWNER TO fulkro;")


def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_drift_summary_10x4;")
    op.execute(
        "DROP TRIGGER IF EXISTS tg_audit_role_assignments ON project_role_assignments;"
    )
    op.execute("DROP POLICY IF EXISTS project_isolation ON project_role_assignments;")
    op.execute("DROP INDEX IF EXISTS ix_role_assignment_project;")
    op.execute("DROP TABLE IF EXISTS project_role_assignments;")
