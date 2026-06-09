"""Modelos NotificationOrchestrator MB-16.1 (ADR-039).

- ``NotificationEvent`` audit immutable per evento despachado.
- ``NotificationPreference`` per ClientUser · canales + DND tz-aware
  + digest_mode.

Tablas migradas en ``sand_notif_events_001`` y ``sand_notif_prefs_001``.
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
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, FullMixin


VALID_NOTIFICATION_STATUSES = (
    "queued",
    "dispatching",
    "delivered",
    "failed",
    "suppressed_dnd",
)

VALID_DIGEST_MODES = ("immediate", "hourly", "daily")


class NotificationEvent(FullMixin, Base):
    """Audit immutable per evento dispatched por NotificationOrchestrator.

    Status lifecycle: queued → dispatching → delivered | failed |
    suppressed_dnd. ``channels_attempted`` lista canales intentados
    (ej. ``["email", "portal_sse"]``); ``channels_succeeded`` los que
    completaron OK; ``channels_failed`` los que fallaron con error
    capturado en ``error`` para diagnostic admin.

    ``email_log_id`` es soft reference a ``email_log`` (existing Paso 7
    audit) sin FK constraint para evitar acoplamiento. ``celery_task_id``
    permite traceability worker dispatch.

    Política inmutabilidad: rows NO se hard-delete. ``deleted_at`` solo
    para retention policy (compliance). Updates limitados a status
    transitions + metadata enrichment via orchestrator.
    """

    __tablename__ = "notification_events"
    __table_args__ = (
        CheckConstraint(
            f"status IN {VALID_NOTIFICATION_STATUSES}",
            name="ck_notification_events_status",
        ),
        Index(
            "ix_notification_events_recipient_created",
            "recipient_user_id",
            "created_at",
        ),
        Index(
            "ix_notification_events_project_created",
            "project_id",
            "created_at",
        ),
        Index(
            "ix_notification_events_status_created",
            "status",
            "created_at",
        ),
        Index(
            "ix_notification_events_event_type_created",
            "event_type",
            "created_at",
        ),
    )

    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    recipient_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("client_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
    )
    channels_attempted: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list,
    )
    channels_succeeded: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list,
    )
    channels_failed: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list,
    )
    payload_jsonb: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict,
    )
    template_used: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="queued",
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    celery_task_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True,
    )
    email_log_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )
    dispatched_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    delivered_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )


class NotificationPreference(FullMixin, Base):
    """Preferences per ClientUser · channels + DND timezone-aware + digest.

    UNIQUE constraint client_user_id garantiza 1 row per usuario.
    Defaults conservadores aplicados al insertar (factory function en
    orchestrator si row no existe).

    ``dnd_start_local`` / ``dnd_end_local`` formato ``HH:MM`` (24h
    local timezone). Si ambos ``None`` → sin DND (envíos siempre).
    Si ambos set → DND activo en ventana ``[start, end)`` inclusive
    para suppress respeto cliente. ``timezone`` IANA name (ej.
    ``Europe/Madrid``) para resolver conversión local↔UTC en check.

    ``digest_mode`` MVP solo ``immediate``. ``hourly`` / ``daily`` schema
    permitido (CheckConstraint) pero engine batch diferido a MB-19+
    (DEC-MB16-DIGEST-MODE-IMMEDIATE-ONLY).
    """

    __tablename__ = "notification_preferences"
    __table_args__ = (
        CheckConstraint(
            f"digest_mode IN {VALID_DIGEST_MODES}",
            name="ck_notification_prefs_digest_mode",
        ),
        CheckConstraint(
            "(dnd_start_local IS NULL AND dnd_end_local IS NULL) OR "
            "(dnd_start_local IS NOT NULL AND dnd_end_local IS NOT NULL)",
            name="ck_notification_prefs_dnd_pair",
        ),
        Index(
            "ix_notification_preferences_client_user",
            "client_user_id",
        ),
    )

    client_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("client_users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    email_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
    )
    portal_sse_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
    )
    dnd_start_local: Mapped[str | None] = mapped_column(
        String(5), nullable=True,
    )
    dnd_end_local: Mapped[str | None] = mapped_column(
        String(5), nullable=True,
    )
    timezone: Mapped[str] = mapped_column(
        String(50), nullable=False, default="Europe/Madrid",
    )
    digest_mode: Mapped[str] = mapped_column(
        String(20), nullable=False, default="immediate",
    )
    # CLUSTER 5 Phase 5E delta · WhatsApp granular toggle + per-event opt-outs.
    # whatsapp_enabled duplicates m31.ClientUser.whatsapp_opt_in_at intentional
    # · permite cliente disable temporal sin borrar opt-in M31 flow.
    # event_opt_outs key=event_type value=bool · TRUE = silence.
    whatsapp_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
    )
    event_opt_outs: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict,
    )


__all__ = [
    "NotificationEvent",
    "NotificationPreference",
    "VALID_NOTIFICATION_STATUSES",
    "VALID_DIGEST_MODES",
]
