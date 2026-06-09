"""san_e_mb3_a_m25_exit_checklist

ADR-046 v3 SAN-E.MB-3.A: tabla exit_checklist_items para checklist granular
pre-cierre proyecto (capa validacion sobre M25 lifecycle FSM).

4 categorias x 4 estados · UNIQUE (project_id, item_code) · partial index
(project_id, status) para queries de readiness rapidos · CHECK constraints
en category y status.

RLS: project_isolation policy + audit trigger fn_audit_track (mismo patron
que evidence, projects, etc.).

Revision ID: e3a01a7b2c34
Revises: ff9d6c0e9ded
Create Date: 2026-05-08
"""
from typing import Sequence, Union

from alembic import op


revision: str = "e3a01a7b2c34"
down_revision: Union[str, None] = "ff9d6c0e9ded"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Crea tabla exit_checklist_items idempotente con RLS y audit trigger."""
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS exit_checklist_items (
            id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            project_id   uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            item_code    varchar(64) NOT NULL,
            label        varchar(255) NOT NULL,
            category     varchar(32) NOT NULL,
            status       varchar(32) NOT NULL DEFAULT 'pendiente',
            evidence_id  uuid REFERENCES evidence(id) ON DELETE SET NULL,
            completed_at timestamptz,
            completed_by varchar(255),
            note         text,
            created_at   timestamptz NOT NULL DEFAULT now(),
            updated_at   timestamptz,
            deleted_at   timestamptz,
            CONSTRAINT uq_exit_checklist_project_item UNIQUE (project_id, item_code),
            CONSTRAINT ck_exit_checklist_category
                CHECK (category IN ('legal','tecnico','documentacion','operacional')),
            CONSTRAINT ck_exit_checklist_status
                CHECK (status IN ('pendiente','completado','bloqueado','no_aplica'))
        );
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_exit_checklist_items_project_id "
        "ON exit_checklist_items (project_id);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_exit_checklist_project_status "
        "ON exit_checklist_items (project_id, status);"
    )

    # Privilegios runtime fulkro_app (NOSUPERUSER · RLS enforced).
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE "
        "ON exit_checklist_items TO fulkro_app"
    )

    # RLS: project_isolation
    op.execute("ALTER TABLE exit_checklist_items ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE exit_checklist_items FORCE ROW LEVEL SECURITY;")
    op.execute(
        """
        DROP POLICY IF EXISTS project_isolation ON exit_checklist_items;
        CREATE POLICY project_isolation ON exit_checklist_items
            USING (project_id = current_project_id());
        """
    )

    # Audit trigger (patron heredado evidence/projects)
    op.execute(
        """
        DROP TRIGGER IF EXISTS tg_audit_exit_checklist_items ON exit_checklist_items;
        CREATE TRIGGER tg_audit_exit_checklist_items
            AFTER INSERT OR UPDATE OR DELETE ON exit_checklist_items
            FOR EACH ROW EXECUTE FUNCTION fn_audit_track();
        """
    )


def downgrade() -> None:
    """Reverso idempotente: drop trigger, policy, indexes, table."""
    op.execute("DROP TRIGGER IF EXISTS tg_audit_exit_checklist_items ON exit_checklist_items;")
    op.execute("DROP POLICY IF EXISTS project_isolation ON exit_checklist_items;")
    op.execute("DROP INDEX IF EXISTS ix_exit_checklist_project_status;")
    op.execute("DROP INDEX IF EXISTS ix_exit_checklist_items_project_id;")
    op.execute("DROP TABLE IF EXISTS exit_checklist_items;")
