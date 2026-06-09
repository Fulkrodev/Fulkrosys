"""ClientNotification model (SAN-E v3.MB-4.bis3 · ADR-020 v3 IMPLEMENTED FULLY).

Reemplaza magic_link cliente · cliente con cuenta portal recibe notificaciones
en /client-portal/inbox · click target_url naviga a portal page apropiada.

Types soportados:
- evidence_request · acta_review · retainer_offer · retainer_reconsideration
- onboarding_ready · generic_alert · invoice_review · risk_validation
- compliance_confirmation · meeting_invite · etc

Priorities: low · normal · high · urgent.

Emisor: motors backend via NotificationService.emit_client_notification().
Audit log via emitted_by_motor (m05 · m18 · m25 · etc).
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base


class ClientNotification(Base):
    __tablename__ = "client_notifications"
    __table_args__ = (
        Index("ix_client_notif_created", "created_at"),
        Index("ix_client_notif_project", "project_id"),
        Index("ix_client_notif_type", "type"),
        Index("ix_client_notif_unread", "client_user_id", "read_at"),
        Index("ix_client_notif_user", "client_user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    client_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("client_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    target_url: Mapped[str] = mapped_column(String(512), nullable=False)
    priority: Mapped[str] = mapped_column(
        String(16), nullable=False, default="normal", server_default="normal",
    )
    payload_json: Mapped[dict | None] = mapped_column(JSONB)
    emitted_by_motor: Mapped[str] = mapped_column(String(32), nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    dismissed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    actioned_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow,
    )
