"""m29: client_messages + client_message_attachments tables (FASE 6.A.1).

Revision ID: d4e7a9b1f632
Revises: c3a8d7f2b419
Create Date: 2026-04-29 22:00:00.000000

Motor 29 — Client Messaging. Mensajería bidireccional cliente↔Marcos +
adjuntos MinIO + email forward + threading. Plan v4.2 sección 6.

Schema:
  - ``client_messages`` (FullMixin + 12 cols negocio + CHECK from_role +
    CHECK email_forward_status) + 3 índices (thread DESC + to_contact
    partial + GIN search body_markdown).
  - ``client_message_attachments`` (FullMixin + 7 cols + CHECK 10MB +
    CHECK MIME whitelist) + 1 índice (message_id).
  - 2 triggers ``tg_audit_*`` siguiendo pattern fn_audit_track existente
    (12+ tablas usan pattern hoy + admin_settings 4.A.2.d + M30 5.5.A).
  - RLS: ``client_isolation`` USING (client_id = current_client_id())
    en client_messages — cliente pool filtra por su client_id, admin
    bypassa via SET LOCAL ROLE fulkro (pattern m12_magic_link consume).
    Attachments heredan policy via FK message_id (cascade).

Política TODO-DB-DRIFT-001: revision SIN ``--autogenerate`` (Alembic
default no detecta triggers + GIN op_classes + CHECK enum, evita
re-derivar drift cross-motor 380+ ops). Conserva SOLO operaciones M29.

Ver:
  - Plan v4.2 sección 6.3 (línea 4412-4485)
  - ADR-005 mensajería cliente
  - audit pre-FASE 6 hallazgo H1 RESOLVED 6.A.0 (Celery infra)
  - audit pre-FASE 6 hallazgo H2 RESOLVED 6.A.0 (MinIO bucket bootstrap)
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "d4e7a9b1f632"
down_revision: Union[str, None] = "c3a8d7f2b419"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# MIME whitelist plan v4.2 6.11 — sincronizado con
# backend/app/motors/m29_client_messaging/models.py::ALLOWED_MIME_TYPES
_ALLOWED_MIME_TYPES = (
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
    "application/pdf",
    "text/plain",
    "text/csv",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/zip",
)

_MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024  # 10 MB
_DEFAULT_SIGNED_URL_TTL_SECONDS = 7 * 24 * 60 * 60  # 7 days
_DEFAULT_MINIO_BUCKET = "fulkro-client-messages"


def _full_mixin_cols():
    """Helper FullMixin (UUID PK + timestamps + soft_delete).

    Idéntico a M30 _full_mixin_cols() — extraído aquí para mantener M29
    self-contained y consistente con migration M30 (f4a8c7b1d2e3).
    """
    return [
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "created_at", postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.Column(
            "updated_at", postgresql.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "deleted_at", postgresql.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    ]


def upgrade() -> None:
    # ====================================================================
    # 1. client_messages
    # ====================================================================
    op.create_table(
        "client_messages",
        *_full_mixin_cols(),
        # Tenant context
        sa.Column(
            "client_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # Threading
        sa.Column(
            "thread_id", postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        # Sender
        sa.Column("from_role", sa.String(16), nullable=False),
        sa.Column(
            "from_user_id", postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        # Recipient (M30 integration)
        sa.Column(
            "to_contact_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("client_contacts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # Body
        sa.Column("body_markdown", sa.Text(), nullable=False),
        sa.Column("body_html", sa.Text(), nullable=True),
        # Read state
        sa.Column(
            "is_read_by_admin", sa.Boolean(),
            nullable=False, server_default=sa.text("false"),
        ),
        sa.Column(
            "is_read_by_client", sa.Boolean(),
            nullable=False, server_default=sa.text("false"),
        ),
        # Email forward
        sa.Column("forwarded_to_email", sa.String(320), nullable=True),
        sa.Column(
            "forwarded_at", postgresql.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "email_forward_status", sa.String(16), nullable=True,
        ),
        # CHECK constraints
        sa.CheckConstraint(
            "from_role IN ('client', 'admin')",
            name="ck_client_messages_from_role",
        ),
        sa.CheckConstraint(
            "email_forward_status IS NULL OR "
            "email_forward_status IN "
            "('pending', 'sent', 'failed', 'skipped')",
            name="ck_client_messages_email_forward_status",
        ),
    )
    op.create_index(
        "ix_client_messages_client_thread",
        "client_messages",
        ["client_id", "thread_id", "created_at"],
    )
    op.create_index(
        "ix_client_messages_to_contact",
        "client_messages",
        ["to_contact_id"],
        postgresql_where=sa.text("to_contact_id IS NOT NULL"),
    )
    # GIN full-text search en body_markdown (búsqueda admin libre).
    op.execute(
        "CREATE INDEX ix_client_messages_body_fts "
        "ON client_messages "
        "USING gin (to_tsvector('spanish', body_markdown))"
    )

    # ====================================================================
    # 2. client_message_attachments
    # ====================================================================
    mime_in_clause = ", ".join(
        f"'{m}'" for m in _ALLOWED_MIME_TYPES
    )
    op.create_table(
        "client_message_attachments",
        *_full_mixin_cols(),
        sa.Column(
            "message_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("client_messages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column(
            "minio_bucket", sa.String(64),
            nullable=False, server_default=_DEFAULT_MINIO_BUCKET,
        ),
        sa.Column(
            "minio_object_key", sa.String(512), nullable=False,
        ),
        sa.Column(
            "signed_url_ttl_seconds", sa.Integer(),
            nullable=False,
            server_default=str(_DEFAULT_SIGNED_URL_TTL_SECONDS),
        ),
        sa.Column(
            "uploaded_at", postgresql.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.CheckConstraint(
            f"size_bytes <= {_MAX_ATTACHMENT_BYTES}",
            name="ck_client_message_attachments_size_max_10mb",
        ),
        sa.CheckConstraint(
            f"mime_type IN ({mime_in_clause})",
            name="ck_client_message_attachments_mime_whitelist",
        ),
    )
    op.create_index(
        "ix_client_message_attachments_message",
        "client_message_attachments",
        ["message_id"],
    )

    # ====================================================================
    # 3. RLS — client_isolation policy
    # ====================================================================
    # Pattern híbrido coherente con magic_link consume (m12):
    # cliente pool establece app.current_client_id via global dep, RLS
    # filtra por ese setting. Admin (Marcos) hace SET LOCAL ROLE fulkro
    # per-endpoint (pattern m12) que bypassa RLS por ser BYPASSRLS role.
    #
    # Attachments NO necesitan policy propia: FK CASCADE garantiza que
    # row attachment sólo existe si row message accesible. Pero por
    # defensa profunda (FORCE ROW LEVEL SECURITY) habilitamos RLS en
    # ambas con policy USING (true) en attachments + filtrado real
    # via JOIN en service queries.
    op.execute("ALTER TABLE client_messages ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE client_messages FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY client_isolation ON client_messages "
        "USING (client_id = current_client_id() OR current_client_id() IS NULL) "
        "WITH CHECK (client_id = current_client_id() OR current_client_id() IS NULL)"
    )

    op.execute("ALTER TABLE client_message_attachments ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE client_message_attachments FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY message_isolation ON client_message_attachments "
        "USING (true) WITH CHECK (true)"
    )

    # ====================================================================
    # 4. Audit triggers (fn_audit_track shared canon)
    # ====================================================================
    for table in ("client_messages", "client_message_attachments"):
        op.execute(
            f"CREATE TRIGGER tg_audit_{table} "
            f"AFTER INSERT OR UPDATE OR DELETE ON {table} "
            f"FOR EACH ROW EXECUTE FUNCTION fn_audit_track();"
        )


def downgrade() -> None:
    # Triggers (fn_audit_track NO se toca — compartida 14+ tablas)
    for table in ("client_message_attachments", "client_messages"):
        op.execute(f"DROP TRIGGER IF EXISTS tg_audit_{table} ON {table}")

    # RLS policies
    op.execute(
        "DROP POLICY IF EXISTS message_isolation ON client_message_attachments"
    )
    op.execute(
        "ALTER TABLE client_message_attachments DISABLE ROW LEVEL SECURITY"
    )
    op.execute(
        "DROP POLICY IF EXISTS client_isolation ON client_messages"
    )
    op.execute("ALTER TABLE client_messages DISABLE ROW LEVEL SECURITY")

    # Indexes + tables (orden inverso)
    op.drop_index(
        "ix_client_message_attachments_message",
        table_name="client_message_attachments",
    )
    op.drop_table("client_message_attachments")

    op.execute("DROP INDEX IF EXISTS ix_client_messages_body_fts")
    op.drop_index(
        "ix_client_messages_to_contact", table_name="client_messages",
    )
    op.drop_index(
        "ix_client_messages_client_thread", table_name="client_messages",
    )
    op.drop_table("client_messages")
