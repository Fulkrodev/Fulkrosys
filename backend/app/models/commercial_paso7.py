"""Modelos Paso 7 final — commercial_discounts + retainer_reports."""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, UUIDPrimaryKeyMixin


class CommercialDiscount(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "commercial_discounts"

    client_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    discount_type: Mapped[str] = mapped_column(String(40), nullable=False)
    amount: Mapped[float | None] = mapped_column(Numeric(10, 2))
    amount_pct: Mapped[float | None] = mapped_column(Numeric(5, 2))
    applicable_to: Mapped[str] = mapped_column(String(40), nullable=False)
    granted_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )
    granted_by: Mapped[str | None] = mapped_column(String(50))
    granted_reason: Mapped[str | None] = mapped_column(Text)
    used_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    used_in_contract_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("contracts.id", ondelete="SET NULL"), index=True,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="available",
    )
    source_invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("invoices.id", ondelete="SET NULL"),
    )
    metadata_jsonb: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )


class RetainerReport(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "retainer_reports"
    __table_args__ = (
        UniqueConstraint(
            "client_id", "report_type", "periodo_year", "periodo_quarter",
            name="uq_retainer_reports_client_periodo",
        ),
    )

    client_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), index=True,
    )
    report_type: Mapped[str] = mapped_column(String(30), nullable=False)
    periodo_year: Mapped[int] = mapped_column(Integer, nullable=False)
    periodo_quarter: Mapped[int | None] = mapped_column(Integer)
    periodo_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    periodo_fin: Mapped[date] = mapped_column(Date, nullable=False)
    kpis_jsonb: Mapped[dict | None] = mapped_column(JSONB)
    payload_jsonb: Mapped[dict | None] = mapped_column(JSONB)
    generated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )
    docx_path: Mapped[str | None] = mapped_column(String(500))
    pdf_path: Mapped[str | None] = mapped_column(String(500))
    signature_ed25519: Mapped[str | None] = mapped_column(Text)
    hash_sha256: Mapped[str | None] = mapped_column(String(64))
    sent_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    magic_link_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="generated",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )
