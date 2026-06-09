"""ChatThread + ChatMessage models (ADR-038 SAN-D MB-14.5).

Pivot SSE+REST en lugar WebSocket (DEC-MB14-CHAT-WEBSOCKET-PIVOT
ADR-038 Deferrables): mensajes via POST + SSE event push real-time.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, FullMixin


class ChatThread(FullMixin, Base):
    """Chat thread cliente↔admin · 1 thread per proyecto típico."""

    __tablename__ = "chat_threads"
    __table_args__ = (
        Index(
            "ix_chat_threads_project_status",
            "project_id", "status",
        ),
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
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="open", nullable=False,
    )
    # SLA tracking · admin response time <2h target
    last_client_message_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    last_admin_response_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    messages_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0"),
    )


class ChatMessage(FullMixin, Base):
    """Mensaje individual en chat thread · sender_type cliente|admin|system."""

    __tablename__ = "chat_messages"
    __table_args__ = (
        Index(
            "ix_chat_messages_thread_created",
            "thread_id", "created_at",
        ),
    )

    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_threads.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    sender_type: Mapped[str] = mapped_column(String(20), nullable=False)
    sender_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_jsonb: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # CLUSTER 5 Phase 5A delta · read tracking · NULL = unread by counterparty.
    # Cliente reads admin messages → mark-read endpoint sets read_at; admin
    # reads client messages → mark-read endpoint sets read_at. Partial index
    # ix_chat_messages_unread optimizes inbox unread counter realtime.
    read_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
