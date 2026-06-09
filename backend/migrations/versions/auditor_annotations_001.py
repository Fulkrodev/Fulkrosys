"""CLUSTER 3 Phase C1.1 · auditor_annotations table + RLS.

Sesión 3B-2B.6 CLUSTER 3 Path C interactive features. Auditor portal users
(magic-link bounded · NO ClientUser auth) crean anotaciones inline sobre
targets cross-motor (evidence · medida DdA · MAGERIT assets/threats/safeguards ·
plan tasks · audit_log entries). Admin (Marcos require_owner) review +
response + status workflow.

RLS isolation (Sub-atom 5.A pattern extended):
- Policy 2-way OR: project_id = current_project_id() OR client_id = current_client_id()
- NO legacy NULL clause necessary (NEW table · todo row creado con tenant tagged)
- Admin (fulkro role) bypassa via SECURITY DEFINER OR explicit RESET ROLE

Revision ID: auditor_annotations_001
Revises: audit_log_auditor_events_001
Create Date: 2026-05-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "auditor_annotations_001"
down_revision: Union[str, None] = "audit_log_auditor_events_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Allowed target_type values · cross-motor inspection (Phase 5 views surface)
TARGET_TYPES = (
    "evidence",
    "medida",
    "magerit_asset",
    "magerit_threat",
    "magerit_safeguard",
    "plan_task",
    "audit_log_entry",
)

# Allowed severity values (auditor judgment scale)
SEVERITY_VALUES = ("info", "warning", "concern", "critical")

# Allowed status values (workflow lifecycle)
STATUS_VALUES = ("open", "admin_reviewed", "resolved", "dismissed")


def upgrade() -> None:
    op.create_table(
        "auditor_annotations",
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
                "Token de auditor (purpose=AUDITOR_PORTAL_ENAC) que creó "
                "esta anotación · SET NULL si magic_link soft-deleted"
            ),
        ),
        sa.Column("target_type", sa.String(40), nullable=False),
        sa.Column(
            "target_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment=(
                "FK lógico · NO constraint (target_type varies cross-motor) · "
                "validation app-level"
            ),
        ),
        sa.Column("annotation_text", sa.Text, nullable=False),
        sa.Column("flag_severity", sa.String(20), nullable=False),
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
            comment="Email of admin user who responded (Marcos)",
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
            "target_type IN " + str(TARGET_TYPES).replace("'", "'"),
            name="ck_auditor_annotations_target_type",
        ),
        sa.CheckConstraint(
            "flag_severity IN " + str(SEVERITY_VALUES).replace("'", "'"),
            name="ck_auditor_annotations_flag_severity",
        ),
        sa.CheckConstraint(
            "status IN " + str(STATUS_VALUES).replace("'", "'"),
            name="ck_auditor_annotations_status",
        ),
    )

    op.create_index(
        "ix_auditor_annotations_project_id",
        "auditor_annotations",
        ["project_id"],
    )
    op.create_index(
        "ix_auditor_annotations_client_id",
        "auditor_annotations",
        ["client_id"],
    )
    op.create_index(
        "ix_auditor_annotations_status",
        "auditor_annotations",
        ["project_id", "status"],
        postgresql_where=sa.text("status = 'open'"),
    )
    op.create_index(
        "ix_auditor_annotations_target",
        "auditor_annotations",
        ["target_type", "target_id"],
    )
    op.create_index(
        "ix_auditor_annotations_magic_link_id",
        "auditor_annotations",
        ["magic_link_id"],
        postgresql_where=sa.text("magic_link_id IS NOT NULL"),
    )

    op.execute("ALTER TABLE auditor_annotations ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE auditor_annotations FORCE ROW LEVEL SECURITY")

    op.execute(
        """
        CREATE POLICY auditor_annotations_isolation ON auditor_annotations
          USING (
            project_id = current_project_id()
            OR client_id = current_client_id()
          )
        """
    )

    op.execute(
        """
        CREATE POLICY auditor_annotations_insert_permissive ON auditor_annotations
          FOR INSERT WITH CHECK (true)
        """
    )

    # GRANT explicit fulkro_app (default_acl pattern fails para tables created
    # by fulkro_migrate role · explicit grant required) · Phase C4 audit discovered
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON auditor_annotations "
        "TO fulkro_app"
    )


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS auditor_annotations_insert_permissive "
        "ON auditor_annotations"
    )
    op.execute(
        "DROP POLICY IF EXISTS auditor_annotations_isolation "
        "ON auditor_annotations"
    )
    op.execute("ALTER TABLE auditor_annotations NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE auditor_annotations DISABLE ROW LEVEL SECURITY")
    op.drop_index(
        "ix_auditor_annotations_magic_link_id",
        table_name="auditor_annotations",
    )
    op.drop_index(
        "ix_auditor_annotations_target",
        table_name="auditor_annotations",
    )
    op.drop_index(
        "ix_auditor_annotations_status",
        table_name="auditor_annotations",
    )
    op.drop_index(
        "ix_auditor_annotations_client_id",
        table_name="auditor_annotations",
    )
    op.drop_index(
        "ix_auditor_annotations_project_id",
        table_name="auditor_annotations",
    )
    op.drop_table("auditor_annotations")
