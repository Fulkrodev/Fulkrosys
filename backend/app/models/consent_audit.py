"""SAN-E v3.MB-9.bis atom 9.bis.1 · Cookie consent audit log model.

``fulkro_consent_audit_log`` is an append-only ledger of every cookie
consent decision (initial accept, granular configure, revoke, 24-month
renewal trigger / renewal). It is the source of truth for the AEPD
inspection requirement under Art. 7.1 GDPR ("the controller shall be
able to demonstrate that the data subject has consented").

The row is created in two situations:
- Anonymous visitor on fulkro.es: ``user_id`` is NULL,
  ``anonymous_session_id`` is the browser-side cookie UUID.
- Authenticated cliente: ``user_id`` is the ClientUser.id and
  ``tenant_client_id`` is the owning Client (denormalised per
  LECCIÓN tenant_client_id pattern in atom 9.bis.2).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import INET, JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, UUIDPrimaryKeyMixin


ACTION_INITIAL = "initial_consent"
ACTION_MODIFIED = "user_modified"
ACTION_REVOKED = "user_revoked"
ACTION_RENEWAL_TRIGGER = "renewal_24m_trigger"
ACTION_RENEWAL_CONFIRMED = "renewal_24m_confirmed"


class FulkroConsentAuditLog(UUIDPrimaryKeyMixin, Base):
    """Append-only audit ledger for cookie consent decisions."""

    __tablename__ = "fulkro_consent_audit_log"

    user_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("client_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    anonymous_session_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    tenant_client_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="SET NULL"),
        nullable=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, index=True
    )
    action_type: Mapped[str] = mapped_column(String(40), nullable=False)
    old_state: Mapped[dict | None] = mapped_column(JSONB)
    new_state: Mapped[dict] = mapped_column(JSONB, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(Text)
    page_url: Mapped[str | None] = mapped_column(Text)
