"""BIA (Business Impact Analysis) models · SAN-C MB-11.5.

Estructura analysis BIA per servicio crítico del proyecto:
RTO/RPO targets + impact financial diario + stakeholders + recursos mínimos.
"""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, String, Numeric, Integer
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class BiaAnalysis(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "bia_analyses"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True,
    )
    service_name: Mapped[str] = mapped_column(String(200), nullable=False)
    rto_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    rpo_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    daily_impact_eur: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    stakeholders: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    minimum_resources: Mapped[dict | None] = mapped_column(JSONB)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
    )
