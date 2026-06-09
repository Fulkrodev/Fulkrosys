"""CLUSTER 3 Phase C2.1 · auditor_clarification_requests table + RLS.

Sesión 3B-2B.6 CLUSTER 3 Path C interactive features. Auditor portal users
solicitan aclaraciones cross-motor (preguntas formales sobre target específico
o consulta general scoped por proyecto). Admin (Marcos) responde + status
workflow.

Mirror pattern Phase C1 auditor_annotations · same 2-way RLS isolation.

Revision ID: auditor_clarification_001
Revises: auditor_annotations_001
Create Date: 2026-05-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "auditor_clarification_001"
down_revision: Union[str, None] = "auditor_annotations_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Optional anchor target_type values (same as annotations Phase C1)
TARGET_TYPES_INCL_NULL = (
    "evidence",
    "medida",
    "magerit_asset",
    "magerit_threat",
    "magerit_safeguard",
    "plan_task",
    "audit_log_entry",
    "general",  # CLUSTER 3 Phase C2 · clarifications can be general (NO target anchor)
)

STATUS_VALUES = ("open", "in_progress", "responded", "closed")

PRIORITY_VALUES = ("low", "normal", "high", "urgent")


def upgrade() -> None:
    op.create_table(
        "auditor_clarification_requests",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "client_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "magic_link_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("magic_links.id", ondelete="SET NULL"),
            nullable=True,
            comment=(
                "Token de auditor (AUDITOR_PORTAL_ENAC) que creó la solicitud · "
                "SET NULL si magic_link soft-deleted"
            ),
        ),
        sa.Column("question_text", sa.Text, nullable=False),
        sa.Column(
            "linked_target_type",
            sa.String(40),
            nullable=False,
            server_default="general",
            comment="Optional anchor · 'general' si NO se vincula a target específico",
        ),
        sa.Column(
            "linked_target_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="FK lógico al target (NULL si linked_target_type='general')",
        ),
        sa.Column(
            "priority",
            sa.String(20),
            nullable=False,
            server_default="normal",
        ),
        sa.Column(
            "status",
            sa.String(30),
            nullable=False,
            server_default="open",
        ),
        sa.Column("admin_response", sa.Text, nullable=True),
        sa.Column(
            "admin_responded_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "admin_responded_by",
            sa.String(255),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "deleted_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.CheckConstraint(
            "linked_target_type IN " + str(TARGET_TYPES_INCL_NULL).replace("'", "'"),
            name="ck_auditor_clarifications_target_type",
        ),
        sa.CheckConstraint(
            "status IN " + str(STATUS_VALUES).replace("'", "'"),
            name="ck_auditor_clarifications_status",
        ),
        sa.CheckConstraint(
            "priority IN " + str(PRIORITY_VALUES).replace("'", "'"),
            name="ck_auditor_clarifications_priority",
        ),
    )

    op.create_index(
        "ix_auditor_clarifications_project_id",
        "auditor_clarification_requests",
        ["project_id"],
    )
    op.create_index(
        "ix_auditor_clarifications_client_id",
        "auditor_clarification_requests",
        ["client_id"],
    )
    op.create_index(
        "ix_auditor_clarifications_status",
        "auditor_clarification_requests",
        ["project_id", "status"],
        postgresql_where=sa.text("status IN ('open', 'in_progress')"),
    )
    op.create_index(
        "ix_auditor_clarifications_priority",
        "auditor_clarification_requests",
        ["priority", "status"],
        postgresql_where=sa.text(
            "priority IN ('high', 'urgent') AND status IN ('open', 'in_progress')"
        ),
    )
    op.create_index(
        "ix_auditor_clarifications_magic_link_id",
        "auditor_clarification_requests",
        ["magic_link_id"],
        postgresql_where=sa.text("magic_link_id IS NOT NULL"),
    )

    op.execute(
        "ALTER TABLE auditor_clarification_requests ENABLE ROW LEVEL SECURITY"
    )
    op.execute(
        "ALTER TABLE auditor_clarification_requests FORCE ROW LEVEL SECURITY"
    )

    op.execute(
        """
        CREATE POLICY auditor_clarifications_isolation
          ON auditor_clarification_requests
          USING (
            project_id = current_project_id()
            OR client_id = current_client_id()
          )
        """
    )
    op.execute(
        """
        CREATE POLICY auditor_clarifications_insert_permissive
          ON auditor_clarification_requests
          FOR INSERT WITH CHECK (true)
        """
    )

    # GRANT SELECT/INSERT/UPDATE/DELETE to fulkro_app (runtime role · RLS enforced)
    # Default ACL pattern fails para tables created by fulkro_migrate · explicit grant.
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON auditor_clarification_requests "
        "TO fulkro_app"
    )


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS auditor_clarifications_insert_permissive "
        "ON auditor_clarification_requests"
    )
    op.execute(
        "DROP POLICY IF EXISTS auditor_clarifications_isolation "
        "ON auditor_clarification_requests"
    )
    op.execute(
        "ALTER TABLE auditor_clarification_requests NO FORCE ROW LEVEL SECURITY"
    )
    op.execute(
        "ALTER TABLE auditor_clarification_requests DISABLE ROW LEVEL SECURITY"
    )
    op.drop_index(
        "ix_auditor_clarifications_magic_link_id",
        table_name="auditor_clarification_requests",
    )
    op.drop_index(
        "ix_auditor_clarifications_priority",
        table_name="auditor_clarification_requests",
    )
    op.drop_index(
        "ix_auditor_clarifications_status",
        table_name="auditor_clarification_requests",
    )
    op.drop_index(
        "ix_auditor_clarifications_client_id",
        table_name="auditor_clarification_requests",
    )
    op.drop_index(
        "ix_auditor_clarifications_project_id",
        table_name="auditor_clarification_requests",
    )
    op.drop_table("auditor_clarification_requests")
