"""Motor 29 — Client Messaging: SQLAlchemy ORM models.

2 tablas:
  - ``client_messages`` — mensaje individual en thread cliente↔Marcos.
  - ``client_message_attachments`` — adjuntos MinIO bucket
    ``fulkro-client-messages`` con MIME whitelist + 10 MB cap.

Convenciones FULKRO:
  - ``FullMixin`` (UUID PK + created_at + updated_at + deleted_at).
  - FK ``client_id`` ON DELETE CASCADE (eliminar cliente borra mensajes).
  - FK ``project_id`` opcional (mensaje libre cliente puede no pertenecer
    a un proyecto activo).
  - FK ``to_contact_id`` opcional (composer admin selecciona contacto M30).
  - FK ``message_id`` ON DELETE CASCADE en attachments.
  - Sin FK on ``from_user_id`` (puede apuntar a ``auth_users.id`` cuando
    ``from_role='admin'`` o a ``client_users.id`` cuando ``from_role='client'``;
    la coherencia se valida en service layer).

RLS:
  - ``client_isolation`` USING (client_id = current_client_id()) — cliente
    pool filtra por su client_id. Admin bypassa via SET LOCAL ROLE fulkro_app_bypassrls
    (pattern m12 magic_link consume).

Indexes:
  - ``client_messages(client_id, thread_id, created_at)`` — listar thread
  - ``client_messages(to_contact_id) WHERE NOT NULL`` — filtro M30 admin
  - ``client_messages USING gin(to_tsvector('spanish', body_markdown))``
    — búsqueda full-text admin
  - ``client_message_attachments(message_id)`` — fetch attachments
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, FullMixin


# ────────────────────────────────────────────────────────────────────
# CONSTANTS
# ────────────────────────────────────────────────────────────────────

# from_role CHECK: pool del sender
FROM_ROLE_VALUES = ("client", "admin")

# email_forward_status CHECK: estado del reenvío email out-of-band
EMAIL_FORWARD_STATUS_VALUES = ("pending", "sent", "failed", "skipped")

# MIME whitelist plan v4.2 6.11 — defensa profunda en BD + service layer
ALLOWED_MIME_TYPES = (
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
    "application/pdf",
    "text/plain",
    "text/csv",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
    "application/zip",
)

# 10 MB cap (CHECK BD + validación service layer + frontend UX)
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024  # 10 485 760

# Default signed URL TTL: 7 días (604 800 s)
DEFAULT_SIGNED_URL_TTL_SECONDS = 7 * 24 * 60 * 60

# MinIO bucket por defecto (sub-fase 6.A.0 bootstrap)
DEFAULT_MINIO_BUCKET = "fulkro-client-messages"


# ────────────────────────────────────────────────────────────────────
# MODELS
# ────────────────────────────────────────────────────────────────────


class ClientMessage(FullMixin, Base):
    """Mensaje en thread cliente↔Marcos.

    Plan v4.2 6.3 schema. Diferencias FullMixin vs plan inline:
      - ``id`` UUID PK heredado de ``UUIDPrimaryKeyMixin`` (uuid.uuid4 default
        Python-side; postgres usa server_default ``gen_random_uuid()`` en
        migración).
      - ``created_at`` heredado de ``TimestampMixin``.
      - ``updated_at`` heredado (triggers BD lo actualizan al UPDATE).
      - ``deleted_at`` heredado de ``SoftDeleteMixin`` para purge differido
        (soft-delete por compliance audit ENS).
    """

    __tablename__ = "client_messages"
    __table_args__ = (
        Index(
            "ix_client_messages_client_thread",
            "client_id", "thread_id", "created_at",
        ),
        Index(
            "ix_client_messages_to_contact",
            "to_contact_id",
            postgresql_where="to_contact_id IS NOT NULL",
        ),
        # GIN full-text search en body_markdown declarado vía
        # ``CREATE INDEX ... USING gin (to_tsvector('spanish', body_markdown))``
        # en migración. Aquí sólo dejamos el sentinel vía Index sin op_class
        # para que Alembic no autogenere btree incompatible.
        CheckConstraint(
            f"from_role IN {FROM_ROLE_VALUES}",
            name="ck_client_messages_from_role",
        ),
        CheckConstraint(
            "email_forward_status IS NULL OR email_forward_status IN "
            f"{EMAIL_FORWARD_STATUS_VALUES}",
            name="ck_client_messages_email_forward_status",
        ),
    )

    # Tenant context
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Threading
    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False,
        doc=(
            "UUID que agrupa mensajes relacionados (conversación). El "
            "primer mensaje genera thread_id nuevo; respuestas reusan."
        ),
    )

    # Sender
    from_role: Mapped[str] = mapped_column(String(16), nullable=False)
    # 'client' | 'admin'
    from_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False,
        doc=(
            "UUID del sender. NO es FK porque puede apuntar a auth_users "
            "(si from_role='admin') o client_users (si from_role='client'). "
            "Coherencia validada en service layer."
        ),
    )

    # Recipient (M30 integration — composer admin selecciona contacto)
    to_contact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("client_contacts.id", ondelete="SET NULL"),
        nullable=True,
        doc=(
            "FK opcional client_contacts.id (M30). Cliente envía sin "
            "to_contact (mensaje al admin general). Admin responde con "
            "to_contact específico → auto-log interaction M30."
        ),
    )

    # Body
    body_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    body_html: Mapped[str | None] = mapped_column(
        Text,
        doc=(
            "HTML sanitizado server-side (rehype-sanitize en service layer). "
            "Prefiere render frontend desde body_markdown; este campo es "
            "fallback para emails out-of-band y previews."
        ),
    )

    # Read state (bidireccional)
    is_read_by_admin: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false",
    )
    is_read_by_client: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false",
    )

    # Email forward (out-of-band notification)
    forwarded_to_email: Mapped[str | None] = mapped_column(String(320))
    forwarded_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    email_forward_status: Mapped[str | None] = mapped_column(String(16))
    # NULL | 'pending' | 'sent' | 'failed' | 'skipped'

    # Relationships
    attachments: Mapped[list["ClientMessageAttachment"]] = relationship(
        back_populates="message",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ClientMessageAttachment(FullMixin, Base):
    """Adjunto de mensaje en MinIO bucket ``fulkro-client-messages``.

    Validaciones BD:
      - ``size_bytes < 10 MB`` (CHECK 10485760).
      - ``mime_type`` whitelist (CHECK enum-like contra ALLOWED_MIME_TYPES).

    Validaciones service layer (defensa profunda):
      - Re-check size_bytes y mime_type pre-upload presigned URL.
      - Re-check post-upload mediante HEAD MinIO (defensa contra spoofing
        del cliente que firma el upload presigned URL).

    Lifecycle:
      - Celery task `cleanup_expired_attachments` borra objects MinIO con
        ``uploaded_at + signed_url_ttl_seconds < now()`` semanalmente
        (plan v4.2 6.15).
    """

    __tablename__ = "client_message_attachments"
    __table_args__ = (
        Index(
            "ix_client_message_attachments_message",
            "message_id",
        ),
        CheckConstraint(
            f"size_bytes <= {MAX_ATTACHMENT_BYTES}",
            name="ck_client_message_attachments_size_max_10mb",
        ),
        CheckConstraint(
            "mime_type IN " + str(tuple(ALLOWED_MIME_TYPES)),
            name="ck_client_message_attachments_mime_whitelist",
        ),
    )

    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("client_messages.id", ondelete="CASCADE"),
        nullable=False,
    )

    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    minio_bucket: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=DEFAULT_MINIO_BUCKET,
        server_default=DEFAULT_MINIO_BUCKET,
    )
    minio_object_key: Mapped[str] = mapped_column(String(512), nullable=False)

    signed_url_ttl_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=DEFAULT_SIGNED_URL_TTL_SECONDS,
        server_default=str(DEFAULT_SIGNED_URL_TTL_SECONDS),
    )

    uploaded_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        doc=(
            "Timestamp del PUT exitoso al MinIO (vs created_at row insert). "
            "NULL hasta que el upload presigned URL se complete y el "
            "service marque uploaded_at via callback o HEAD verify."
        ),
    )

    # Relationships
    message: Mapped["ClientMessage"] = relationship(
        back_populates="attachments",
    )
