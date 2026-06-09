"""Collaborative workspace (M20): docs, feed, chat, videocall sessions.

Workspace 1:1 con proyecto (unique constraint en project_id).
Files con SHA-256 obligatorio. Chat/feed append-only.
Videocall: solo modelo + state machine (LiveKit real = TODO futuro).

WorkspaceChatMessage.mensaje cifrado at-rest vía ``EncryptedText``
(Fernet local master key · ADR-032 implementada SAN-B.MB-3.ter.4).
"""
import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, SmallInteger, String, Text, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.encryption import EncryptedText
from backend.app.models.base import Base, FullMixin


class CollaborativeWorkspace(FullMixin, Base):
    __tablename__ = "collaborative_workspaces"
    __table_args__ = (
        UniqueConstraint("project_id", name="uq_workspace_project_id"),
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id"), nullable=False, index=True,
    )
    nombre: Mapped[str | None] = mapped_column(String(200))
    estado: Mapped[str | None] = mapped_column(String(20), default="active")
    # "active" → "archived" → "destroyed"
    config: Mapped[dict | None] = mapped_column(JSONB)
    # {"features": {"chat": true, "files": true, "feed": true, "videocall": false},
    #  "retention_days_post_close": 90}
    carpeta_docs_path: Mapped[str | None] = mapped_column(String(500))
    caducidad_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    livekit_room_id: Mapped[str | None] = mapped_column(String(100))
    feed_suscripciones: Mapped[dict | None] = mapped_column(JSONB)


class WorkspaceFile(FullMixin, Base):
    __tablename__ = "workspace_files"
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("collaborative_workspaces.id"), nullable=False, index=True,
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id"), index=True,
    )
    nombre: Mapped[str] = mapped_column(String(300), nullable=False)
    carpeta: Mapped[str | None] = mapped_column(String(500), default="/")
    # Ruta virtual: "/documentos/politicas/", "/evidencias/", etc.
    path: Mapped[str | None] = mapped_column(String(500))
    storage_path: Mapped[str | None] = mapped_column(String(500))  # MinIO reference
    tipo_mime: Mapped[str | None] = mapped_column(String(100))
    tamano_bytes: Mapped[int | None] = mapped_column(Integer, default=0)
    # Integridad
    hash_sha256: Mapped[str | None] = mapped_column(String(64))
    # Metadata
    version: Mapped[int | None] = mapped_column(Integer, default=1)
    subido_por: Mapped[str | None] = mapped_column(String(255))
    subido_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    versiones: Mapped[dict | None] = mapped_column(JSONB)
    estado: Mapped[str | None] = mapped_column(String(20), default="active")
    # "active", "archived", "deleted"


class WorkspaceFeedItem(FullMixin, Base):
    """Feed de actividad del workspace: hitos, documentos, evidencias, alertas."""
    __tablename__ = "workspace_feed_items"
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("collaborative_workspaces.id"), nullable=False, index=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id"), nullable=False, index=True,
    )
    tipo: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # "hito_completado" | "documento_generado" | "evidencia_aportada"
    # | "finding_detectado" | "tarea_completada" | "firma_pendiente"
    # | "comentario" | "alerta" | "reunion_programada"
    titulo: Mapped[str] = mapped_column(String(300), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    item_metadata: Mapped[dict | None] = mapped_column(JSONB)
    # {"entregable": "E-040", "link": "/projects/.../dda", "icono": "document"}
    autor: Mapped[str] = mapped_column(String(100), nullable=False, default="plataforma")
    # "marcos" | "plataforma" | "cliente"
    leido: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    leido_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))


class WorkspaceChatMessage(FullMixin, Base):
    """Mensajes del chat del workspace. Append-only (regla 11)."""
    __tablename__ = "workspace_chat_messages"
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("collaborative_workspaces.id"), nullable=False, index=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id"), nullable=False, index=True,
    )
    autor: Mapped[str] = mapped_column(String(200), nullable=False)
    autor_tipo: Mapped[str] = mapped_column(String(20), nullable=False, default="marcos")
    # "marcos" | "cliente" | "sistema"
    # Cifrado at-rest Fernet · transparente via EncryptedText TypeDecorator
    mensaje: Mapped[str] = mapped_column(EncryptedText, nullable=False)
    encryption_version: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default="1",
    )
    # Track key generation activa · soporta MultiFernet rotation
    adjunto_file_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    # FK lógica a workspace_files.id (sin constraint por simplicidad)
    respondiendo_a: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    # FK lógica a workspace_chat_messages.id (hilo de respuestas)


class VideocallSession(FullMixin, Base):
    """Sesión de videollamada. State machine sin LiveKit real (TODO futuro)."""
    __tablename__ = "videocall_sessions"
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("collaborative_workspaces.id"), nullable=False, index=True,
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id"), index=True,
    )
    estado: Mapped[str | None] = mapped_column(String(20), default="solicitada")
    # "solicitada" → "aceptada" → "en_curso" → "finalizada" | "cancelada"
    solicitada_por: Mapped[str | None] = mapped_column(String(100))
    participantes: Mapped[dict | None] = mapped_column(JSONB)
    solicitada_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    aceptada_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    iniciada_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    finalizada_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    duracion_minutos: Mapped[int | None] = mapped_column(Integer)
    livekit_room_name: Mapped[str | None] = mapped_column(String(200))
    grabacion_path: Mapped[str | None] = mapped_column(String(500))
    consentimiento_grabacion: Mapped[bool | None] = mapped_column(Boolean)
