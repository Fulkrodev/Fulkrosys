"""Per-norma compliance report model (mini-atom 3).

Each row is one historical snapshot of FULKRO's compliance posture against
a registered ``NormaModule`` (RGPD, NIS2, ISO 27001, ...). Reports are
generated periodically by ``ComplianceNormaReportsService`` and consumed
by:

- Admin UI ``/admin/compliance/norma-reports``  (history + trends).
- Trust Center public ``/api/v1/legal/compliance/status``  (latest score).
- Self-Monitoring alerts when ``compliance_score < 85``.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class FulkroComplianceNormaReport(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "fulkro_compliance_norma_reports"

    norma_key: Mapped[str] = mapped_column(String(50), nullable=False)
    norma_name: Mapped[str] = mapped_column(String(200), nullable=False)
    period_start: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    period_end: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    compliance_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    checks_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    checks_passed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    checks_warning: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    checks_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    report_md_content: Mapped[str] = mapped_column(Text, nullable=False)
    report_json_content: Mapped[dict] = mapped_column(JSONB, nullable=False)
    storage_path_dev: Mapped[str | None] = mapped_column(Text)
    storage_path_prod: Mapped[str | None] = mapped_column(Text)
    email_sent_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    generated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    reviewed_by_marcos_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    reviewed_marcos_notes: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index(
            "ix_norma_reports_norma_period",
            "norma_key",
            "period_end",
        ),
        Index(
            "ix_norma_reports_compliance_score",
            "compliance_score",
        ),
    )
