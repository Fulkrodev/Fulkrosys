"""M31 WhatsApp Business ORM models · atom 8.1."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint, ForeignKey, Index, Integer, String, Text, text,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base


class WhatsAppThread(Base):
    """1:1 cliente↔Marcos thread · same pattern chat_threads ADR-038."""

    __tablename__ = "whatsapp_threads"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'closed')",
            name="ck_whatsapp_threads_status",
        ),
        Index("ix_whatsapp_threads_project_id", "project_id"),
        Index(
            "ix_whatsapp_threads_active_inbound",
            "status", text("last_inbound_at DESC"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    client_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("client_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'active'"),
    )
    last_outbound_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
    )
    last_inbound_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
    )
    last_message_preview: Mapped[str | None] = mapped_column(String(500))
    messages_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0"),
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"),
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
    )


class WhatsAppMessage(Base):
    """Single WA message · outbound/inbound with delivery tracking."""

    __tablename__ = "whatsapp_messages"
    __table_args__ = (
        CheckConstraint(
            "direction IN ('outbound', 'inbound')",
            name="ck_whatsapp_messages_direction",
        ),
        CheckConstraint(
            "sender_type IN ('system', 'marcos', 'cliente')",
            name="ck_whatsapp_messages_sender",
        ),
        Index(
            "ix_whatsapp_messages_thread_sent",
            "thread_id", text("sent_at DESC"),
        ),
        Index(
            "ix_whatsapp_messages_unread_inbound",
            "thread_id",
            postgresql_where=text("direction = 'inbound' AND read_at IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("whatsapp_threads.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    sender_type: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    whatsapp_message_id: Mapped[str | None] = mapped_column(String(120))
    sent_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"),
    )
    delivered_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
    )
    read_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
    )
    failed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
    )
    failure_reason: Mapped[str | None] = mapped_column(String(500))
    metadata_jsonb: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
    )


class WhatsAppCriticalEventRouting(Base):
    """Per-event tier matrix routing (Q5.A+tier cement)."""

    __tablename__ = "whatsapp_critical_events_routing"
    __table_args__ = (
        CheckConstraint(
            "tier_basica_route IN ('whatsapp', 'email', 'sse_only', 'digest', 'silent')",
            name="ck_wa_routing_basica",
        ),
        CheckConstraint(
            "tier_media_route IN ('whatsapp', 'email', 'sse_only', 'digest', 'silent')",
            name="ck_wa_routing_media",
        ),
        CheckConstraint(
            "tier_alta_route IN ('whatsapp', 'email', 'sse_only', 'digest', 'silent')",
            name="ck_wa_routing_alta",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    event_type: Mapped[str] = mapped_column(
        String(80), nullable=False, unique=True,
    )
    tier_basica_route: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'digest'"),
    )
    tier_media_route: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'whatsapp'"),
    )
    tier_alta_route: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'whatsapp'"),
    )
    template_es: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"),
    )
