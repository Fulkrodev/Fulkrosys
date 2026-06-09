"""Motor 25 - Project lifecycle and archival."""
import uuid
from datetime import date, datetime

from sqlalchemy import ForeignKey, Integer, String, Text, BigInteger, Date, text
from sqlalchemy.dialects.postgresql import ARRAY, UUID, JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class ProjectLifecycleState(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "project_lifecycle_states"
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    state: Mapped[str] = mapped_column(String(50), nullable=False)
    entered_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    entered_by: Mapped[str | None] = mapped_column(String(255))
    previous_state: Mapped[str | None] = mapped_column(String(50))
    reason: Mapped[str | None] = mapped_column(Text)
    metadata_extra: Mapped[dict | None] = mapped_column(JSONB)


class ArchivedProject(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "archived_projects"
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), nullable=False)
    client_nif: Mapped[str | None] = mapped_column(String(20))
    client_name: Mapped[str | None] = mapped_column(String(255))
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    project_name: Mapped[str | None] = mapped_column(String(255))
    archive_started_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    archive_completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    archive_zip_path: Mapped[str | None] = mapped_column(String(500))
    archive_zip_hash_sha256: Mapped[str | None] = mapped_column(String(64))
    archive_zip_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    manifest: Mapped[dict | None] = mapped_column(JSONB)
    signed_by: Mapped[str | None] = mapped_column(String(255))
    signature_ed25519: Mapped[str | None] = mapped_column(Text)
    cold_storage_location: Mapped[str | None] = mapped_column(String(500))
    retention_until: Mapped[date | None] = mapped_column(Date)
    purge_scheduled_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    purged_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    # --- Motor 25 additions (wrapper ArchivePackage) ---
    retention_years: Mapped[int | None] = mapped_column(default=6)
    estado: Mapped[str | None] = mapped_column(String(20), default="created")
    # "created" | "verified" | "purged"
    documents_count: Mapped[int | None] = mapped_column(default=0)
    evidence_count: Mapped[int | None] = mapped_column(default=0)


class ProjectExport(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "project_exports"
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    export_type: Mapped[str | None] = mapped_column(String(50))
    exported_by: Mapped[str | None] = mapped_column(String(255))
    export_zip_path: Mapped[str | None] = mapped_column(String(500))
    export_zip_hash: Mapped[str | None] = mapped_column(String(64))
    export_zip_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    exported_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))


# ══════════════════════════════════════════════════════════════════════
# M25 Paso 4 — lifecycle events + archived backups (cierre sin retainer)
# ══════════════════════════════════════════════════════════════════════


class ProjectLifecycleEvent(UUIDPrimaryKeyMixin, Base):
    """Event log cliente-facing del ciclo de vida del proyecto.

    A diferencia de ``ProjectLifecycleState`` (transiciones de la state
    machine interna), este log guarda eventos mas amplios orientados al
    cliente: certificacion, oferta/decision retainer, grace period,
    backups generados, borrado, reactivacion.
    """

    __tablename__ = "project_lifecycle_events"

    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True,
    )
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("clients.id", ondelete="SET NULL"), nullable=True, index=True,
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    event_date: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )
    performed_by: Mapped[str | None] = mapped_column(String(50))
    metadata_jsonb: Mapped[dict | None] = mapped_column(JSONB)
    grace_period_days: Mapped[int | None] = mapped_column(Integer)
    backup_zip_path: Mapped[str | None] = mapped_column(String(500))
    backup_signature_ed25519: Mapped[str | None] = mapped_column(Text)
    backup_download_magic_link_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
    )
    notification_sent_to: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )


class ProjectArchivedBackup(UUIDPrimaryKeyMixin, Base):
    """ZIP descargable firmado con todo el contenido del proyecto cerrado.

    Se genera a los 210 dias de grace period (mes 7), con TTL de 60 dias
    para descarga del cliente. Tras expirar se elimina del almacenamiento
    en frio (MinIO).
    """

    __tablename__ = "project_archived_backups"

    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True,
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    zip_path: Mapped[str] = mapped_column(String(500), nullable=False)
    zip_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    ed25519_signature: Mapped[str] = mapped_column(Text, nullable=False)
    ed25519_public_key_pem: Mapped[str | None] = mapped_column(Text)
    manifest_jsonb: Mapped[dict] = mapped_column(JSONB, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False,
    )
    downloaded_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
    )
    download_count: Mapped[int] = mapped_column(
        Integer, server_default=text("0"), nullable=False, default=0,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )
