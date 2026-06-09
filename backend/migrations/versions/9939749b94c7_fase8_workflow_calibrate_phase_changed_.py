"""8.WORKFLOW.CALIBRATE W3 — añadir 'phase_changed' al enum event_type.

ISSUE-W3: workflow_state CASCADE queries necesitan filtrar data motor por
último phase_changed event para respetar phase regression. El CHECK
constraint actual de ``project_lifecycle_events.event_type`` no incluye
``phase_changed``, por lo que cualquier INSERT con ese valor falla.

Esta migration añade ``phase_changed`` al enum permitido. NO crea trigger
automático para emitir el evento cuando ``projects.fase`` cambia · eso queda
como TODO-FASE-8-WORKFLOW-PHASE-CHANGED-TRIGGER-001 (pendiente o decisión:
trigger PG vs hook SQLAlchemy event vs servicio explícito).

Sin ese trigger, el filtro CASCADE COALESCE→epoch deja pasar toda la data
(comportamiento equivalente al pre-W3). Migration es por tanto preparación
de infraestructura · activación efectiva requiere completar el trigger.

Revision ID: 9939749b94c7
Revises: 0bdc5b753ab2
Create Date: 2026-04-30 17:58:53.001135
"""
from typing import Sequence, Union

from alembic import op


revision: str = "9939749b94c7"
down_revision: Union[str, None] = "0bdc5b753ab2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_OLD_CHECK = (
    "event_type IN ("
    "'certified', 'retainer_offered', 'retainer_accepted', "
    "'retainer_declined', 'grace_period_started', 'backup_generated', "
    "'backup_sent', 'warning_sent', 'reconsideration_sent', "
    "'deletion_scheduled', 'data_deleted', 'reactivated'"
    ")"
)
_NEW_CHECK = (
    "event_type IN ("
    "'certified', 'retainer_offered', 'retainer_accepted', "
    "'retainer_declined', 'grace_period_started', 'backup_generated', "
    "'backup_sent', 'warning_sent', 'reconsideration_sent', "
    "'deletion_scheduled', 'data_deleted', 'reactivated', "
    "'phase_changed'"
    ")"
)
_CONSTRAINT_NAME = "ck_project_lifecycle_events_event_type"


def upgrade() -> None:
    op.drop_constraint(
        _CONSTRAINT_NAME,
        "project_lifecycle_events",
        type_="check",
    )
    op.create_check_constraint(
        _CONSTRAINT_NAME,
        "project_lifecycle_events",
        _NEW_CHECK,
    )


def downgrade() -> None:
    # Borrar rows existentes con phase_changed antes de revertir el CHECK,
    # para no dejar BD en estado que viole el constraint anterior.
    op.execute(
        "DELETE FROM project_lifecycle_events "
        "WHERE event_type = 'phase_changed'"
    )
    op.drop_constraint(
        _CONSTRAINT_NAME,
        "project_lifecycle_events",
        type_="check",
    )
    op.create_check_constraint(
        _CONSTRAINT_NAME,
        "project_lifecycle_events",
        _OLD_CHECK,
    )
