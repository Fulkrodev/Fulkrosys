"""AEPD notifications model · SAN-C MB-11.2.

Tracking notificaciones AEPD art.33-34 RGPD (deadline 72h):
incident_id opcional (permite evaluaciones hipotéticas sin incidente
formal aún registrado en incidents) + decision_tree_path JSONB para
audit razonamiento + notification_status lifecycle.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class AepdNotification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "aepd_notifications"
    __table_args__ = (
        Index("ix_aepd_notifications_incident_id", "incident_id"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id"),
        nullable=False,
        index=True,
    )
    incident_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("incidents.id"),
        nullable=True,
    )
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    """low · medium · high · critical."""
    requires_notification: Mapped[bool] = mapped_column(Boolean, nullable=False)
    notify_subjects: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
    )
    deadline_hours: Mapped[int | None] = mapped_column(Integer)
    decision_tree_path: Mapped[list[str] | None] = mapped_column(JSONB)
    notification_status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False,
    )
    """pending · sent · acknowledged · cancelled."""
    aepd_reference: Mapped[str | None] = mapped_column(String(100))
    detected_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
    )
