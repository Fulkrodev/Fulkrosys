"""sand_magic_link_migration

SAN-D MB-19.9 · magic_link_migration_log table audit trail (ADR-042).

Tabla append-only · log every migration action ejecutada por
backend/app/scripts/migrate_magic_links_to_tasks.py:

- converted_to_task: magic-link CONTINUO → ClientTask portal record creado.
- revoked_obsolete: magic-link soft-deprecated revocado sin task target
  (lead phase · no client_user yet).
- kept_one_shot: skip · purpose mantiene razón (categoría A-F ADR-042).
- pending_review: skip pero marca para revision manual (no ClientUser
  asociado al project · migration manual cuando cliente onboarding completed).

UNIQUE (magic_link_id) garantiza idempotencia · safe re-run script.

NO FK CASCADE · preserva audit trail si magic_link soft-deleted (auditable
ENAC).

Revision ID: sand_magic_link_migration
Revises: sand_crm_lead_extensions
Create Date: 2026-05-07
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "sand_magic_link_migration"
down_revision = "sand_crm_lead_extensions"
branch_labels = None
depends_on = None


_VALID_MIGRATION_ACTIONS = (
    "converted_to_task",
    "revoked_obsolete",
    "kept_one_shot",
    "pending_review",
)


def upgrade() -> None:
    op.create_table(
        "magic_link_migration_log",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "magic_link_id",
            UUID(as_uuid=True),
            sa.ForeignKey("magic_links.id"),
            nullable=False,
        ),
        sa.Column(
            "original_purpose",
            sa.String(50),
            nullable=False,
        ),
        sa.Column(
            "migration_action",
            sa.String(30),
            nullable=False,
        ),
        sa.Column(
            "target_task_id",
            UUID(as_uuid=True),
            sa.ForeignKey("client_tasks.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "notes",
            sa.Text,
            nullable=True,
        ),
        sa.Column(
            "processed_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "magic_link_id",
            name="uq_magic_link_migration_log_magic_link",
        ),
        sa.CheckConstraint(
            f"migration_action IN {_VALID_MIGRATION_ACTIONS}",
            name="ck_magic_link_migration_action",
        ),
    )
    op.create_index(
        "ix_magic_link_migration_purpose_action",
        "magic_link_migration_log",
        ["original_purpose", "migration_action"],
    )
    op.create_index(
        "ix_magic_link_migration_processed_at",
        "magic_link_migration_log",
        [sa.text("processed_at DESC")],
    )

    op.execute(
        "GRANT SELECT, INSERT ON magic_link_migration_log TO fulkro_app"
    )


def downgrade() -> None:
    op.execute(
        "REVOKE SELECT, INSERT ON magic_link_migration_log FROM fulkro_app"
    )
    op.drop_index(
        "ix_magic_link_migration_processed_at",
        table_name="magic_link_migration_log",
    )
    op.drop_index(
        "ix_magic_link_migration_purpose_action",
        table_name="magic_link_migration_log",
    )
    op.drop_table("magic_link_migration_log")
