"""Motor 29 — Client Messaging: Schemas Pydantic.

Schemas in/out organizados por flujo:

CLIENTE (pool cliente):
  - ``ClientSendMessageBody`` — POST /client-portal/messages
  - ``ClientMessageListItem`` — list view threads del cliente
  - ``ClientMessageDetail`` — detalle thread con attachments

ADMIN (Marcos):
  - ``AdminSendMessageBody`` — POST /admin/messages (replier o new
    thread con to_contact_id opcional)
  - ``AdminMessageListItem`` — inbox admin con filtro client_id
  - ``AdminMessageDetail`` — detalle thread

ATTACHMENTS:
  - ``AttachmentUploadRequest`` / ``AttachmentUploadResponse`` —
    presigned URL upload flow
  - ``AttachmentOut`` — metadata attachment con signed download URL

UNREAD COUNTS:
  - ``UnreadCountResponse`` — badge sidebar admin/cliente

Pattern Pydantic v2 + ``ConfigDict(from_attributes=True)`` para
serialización ORM coherente con M30 schemas.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from backend.app.motors.m29_client_messaging.models import (
    ALLOWED_MIME_TYPES,
    MAX_ATTACHMENT_BYTES,
)


# ────────────────────────────────────────────────────────────────────
# TYPE ALIASES
# ────────────────────────────────────────────────────────────────────

FromRole = Literal["client", "admin"]
EmailForwardStatus = Literal["pending", "sent", "failed", "skipped"]


# ────────────────────────────────────────────────────────────────────
# CLIENTE — input
# ────────────────────────────────────────────────────────────────────


class ClientSendMessageBody(BaseModel):
    """Body POST /client-portal/messages — cliente envía nuevo mensaje.

    Si ``thread_id`` ausente: nuevo thread (service genera UUID).
    Si ``thread_id`` presente: reply en thread existente (service valida
    que el thread pertenece al cliente).
    """

    body_markdown: str = Field(..., min_length=1, max_length=20_000)
    thread_id: uuid.UUID | None = Field(
        default=None,
        description=(
            "UUID thread existing para responder. Omitir crea thread nuevo."
        ),
    )
    project_id: uuid.UUID | None = Field(
        default=None,
        description="Asociar mensaje a proyecto activo (opcional).",
    )


# ────────────────────────────────────────────────────────────────────
# ADMIN — input
# ────────────────────────────────────────────────────────────────────


class AdminSendMessageBody(BaseModel):
    """Body POST /admin/messages — Marcos envía/responde a cliente.

    Modos:
      - Nuevo thread con cliente: ``client_id`` requerido + sin ``thread_id``.
        Service genera ``thread_id`` nuevo.
      - Reply thread existente: ``thread_id`` requerido. ``client_id``
        derivado del thread.
      - Composer con M30 picker: ``to_contact_id`` opcional → auto-log
        interaction en timeline contacto.
    """

    body_markdown: str = Field(..., min_length=1, max_length=20_000)
    client_id: uuid.UUID | None = Field(
        default=None,
        description=(
            "Requerido si nuevo thread. Si reply, derivado del thread."
        ),
    )
    thread_id: uuid.UUID | None = Field(
        default=None,
        description="UUID thread existing para responder. Omitir = nuevo.",
    )
    project_id: uuid.UUID | None = None
    to_contact_id: uuid.UUID | None = Field(
        default=None,
        description=(
            "Contacto M30 destinatario (opcional). Si presente, service "
            "auto-loggea interaction_type='message' source_motor='m29' "
            "en timeline contacto."
        ),
    )


# ────────────────────────────────────────────────────────────────────
# ATTACHMENTS — upload flow
# ────────────────────────────────────────────────────────────────────


class AttachmentUploadRequest(BaseModel):
    """Request presigned URL upload — cliente o admin pre-PUT.

    Validación profunda:
      - ``mime_type`` ∈ whitelist (CHECK BD también)
      - ``size_bytes`` ≤ 10 MB (CHECK BD también)

    Service responde con presigned URL TTL 5 min para PUT directo MinIO.
    """

    filename: str = Field(..., min_length=1, max_length=255)
    mime_type: str = Field(..., min_length=1, max_length=100)
    size_bytes: int = Field(..., gt=0)

    @field_validator("mime_type")
    @classmethod
    def _validate_mime(cls, v: str) -> str:
        if v not in ALLOWED_MIME_TYPES:
            allowed = ", ".join(ALLOWED_MIME_TYPES)
            raise ValueError(
                f"MIME type '{v}' no permitido. Whitelist: {allowed}"
            )
        return v

    @field_validator("size_bytes")
    @classmethod
    def _validate_size(cls, v: int) -> int:
        if v > MAX_ATTACHMENT_BYTES:
            raise ValueError(
                f"size_bytes {v} excede límite {MAX_ATTACHMENT_BYTES} "
                f"(10 MB). Comprime o divide el archivo."
            )
        return v


class AttachmentUploadResponse(BaseModel):
    """Response presigned URL listo para PUT directo MinIO."""

    attachment_id: uuid.UUID
    upload_url: str = Field(
        description="Presigned PUT URL TTL 5 min al bucket."
    )
    upload_method: str = Field(default="PUT")
    upload_headers: dict[str, str] = Field(
        default_factory=dict,
        description="Headers requeridos por presigned URL (incl Content-Type).",
    )


class AttachmentOut(BaseModel):
    """Metadata attachment + signed download URL."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    mime_type: str
    size_bytes: int
    download_url: str | None = Field(
        default=None,
        description=(
            "Signed GET URL TTL signed_url_ttl_seconds. None si no se ha "
            "completado upload (uploaded_at IS NULL)."
        ),
    )
    uploaded_at: datetime | None = None


