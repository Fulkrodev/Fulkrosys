"""san_b_workflow_phase_changed_trigger_lifecycle

Revision ID: 7ebd575c4f66
Revises: 90dd52c1dfd9
Create Date: 2026-05-04 17:38:43.425560

Trigger BD ``tg_projects_phase_changed`` AFTER UPDATE OF fase ON projects.
Emite row en ``project_lifecycle_events`` con ``event_type='phase_changed'``
+ metadata_jsonb {old_fase, new_fase, changed_by, source}.

Reuso intencional de tabla existente (NO event_log nueva): workflow_state.py:101
ya consume `project_lifecycle_events` con ese event_type para filtro W3.
M19 listener (MB-6.3) consume mismos events para auto-generar magic-links.

Refs: SAN-B.MB-6.1 · cierre TODO-FASE-8-WORKFLOW-PHASE-CHANGED-TRIGGER-001
"""
from typing import Sequence, Union

from alembic import op


revision: str = '7ebd575c4f66'
down_revision: Union[str, None] = '90dd52c1dfd9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION fn_projects_phase_changed()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.fase IS DISTINCT FROM OLD.fase THEN
                INSERT INTO project_lifecycle_events (
                    project_id, event_type, event_date, metadata_jsonb
                ) VALUES (
                    NEW.id,
                    'phase_changed',
                    NOW(),
                    jsonb_build_object(
                        'old_fase', OLD.fase,
                        'new_fase', NEW.fase,
                        'changed_by', current_setting('app.current_user_id', true),
                        'source', 'tg_projects_phase_changed'
                    )
                );
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        DROP TRIGGER IF EXISTS tg_projects_phase_changed ON projects;
        CREATE TRIGGER tg_projects_phase_changed
        AFTER UPDATE OF fase ON projects
        FOR EACH ROW
        EXECUTE FUNCTION fn_projects_phase_changed();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS tg_projects_phase_changed ON projects;")
    op.execute("DROP FUNCTION IF EXISTS fn_projects_phase_changed();")
