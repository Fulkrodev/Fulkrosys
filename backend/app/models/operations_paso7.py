"""Modelos Paso 7 — email_log + normativa_alerts.

Modulo separado para no tocar ``backend/app/models/operations.py``
(que ya existe con operaciones legacy) y mantener los nuevos
modelos del Paso 7 aislados.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, UUIDPrimaryKeyMixin


class EmailLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "email_log"

    recipient: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    template_used: Mapped[str | None] = mapped_column(String(120), index=True)
    body_html: Mapped[str | None] = mapped_column(Text)
    body_text: Mapped[str | None] = mapped_column(Text)
    backend_used: Mapped[str] = mapped_column(String(30), nullable=False)
    queued_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )
    sent_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    delivery_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="queued",
    )
    message_id: Mapped[str | None] = mapped_column(String(255))
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    magic_link_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), index=True,
    )
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("clients.id", ondelete="SET NULL"), index=True,
    )
    metadata_jsonb: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )


class NormativaAlert(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "normativa_alerts"
    __table_args__ = (
        UniqueConstraint(
            "source", "source_item_id",
            name="uq_normativa_alerts_source_item",
        ),
    )

    source: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    source_url: Mapped[str | None] = mapped_column(String(1000))
    source_item_id: Mapped[str | None] = mapped_column(String(500))
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    detected_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    affected_measures_jsonb: Mapped[dict | None] = mapped_column(JSONB)
    affected_clients_jsonb: Mapped[dict | None] = mapped_column(JSONB)
    summary_llm: Mapped[str | None] = mapped_column(Text)
    classified_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    notification_sent_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="detected", index=True,
    )
    metadata_jsonb: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )
