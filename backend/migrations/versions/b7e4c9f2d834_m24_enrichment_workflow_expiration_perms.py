"""M24 IDMS enrichment — workflow status + expiration + permissions.

Extiende M24 IDMS existente con 3 gaps de Paso 3.1 Sesion 9:
- documents: columnas approved_by_user_id, approved_at, expires_at,
  review_period_months + indices.
- idms_document_permissions: tabla nueva owner/editor/viewer.

NO reescribe nada existente. NO anade CHECK constraint sobre
documents.estado porque el campo es legacy compartido con M6 y otros
motores; el workflow enforza valores en service layer.

Revision ID: b7e4c9f2d834
Revises: a5c2f8e9d417
Create Date: 2026-04-24 09:30:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "b7e4c9f2d834"
down_revision = "a5c2f8e9d417"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. documents: columnas para workflow approve + expiration
    # ------------------------------------------------------------------
    op.add_column(
        "documents",
        sa.Column(
            "approved_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("auth_users.id"),
            nullable=True,
        ),
    )
    op.add_column(
        "documents",
        sa.Column(
            "approved_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "documents",
        sa.Column(
            "expires_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "documents",
        sa.Column(
            "review_period_months",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_documents_approved_by_user_id",
        "documents",
        ["approved_by_user_id"],
    )
    # Indice parcial para queries rapidas de alertas caducidad
    op.create_index(
        "ix_documents_expires_at_notnull",
        "documents",
        ["expires_at"],
        postgresql_where=sa.text("expires_at IS NOT NULL"),
    )
    # Composite para queries list-by-status
    op.create_index(
        "ix_documents_project_estado",
        "documents",
        ["project_id", "estado"],
    )

    # ------------------------------------------------------------------
    # 2. idms_document_permissions: tabla nueva
    # ------------------------------------------------------------------
    op.create_table(
        "idms_document_permissions",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            primary_key=True, server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "document_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("auth_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column(
            "granted_by_user_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("auth_users.id"),
            nullable=True,
        ),
        sa.Column(
            "granted_at", sa.TIMESTAMP(timezone=True),
            nullable=False, server_default=sa.text("now()"),
        ),
        # FullMixin columns (matching TimestampMixin + SoftDeleteMixin)
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True),
            nullable=False, server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True),
            nullable=True, server_default=sa.text("now()"),
            onupdate=sa.text("now()"),
        ),
        sa.Column(
            "deleted_at", sa.TIMESTAMP(timezone=True), nullable=True,
        ),
        sa.CheckConstraint(
            "role IN ('owner', 'editor', 'viewer')",
            name="ck_idms_perm_role",
        ),
        sa.UniqueConstraint(
            "document_id", "user_id",
            name="uq_idms_perm_doc_user",
        ),
    )
    op.create_index(
        "ix_idms_perm_document_id",
        "idms_document_permissions",
        ["document_id"],
    )
    op.create_index(
        "ix_idms_perm_user_id",
        "idms_document_permissions",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_idms_perm_user_id", table_name="idms_document_permissions")
    op.drop_index("ix_idms_perm_document_id", table_name="idms_document_permissions")
    op.drop_table("idms_document_permissions")

    op.drop_index("ix_documents_project_estado", table_name="documents")
    op.drop_index("ix_documents_expires_at_notnull", table_name="documents")
    op.drop_index("ix_documents_approved_by_user_id", table_name="documents")

    op.drop_column("documents", "review_period_months")
    op.drop_column("documents", "expires_at")
    op.drop_column("documents", "approved_at")
    op.drop_column("documents", "approved_by_user_id")
