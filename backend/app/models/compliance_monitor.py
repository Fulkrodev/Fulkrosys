"""SAN-E v3.MB-9.bis atom 9.bis.6 — FULKRO Self-Monitoring System models.

Three tables backing the autonomous compliance verification subsystem:

- ``compliance_checks``: registry of 17 named checks (daily/weekly/monthly/
  quarterly cadence). Each row is the *latest* state of a named check. The
  ``status`` column is the semaphore (``green``/``yellow``/``red``).
- ``compliance_alerts``: append-only alert ledger. Created when a check
  transitions to ``yellow`` or ``red``. Resolved when remediated.
- ``compliance_reports``: weekly/monthly status report artifacts.
  ``storage_mode`` is ``desktop`` in development and ``minio`` in
  production (see ``reports_service.ComplianceReportsService``).

All tables are platform-global (no project_id, no RLS) — they describe the
FULKRO platform itself, not cliente data. Admin-only access via
``require_owner`` (Marcos / future co-DPO).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


# ── Frequency / severity / status string enums ──────────────────────────
# Stored as String(20) for forward compatibility (no Postgres ENUM type, so
# rolling out new cadences or severities does not need a migration).

FREQUENCY_DAILY = "daily"
FREQUENCY_WEEKLY = "weekly"
FREQUENCY_MONTHLY = "monthly"
FREQUENCY_QUARTERLY = "quarterly"

SEVERITY_HIGH = "high"
SEVERITY_MEDIUM = "medium"
SEVERITY_LOW = "low"

STATUS_GREEN = "green"
STATUS_YELLOW = "yellow"
STATUS_RED = "red"
STATUS_UNKNOWN = "unknown"  # before first run

ALERT_OPEN = "open"
ALERT_RESOLVED = "resolved"
ALERT_ACKNOWLEDGED = "acknowledged"


class ComplianceCheck(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Latest state of a named compliance check.

    ``check_name`` is the stable identifier referenced by the check function
    registry in ``m_compliance_monitor.checks``. Each name corresponds to
    exactly one row (unique constraint enforced at app level via
    ``ComplianceMonitorService.upsert_check``).
    """

    __tablename__ = "compliance_checks"

    check_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    frequency: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    severity_threshold: Mapped[str] = mapped_column(String(20), default=SEVERITY_MEDIUM)
    status: Mapped[str] = mapped_column(String(20), default=STATUS_UNKNOWN, index=True)
    last_run_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    next_run_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), index=True)
    last_result: Mapped[dict | None] = mapped_column(JSONB)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[str | None] = mapped_column(Text)
    regulatory_basis: Mapped[str | None] = mapped_column(String(255))


class ComplianceAlert(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Append-only alert ledger.

    Created by ``ComplianceMonitorService.run_check`` when a check returns a
    non-green status (severity respected). Resolved manually by Marcos via
    admin UI, or automatically when the same check returns green on the
    next run (``auto_resolved=True``).
    """

    __tablename__ = "compliance_alerts"

    check_id: Mapped[str] = mapped_column(
        ForeignKey("compliance_checks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    check_name: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default=ALERT_OPEN, nullable=False, index=True
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict | None] = mapped_column(JSONB)
    triggered_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, index=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    resolved_by: Mapped[str | None] = mapped_column(String(255))
    resolution_note: Mapped[str | None] = mapped_column(Text)
    auto_resolved: Mapped[bool] = mapped_column(default=False, nullable=False)
    email_sent_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))


class ComplianceReport(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Status report artifacts (weekly digest, monthly review).

    ``storage_mode``:
        - ``desktop``: file written to Desktop folder (development env)
        - ``minio``: object stored in MinIO bucket (production env)
        - ``inline``: only metadata + body kept in DB (e.g. CI tests)

    ``storage_path`` is the absolute filesystem path (desktop) or the
    bucket/key tuple (minio). ``signed_url`` is the pre-signed download URL
    emailed to Marcos (minio only).
    """

    __tablename__ = "compliance_reports"

    report_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    period_start: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    summary: Mapped[dict] = mapped_column(JSONB, nullable=False)
    body_markdown: Mapped[str | None] = mapped_column(Text)
    storage_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    storage_path: Mapped[str | None] = mapped_column(String(1000))
    signed_url: Mapped[str | None] = mapped_column(String(2000))
    signed_url_expires_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    email_sent_to: Mapped[str | None] = mapped_column(String(255))
    email_sent_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    generated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, index=True
    )
