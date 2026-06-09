"""add phase_changed to ck_project_lifecycle_events_event_type

Ejecutable 8 Pasada 16 (Future-1.E.workflow-trigger-bug-fix · finding P9/P7):
el trigger tg_projects_phase_changed emite event_type='phase_changed' al avanzar
projects.fase, pero el CHECK constraint ck_project_lifecycle_events_event_type NO
incluía 'phase_changed' -> IntegrityError (violates check constraint) en m19_risk
triggers, core/test_workflow_state, billing/auto_billing, notifications. Se añade el
valor. Afecta a ambas DBs (el árbol nunca lo añadió). Idempotente (DROP IF EXISTS).

Revision ID: add_phase_changed_event_type_001
Revises: radar_widen_llm_freetext_text_001
Create Date: 2026-05-31
"""
from alembic import op

revision = "add_phase_changed_event_type_001"
down_revision = "radar_widen_llm_freetext_text_001"
branch_labels = None
depends_on = None

_TABLE = "project_lifecycle_events"
_CONSTRAINT = "ck_project_lifecycle_events_event_type"
_BASE = [
    "certified", "retainer_offered", "retainer_accepted", "retainer_declined",
    "grace_period_started", "backup_generated", "backup_sent", "warning_sent",
    "reconsideration_sent", "deletion_scheduled", "data_deleted", "reactivated",
    "audit_marked",
]


def _recreate(values):
    vals = ", ".join(f"'{v}'" for v in values)
    op.execute(f"ALTER TABLE {_TABLE} DROP CONSTRAINT IF EXISTS {_CONSTRAINT}")
    op.execute(
        f"ALTER TABLE {_TABLE} ADD CONSTRAINT {_CONSTRAINT} "
        f"CHECK (event_type::text = ANY (ARRAY[{vals}]::text[]))"
    )


def upgrade() -> None:
    _recreate(_BASE + ["phase_changed"])


def downgrade() -> None:
    _recreate(_BASE)
