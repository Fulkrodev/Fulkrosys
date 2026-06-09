"""san_c_audit_schedules

Revision ID: sancauditsch1
Revises: sancluciafed01
Create Date: 2026-05-05 16:00:00.000000

Crea ``audit_schedules`` (SAN-C.MB-10.6) para tracking auditorías bienales
art. 31 RD 311/2022 + auditorías extraordinarias por cambios sustanciales
(art. 31bis · cloud migration · CPD change · merger).

Refs: SAN-C.MB-10.6
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "sancauditsch1"
down_revision: Union[str, None] = "sancluciafed01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_schedules",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "audit_type",
            sa.String(length=20),
            nullable=False,
            comment="biannual/extraordinary/internal",
        ),
        sa.Column(
            "next_audit_due",
            sa.Date(),
            nullable=False,
        ),
        sa.Column(
            "last_audit_completed",
            sa.Date(),
            nullable=True,
        ),
        sa.Column(
            "last_audit_result",
            sa.String(length=20),
            nullable=True,
            comment="conforme/no_conforme_mayor/no_conforme_menor/observaciones",
        ),
        sa.Column(
            "triggered_by",
            sa.String(length=50),
            nullable=False,
            comment="art_31_periodic/cloud_migration/datacenter_change/merger/etc",
        ),
        sa.Column(
            "notification_sent_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "metadata_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "deleted_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_audit_schedules_project_due",
        "audit_schedules",
        ["project_id", "next_audit_due"],
    )
    op.create_index(
        "ix_audit_schedules_due",
        "audit_schedules",
        ["next_audit_due"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON audit_schedules TO fulkro_app"
    )

    op.execute("ALTER TABLE audit_schedules ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audit_schedules FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY project_isolation ON audit_schedules "
        "USING (project_id = current_project_id())"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS project_isolation ON audit_schedules")
    op.drop_index("ix_audit_schedules_due", table_name="audit_schedules")
    op.drop_index(
        "ix_audit_schedules_project_due", table_name="audit_schedules"
    )
    op.drop_table("audit_schedules")
