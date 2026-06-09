"""san_e_mb3_d_m27_renewal_milestones

ADR-046 v3 SAN-E.MB-3.D: sub-tabla relacional renewal_campaign_milestones
(child de renewal_campaigns). 8 milestones default seed pre-renovacion.

Revision ID: b5e9c2a4d8f7
Revises: a8f3d2c4b5e1
Create Date: 2026-05-08
"""
from typing import Sequence, Union

from alembic import op


revision: str = "b5e9c2a4d8f7"
down_revision: Union[str, None] = "a8f3d2c4b5e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS renewal_campaign_milestones (
            id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            campaign_id     uuid NOT NULL REFERENCES renewal_campaigns(id) ON DELETE CASCADE,
            milestone_code  varchar(64) NOT NULL,
            label           varchar(255) NOT NULL,
            due_date        timestamptz,
            status          varchar(32) NOT NULL DEFAULT 'pendiente',
            responsable     varchar(255),
            completed_at    timestamptz,
            notes           text,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz,
            deleted_at      timestamptz,
            CONSTRAINT uq_renewal_milestone_campaign_code UNIQUE (campaign_id, milestone_code),
            CONSTRAINT ck_renewal_milestone_status
                CHECK (status IN ('pendiente','en_progreso','completado','bloqueado','no_aplica'))
        );
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_renewal_milestone_campaign "
        "ON renewal_campaign_milestones (campaign_id);"
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE "
        "ON renewal_campaign_milestones TO fulkro_app"
    )

    # RLS via parent campaign · project_isolation indirecto
    op.execute("ALTER TABLE renewal_campaign_milestones ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE renewal_campaign_milestones FORCE ROW LEVEL SECURITY;")
    op.execute(
        """
        DROP POLICY IF EXISTS campaign_isolation ON renewal_campaign_milestones;
        CREATE POLICY campaign_isolation ON renewal_campaign_milestones
            USING (
                campaign_id IN (
                    SELECT id FROM renewal_campaigns
                    WHERE project_id = current_project_id()
                       OR project_id IS NULL
                )
            );
        """
    )

    op.execute(
        """
        DROP TRIGGER IF EXISTS tg_audit_renewal_milestones ON renewal_campaign_milestones;
        CREATE TRIGGER tg_audit_renewal_milestones
            AFTER INSERT OR UPDATE OR DELETE ON renewal_campaign_milestones
            FOR EACH ROW EXECUTE FUNCTION fn_audit_track();
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS tg_audit_renewal_milestones ON renewal_campaign_milestones;"
    )
    op.execute("DROP POLICY IF EXISTS campaign_isolation ON renewal_campaign_milestones;")
    op.execute("DROP INDEX IF EXISTS ix_renewal_milestone_campaign;")
    op.execute("DROP TABLE IF EXISTS renewal_campaign_milestones;")
