"""SAN-E v3.MB-9.bis atom 9.bis.2 · Breach notification + erasure request models.

Two platform-global tables (no RLS, admin or cliente-scoped via FK):

- ``fulkro_breach_notifications``: Art. 33 GDPR breach register. 72h SLA
  starts at ``detected_at``. ``notification_status`` tracks the workflow
  state (pending → aepd_notified → clients_notified → closed_*).

- ``fulkro_erasure_requests``: Art. 17 GDPR cliente erasure workflow.
  ``client_user_id`` FK is preserved even after the cliente row is
  anonymised so the legal basis for retention can be audited.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


# Breach severity / status / erasure status string constants.
SEVERITY_LOW = "low"
SEVERITY_MEDIUM = "medium"
SEVERITY_HIGH = "high"
SEVERITY_CRITICAL = "critical"

BREACH_PENDING = "pending"
BREACH_AEPD_NOTIFIED = "aepd_notified"
BREACH_CLIENTS_NOTIFIED = "clients_notified"
BREACH_CLOSED_RESOLVED = "closed_resolved"
BREACH_CLOSED_NO_ACTION = "closed_no_action"

ERASURE_PENDING = "pending"
ERASURE_PROCESSING = "processing"
ERASURE_COMPLETED = "completed"
ERASURE_REJECTED_AUDIT = "rejected_audit_retention"


class FulkroBreachNotification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Art. 33 GDPR breach notification register."""

    __tablename__ = "fulkro_breach_notifications"

    breach_code: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False
    )
    detected_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, index=True
    )
    reported_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), index=True
    )
    notified_aepd_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    notified_clients_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    data_categories_affected: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )
    data_subjects_count: Mapped[int | None] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    root_cause: Mapped[str | None] = mapped_column(Text)
    containment_actions: Mapped[str | None] = mapped_column(Text)
    remediation_actions: Mapped[str | None] = mapped_column(Text)
    notification_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default=BREACH_PENDING, index=True
    )
    affected_client_user_ids: Mapped[list[str] | None] = mapped_column(
        ARRAY(String)
    )
    reporter_user_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True)
    )
    aepd_reference: Mapped[str | None] = mapped_column(String(100))


class FulkroErasureRequest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Art. 17 GDPR cliente erasure workflow."""

    __tablename__ = "fulkro_erasure_requests"

    client_user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("client_users.id"),
        nullable=False,
        index=True,
    )
    tenant_client_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id"),
        nullable=False,
    )
    requested_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    requester_reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default=ERASURE_PENDING, index=True
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    processed_by: Mapped[str | None] = mapped_column(String(255))
    tombstone_data: Mapped[dict | None] = mapped_column(JSONB)
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    audit_log_preserved: Mapped[bool] = mapped_column(
        nullable=False, default=True
    )
