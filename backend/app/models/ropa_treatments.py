"""SAN-E v3.MB-9.bis atom 9.bis.3 · fulkro_ropa_treatments model.

Article 30 GDPR (Record of Processing Activities) — FULKRO platform self.
Stores the 10 declared treatments that FULKRO performs as data processor
on behalf of clientes (and a few as controller of its own data).

The Trust Center sub_processors_count reads ``is_sub_processor=true`` rows
(unique processor count). The Self-Monitoring check ``ropa_review_due``
reads ``last_reviewed_at`` for annual review compliance.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import ARRAY, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class FulkroRoPATreatment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Record of Processing Activity (Art. 30 GDPR) for one FULKRO treatment."""

    __tablename__ = "fulkro_ropa_treatments"

    treatment_code: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False
    )
    treatment_name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    legal_basis: Mapped[str] = mapped_column(String(100), nullable=False)
    data_categories: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )
    data_subjects_categories: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )
    recipients: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    transfers_outside_eu: Mapped[bool] = mapped_column(
        nullable=False, default=False
    )
    transfer_safeguards: Mapped[str | None] = mapped_column(Text)
    retention_period: Mapped[str] = mapped_column(String(200), nullable=False)
    security_measures: Mapped[str] = mapped_column(Text, nullable=False)
    processor_name: Mapped[str | None] = mapped_column(String(200))
    is_sub_processor: Mapped[bool] = mapped_column(nullable=False, default=False)
    dpa_signed: Mapped[bool] = mapped_column(nullable=False, default=False)
    dpa_expires_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    controller_dpo: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        default="Marcos Mata García · dpo@fulkro.es",
    )
    last_reviewed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, index=True
    )
