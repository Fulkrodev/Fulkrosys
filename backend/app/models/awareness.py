"""Awareness training models · SAN-C MB-11.5.

Tracking sesiones formación seguridad + asistencia + coverage cliente.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class AwarenessSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "awareness_sessions"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    scheduled_date: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False,
    )
    topics: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    mandatory: Mapped[bool] = mapped_column(Boolean, default=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
    )


class AwarenessAttendance(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "awareness_attendance"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("awareness_sessions.id"),
        nullable=False,
        index=True,
    )
    attendee_email: Mapped[str] = mapped_column(String(200), nullable=False)
    method: Mapped[str] = mapped_column(String(20), nullable=False)
    """in_person · virtual · recorded."""
    attended_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False,
    )
    magic_link_token: Mapped[str | None] = mapped_column(String(100))