# ────────────────────────────────────────────────────────────────────
# OUTPUT — message detail + list items
# ────────────────────────────────────────────────────────────────────


class MessageOut(BaseModel):
    """Mensaje individual con attachments + flags read state.

    Vista compartida cliente/admin (campos sensibles solo populated en
    contexto admin: ``forwarded_to_email``, ``email_forward_status``).
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    thread_id: uuid.UUID
    client_id: uuid.UUID
    project_id: uuid.UUID | None = None
    from_role: FromRole
    from_user_id: uuid.UUID
    to_contact_id: uuid.UUID | None = None
    body_markdown: str
    body_html: str | None = None
    is_read_by_admin: bool
    is_read_by_client: bool
    forwarded_to_email: str | None = None
    forwarded_at: datetime | None = None
    email_forward_status: EmailForwardStatus | None = None
    created_at: datetime
    attachments: list[AttachmentOut] = Field(default_factory=list)


class ThreadSummary(BaseModel):
    """Resumen thread (ultimo mensaje + counts) para list views.

    Cliente ve sus propios threads (filtrados por client_id).
    Admin ve todos con filtros opcionales (client_id, contact_id).
    """

    model_config = ConfigDict(from_attributes=True)

    thread_id: uuid.UUID
    client_id: uuid.UUID
    last_message_id: uuid.UUID
    last_message_excerpt: str = Field(
        description="Primeros 200 chars de body_markdown del último mensaje."
    )
    last_message_at: datetime
    last_message_from_role: FromRole
    total_messages: int
    unread_for_admin: int = Field(
        description="Mensajes con is_read_by_admin=False. Solo populated "
                    "en contexto admin response."
    )
    unread_for_client: int = Field(
        description="Mensajes con is_read_by_client=False. Solo populated "
                    "en contexto cliente response."
    )
    has_attachments: bool = Field(
        default=False,
        description="True si algún mensaje del thread tiene attachments.",
    )
    last_to_contact_id: uuid.UUID | None = None


# ────────────────────────────────────────────────────────────────────
# UNREAD COUNT — badge sidebar
# ────────────────────────────────────────────────────────────────────


class UnreadCountResponse(BaseModel):
    """Badge sidebar (admin /admin/messages/unread-count + cliente
    /client-portal/messages/unread-count)."""

    unread_total: int = Field(ge=0)
    unread_threads: int = Field(
        ge=0,
        description="Threads con al menos 1 mensaje no leído.",
    )


# ────────────────────────────────────────────────────────────────────
# MARK READ
# ────────────────────────────────────────────────────────────────────


class MarkReadResponse(BaseModel):
    """Response POST /messages/{id}/mark-read — confirma cambio idempotente."""

    message_id: uuid.UUID
    is_read_by_admin: bool
    is_read_by_client: bool
