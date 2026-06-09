"""san_e_mb3_b_m14_providers

ADR-046 v3 SAN-E.MB-3.B: tablas providers + provider_c002 con auto-detect
cross-compliance (ENS Art 18 + GDPR Art 28 + NIS2 cuando aplica).

Patron heredado MB-3.A: idempotente · RLS project_isolation · audit trigger ·
GRANT runtime fulkro_app.

Revision ID: f4b2c8d1e7a3
Revises: e3a01a7b2c34
Create Date: 2026-05-08
"""
from typing import Sequence, Union

from alembic import op


revision: str = "f4b2c8d1e7a3"
down_revision: Union[str, None] = "e3a01a7b2c34"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Crea providers + provider_c002 idempotente."""
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS providers (
            id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            project_id       uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            name             varchar(255) NOT NULL,
            type             varchar(32) NOT NULL,
            scope            text NOT NULL,
            criticality      varchar(16) NOT NULL,
            last_reviewed_at timestamptz,
            last_reviewed_by varchar(255),
            created_at       timestamptz NOT NULL DEFAULT now(),
            updated_at       timestamptz,
            deleted_at       timestamptz,
            CONSTRAINT ck_providers_type
                CHECK (type IN ('cloud','saas','on-prem','staffing','hardware','consultoria')),
            CONSTRAINT ck_providers_criticality
                CHECK (criticality IN ('CRITICO','ALTO','MEDIO','BAJO'))
        );
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_providers_project_id "
        "ON providers (project_id);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_providers_project_criticality "
        "ON providers (project_id, criticality);"
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS provider_c002 (
            id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            provider_id        uuid NOT NULL UNIQUE REFERENCES providers(id) ON DELETE CASCADE,
            status             varchar(32) NOT NULL DEFAULT 'pendiente',
            generated_at       timestamptz,
            evidence_id        uuid REFERENCES evidence(id) ON DELETE SET NULL,
            gaps_json          jsonb,
            last_gap_check_at  timestamptz,
            created_at         timestamptz NOT NULL DEFAULT now(),
            updated_at         timestamptz,
            deleted_at         timestamptz,
            CONSTRAINT ck_provider_c002_status
                CHECK (status IN ('pendiente','firmado','no_aplica','revocado'))
        );
        """
    )

    # GRANT runtime fulkro_app
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON providers TO fulkro_app")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON provider_c002 TO fulkro_app")

    # RLS providers (project_isolation directo)
    op.execute("ALTER TABLE providers ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE providers FORCE ROW LEVEL SECURITY;")
    op.execute(
        """
        DROP POLICY IF EXISTS project_isolation ON providers;
        CREATE POLICY project_isolation ON providers
            USING (project_id = current_project_id());
        """
    )

    # RLS provider_c002 (via provider parent)
    op.execute("ALTER TABLE provider_c002 ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE provider_c002 FORCE ROW LEVEL SECURITY;")
    op.execute(
        """
        DROP POLICY IF EXISTS provider_isolation ON provider_c002;
        CREATE POLICY provider_isolation ON provider_c002
            USING (
                provider_id IN (
                    SELECT id FROM providers
                    WHERE project_id = current_project_id()
                )
            );
        """
    )

    # Audit triggers
    op.execute(
        """
        DROP TRIGGER IF EXISTS tg_audit_providers ON providers;
        CREATE TRIGGER tg_audit_providers
            AFTER INSERT OR UPDATE OR DELETE ON providers
            FOR EACH ROW EXECUTE FUNCTION fn_audit_track();
        """
    )
    op.execute(
        """
        DROP TRIGGER IF EXISTS tg_audit_provider_c002 ON provider_c002;
        CREATE TRIGGER tg_audit_provider_c002
            AFTER INSERT OR UPDATE OR DELETE ON provider_c002
            FOR EACH ROW EXECUTE FUNCTION fn_audit_track();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS tg_audit_provider_c002 ON provider_c002;")
    op.execute("DROP TRIGGER IF EXISTS tg_audit_providers ON providers;")
    op.execute("DROP POLICY IF EXISTS provider_isolation ON provider_c002;")
    op.execute("DROP POLICY IF EXISTS project_isolation ON providers;")
    op.execute("DROP TABLE IF EXISTS provider_c002;")
    op.execute("DROP INDEX IF EXISTS ix_providers_project_criticality;")
    op.execute("DROP INDEX IF EXISTS ix_providers_project_id;")
    op.execute("DROP TABLE IF EXISTS providers;")
