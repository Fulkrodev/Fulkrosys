"""sub_processor_subscribers table (atom 9.bis.5).

Stores public email subscriptions to the sub-processor change notification
list (Art. 28.2 GDPR transparency obligation: data controllers must inform
the data exporter when new sub-processors are added). Public anonymous
subscription — no project_id, no auth.

The notification dispatch itself is implemented later (Marcos updates the
sub-processors MD → m_compliance_monitor.tasks fires a batch email). This
atom only stores the subscription intent + consent.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SubProcessorSubscriber(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Public email subscribers to sub-processor change notifications."""

    __tablename__ = "sub_processor_subscribers"

    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    consent_given_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    unsubscribed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    last_notified_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
