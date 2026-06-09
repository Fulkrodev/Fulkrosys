"""M25 Paso 4 — project_lifecycle_events + project_archived_backups + grace period fields.

Anade:
- project_lifecycle_events (event log cliente-facing con event_type amplio)
- project_archived_backups (ZIP descargable con TTL 60d y firma Ed25519)
- projects: certified_at, grace_period_started_at, grace_period_ends_at, deleted_at

RLS:
- project_lifecycle_events: project_id (tolera NULL para eventos post-delete)
- project_archived_backups: client_id (tolera project_id NULL para reactivacion)

Revision ID: d2e6f4a9b812
Revises: c9a3b7f5d201
Create Date: 2026-04-22 15:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "d2e6f4a9b812"
down_revision = "c9a3b7f5d201"
branch_labels = None
depends_on = None


ALLOWED_EVENT_TYPES = (
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
)


def upgrade() -> None:
    # ── project_lifecycle_events ──────────────────────────────────────
    op.create_table(
        "project_lifecycle_events",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "project_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="SET NULL"),
            nullable=True, index=True,
        ),
        sa.Column(
            "client_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clients.id", ondelete="SET NULL"),
            nullable=True, index=True,
        ),
        sa.Column(
            "event_type", sa.String(50), nullable=False, index=True,
        ),
        sa.Column(
            "event_date", sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"), nullable=False, index=True,
        ),
        sa.Column(
            "performed_by", sa.String(50), nullable=True,
            # marcos | cliente | system | celery
        ),
        sa.Column(
            "metadata_jsonb", postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "grace_period_days", sa.Integer(), nullable=True,
        ),
        sa.Column(
            "backup_zip_path", sa.String(500), nullable=True,
        ),
        sa.Column(
            "backup_signature_ed25519", sa.Text(), nullable=True,
        ),
        sa.Column(
            "backup_download_magic_link_id", postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "notification_sent_to", postgresql.ARRAY(sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.CheckConstraint(
            "event_type IN ("
            + ", ".join(f"'{e}'" for e in ALLOWED_EVENT_TYPES)
            + ")",
            name="ck_project_lifecycle_events_event_type",
        ),
    )

    # ── project_archived_backups ──────────────────────────────────────
    op.create_table(
        "project_archived_backups",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "project_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="SET NULL"),
            nullable=True, index=True,
        ),
        sa.Column(
            "client_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clients.id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column("zip_path", sa.String(500), nullable=False),
        sa.Column("zip_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256_hash", sa.String(64), nullable=False),
        sa.Column("ed25519_signature", sa.Text(), nullable=False),
        sa.Column("ed25519_public_key_pem", sa.Text(), nullable=True),
        sa.Column(
            "manifest_jsonb", postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "generated_at", sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.Column(
            "expires_at", sa.TIMESTAMP(timezone=True), nullable=False,
        ),
        sa.Column(
            "downloaded_at", sa.TIMESTAMP(timezone=True), nullable=True,
        ),
        sa.Column(
            "download_count", sa.Integer(), nullable=False, server_default="0",
        ),
        sa.Column(
            "deleted_at", sa.TIMESTAMP(timezone=True), nullable=True,
        ),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
    )
    op.create_index(
        "ix_project_archived_backups_expires_at",
        "project_archived_backups", ["expires_at"],
    )

    # ── projects: campos adicionales para Paso 4 ─────────────────────
    op.add_column(
        "projects",
        sa.Column("certified_at", sa.Date(), nullable=True),
    )
    op.add_column(
        "projects",
        sa.Column(
            "grace_period_started_at",
            sa.TIMESTAMP(timezone=True), nullable=True,
        ),
    )
    op.add_column(
        "projects",
        sa.Column(
            "grace_period_ends_at",
            sa.TIMESTAMP(timezone=True), nullable=True,
        ),
    )
    # Nota: projects.deleted_at ya existe via SoftDeleteMixin — no re-crear.

    # ── RLS ──────────────────────────────────────────────────────────
    op.execute(
        "ALTER TABLE project_lifecycle_events ENABLE ROW LEVEL SECURITY"
    )
    op.execute(
        "ALTER TABLE project_lifecycle_events FORCE ROW LEVEL SECURITY"
    )
    # project_id puede quedar NULL tras delete, tolerarlo (Marcos ve todo via admin)
    op.execute(
        "CREATE POLICY project_isolation ON project_lifecycle_events "
        "USING (project_id = current_project_id() OR project_id IS NULL)"
    )

    op.execute(
        "ALTER TABLE project_archived_backups ENABLE ROW LEVEL SECURITY"
    )
    op.execute(
        "ALTER TABLE project_archived_backups FORCE ROW LEVEL SECURITY"
    )
    op.execute(
        "CREATE POLICY client_isolation ON project_archived_backups "
        "USING (client_id = current_client_id())"
    )


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS client_isolation ON project_archived_backups"
    )
    op.execute(
        "ALTER TABLE project_archived_backups DISABLE ROW LEVEL SECURITY"
    )
    op.execute(
        "DROP POLICY IF EXISTS project_isolation ON project_lifecycle_events"
    )
    op.execute(
        "ALTER TABLE project_lifecycle_events DISABLE ROW LEVEL SECURITY"
    )

    op.drop_column("projects", "grace_period_ends_at")
    op.drop_column("projects", "grace_period_started_at")
    op.drop_column("projects", "certified_at")

    op.drop_index(
        "ix_project_archived_backups_expires_at",
        table_name="project_archived_backups",
    )
    op.drop_table("project_archived_backups")
    op.drop_table("project_lifecycle_events")
