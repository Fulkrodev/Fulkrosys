"""M24 IDMS + M25 Project Lifecycle — SPRINT FINAL.

M24:
- Create document_folders (jerarquía carpetas virtuales)
- Create document_tags (tagging manual/regla/llm)
- Extend documents: folder_id, full_text_content, content_hash,
  file_size_bytes, storage_path, clasificacion

M25:
- Extend archived_projects: retention_years, estado, documents_count,
  evidence_count (wrapper ArchivePackage)
- Add projects.lifecycle_state (10 valores)

RLS:
- document_folders + document_tags con project_id tolerante a NULL
- archived_projects ya tiene client_id RLS (mantener)
- project_lifecycle_states ya tiene project_id RLS (mantener)

Revision ID: f4a7c1d982e5
Revises: e2b8f3c91a7d
Create Date: 2026-04-18 22:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "f4a7c1d982e5"
down_revision: Union[str, None] = "e2b8f3c91a7d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ═══════════════════════════════════════
    # M24 — document_folders
    # ═══════════════════════════════════════
    op.create_table(
        "document_folders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("parent_folder_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("document_folders.id"), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("virtual_path", sa.String(length=500), nullable=False),
        sa.Column("is_standard", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("standard_code", sa.String(length=20), nullable=True),
        sa.Column("custom_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.create_index("ix_document_folders_project_id", "document_folders", ["project_id"])
    op.create_index("ix_document_folders_client_id", "document_folders", ["client_id"])

    # M24 — document_tags
    op.create_table(
        "document_tags",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("tag_type", sa.String(length=30), nullable=False),
        sa.Column("tag_value", sa.String(length=100), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default=sa.text("1.0")),
        sa.Column("source", sa.String(length=20), nullable=False, server_default="manual"),
    )
    op.create_index("ix_document_tags_document_id", "document_tags", ["document_id"])
    op.create_index("ix_document_tags_project_id", "document_tags", ["project_id"])
    op.create_index("ix_document_tags_value", "document_tags", ["tag_value"])

    # M24 — extend documents
    op.add_column("documents", sa.Column("folder_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_documents_folder_id", "documents", "document_folders",
        ["folder_id"], ["id"],
    )
    op.create_index("ix_documents_folder_id", "documents", ["folder_id"])
    op.add_column("documents", sa.Column("full_text_content", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("content_hash", sa.String(length=64), nullable=True))
    op.create_index("ix_documents_content_hash", "documents", ["content_hash"])
    op.add_column("documents", sa.Column("file_size_bytes", sa.Integer(), nullable=True, server_default="0"))
    op.add_column("documents", sa.Column("storage_path", sa.String(length=500), nullable=True))
    op.add_column("documents", sa.Column("clasificacion", sa.String(length=30), nullable=True))
    op.create_index("ix_documents_clasificacion", "documents", ["clasificacion"])

    # ═══════════════════════════════════════
    # M25 — extend archived_projects (wrapper ArchivePackage)
    # ═══════════════════════════════════════
    op.add_column("archived_projects", sa.Column("retention_years", sa.Integer(), nullable=True, server_default="6"))
    op.add_column("archived_projects", sa.Column("estado", sa.String(length=20), nullable=True, server_default="created"))
    op.add_column("archived_projects", sa.Column("documents_count", sa.Integer(), nullable=True, server_default="0"))
    op.add_column("archived_projects", sa.Column("evidence_count", sa.Integer(), nullable=True, server_default="0"))

    # M25 — add projects.lifecycle_state
    op.add_column(
        "projects",
        sa.Column("lifecycle_state", sa.String(length=30), nullable=True, server_default="DRAFT"),
    )

    # ═══════════════════════════════════════
    # RLS — nuevas tablas project-scoped
    # ═══════════════════════════════════════
    for table in ("document_folders", "document_tags"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY project_isolation ON {table} "
            f"USING (project_id = current_project_id() OR project_id IS NULL)"
        )


def downgrade() -> None:
    for table in ("document_tags", "document_folders"):
        op.execute(f"DROP POLICY IF EXISTS project_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    op.drop_column("projects", "lifecycle_state")

    for col in ("evidence_count", "documents_count", "estado", "retention_years"):
        op.drop_column("archived_projects", col)

    op.drop_index("ix_documents_clasificacion", table_name="documents")
    op.drop_column("documents", "clasificacion")
    op.drop_column("documents", "storage_path")
    op.drop_column("documents", "file_size_bytes")
    op.drop_index("ix_documents_content_hash", table_name="documents")
    op.drop_column("documents", "content_hash")
    op.drop_column("documents", "full_text_content")
    op.drop_index("ix_documents_folder_id", table_name="documents")
    op.drop_constraint("fk_documents_folder_id", "documents", type_="foreignkey")
    op.drop_column("documents", "folder_id")

    op.drop_index("ix_document_tags_value", table_name="document_tags")
    op.drop_index("ix_document_tags_project_id", table_name="document_tags")
    op.drop_index("ix_document_tags_document_id", table_name="document_tags")
    op.drop_table("document_tags")

    op.drop_index("ix_document_folders_client_id", table_name="document_folders")
    op.drop_index("ix_document_folders_project_id", table_name="document_folders")
    op.drop_table("document_folders")
