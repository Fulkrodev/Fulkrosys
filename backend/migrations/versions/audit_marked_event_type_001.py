"""Sesión 3B-2B.6 Cluster 1 Phase 2 · extend project_lifecycle_events check constraint con 'audit_marked'.

Audit Phase 0 DIM 4 critical gap A · admin mark_audit_passed emits NEW event_type
'audit_marked' que no estaba en CHECK constraint original (d2e6f4a9b812 ALLOWED set).

Backward-compat: solo ADD permite nuevo valor · existing 12 valores untouched.

Revision ID: audit_marked_event_type_001
Revises: audit_passed_columns_001
Create Date: 2026-05-26
"""
from typing import Sequence, Union

from alembic import op


revision: str = "audit_marked_event_type_001"
down_revision: Union[str, None] = "audit_passed_columns_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_NEW_VALUES = [
    "certified",
    "retainer_offered",
    "retainer_accepted",
    "retainer_declined",
    "grace_period_started",
    "backup_generated",
    "backup_sent",
    "warning_sent",
    "reconsideration_sent",
    "deletion_scheduled",
    "data_deleted",
    "reactivated",
    "audit_marked",  # NEW
]

_OLD_VALUES = [v for v in _NEW_VALUES if v != "audit_marked"]


def _values_clause(values: list[str]) -> str:
    return ", ".join(f"'{v}'" for v in values)


def upgrade() -> None:
    op.drop_constraint(
        "ck_project_lifecycle_events_event_type",
        "project_lifecycle_events",
        type_="check",
    )
    op.create_check_constraint(
        "ck_project_lifecycle_events_event_type",
        "project_lifecycle_events",
        f"event_type IN ({_values_clause(_NEW_VALUES)})",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_project_lifecycle_events_event_type",
        "project_lifecycle_events",
        type_="check",
    )
    op.create_check_constraint(
        "ck_project_lifecycle_events_event_type",
        "project_lifecycle_events",
        f"event_type IN ({_values_clause(_OLD_VALUES)})",
    )
