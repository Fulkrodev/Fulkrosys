"""Sesión 3B-2B.6 Cluster 1 Phase 2 · projects.audit_passed_at + audit_passed_by columns.

Audit Phase 0 DIM 4 critical gap A: NO admin endpoint mark-audit-passed +
lifecycle_state advance missing. This migration adds tracking columns para state
transition UNDER_REVIEW → CONFORMANT + lifecycle DRAFT/SIGNED/ACTIVE → CERTIFIED.

Backward-compat: ambas nullable · existing rows NO afectados.

Revision ID: audit_passed_columns_001
Revises: copilot_rls_client_isolation_001
Create Date: 2026-05-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "audit_passed_columns_001"
down_revision: Union[str, None] = "copilot_rls_client_isolation_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column(
            "audit_passed_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "projects",
        sa.Column(
            "audit_passed_by",
            sa.String(length=255),
            nullable=True,
        ),
    )
    op.add_column(
        "projects",
        sa.Column(
            "audit_result",
            sa.String(length=30),
            nullable=True,
        ),
    )
    op.add_column(
        "projects",
        sa.Column(
            "audit_report_ref",
            sa.String(length=120),
            nullable=True,
        ),
    )

    # CHECK constraint audit_result allowed values
    op.create_check_constraint(
        "projects_audit_result_check",
        "projects",
        "audit_result IS NULL OR audit_result IN ("
        "'passed', 'observed', 'correction_required', 'failed'"
        ")",
    )

    # Index for queries "latest audit-passed projects" (Marcos dashboard)
    op.create_index(
        "ix_projects_audit_passed_at",
        "projects",
        ["audit_passed_at"],
        postgresql_where=sa.text("audit_passed_at IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_projects_audit_passed_at", table_name="projects")
    op.drop_constraint("projects_audit_result_check", "projects", type_="check")
    op.drop_column("projects", "audit_report_ref")
    op.drop_column("projects", "audit_result")
    op.drop_column("projects", "audit_passed_by")
    op.drop_column("projects", "audit_passed_at")
