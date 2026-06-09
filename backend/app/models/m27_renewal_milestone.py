"""M27 Renewal Campaign Milestones · ADR-046 v3 SAN-E.MB-3.D.

Sub-tabla relacional 1:N (renewal_campaigns 1 - N renewal_campaign_milestones).
8 milestones default seed pre-renovacion ENS.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, FullMixin


MILESTONE_STATUSES = ("pendiente", "en_progreso", "completado", "bloqueado", "no_aplica")

DEFAULT_MILESTONES = [
    {"code": "prep",                "label": "Preparacion campana renovacion",      "offset_weeks": -16},
    {"code": "review_docs",         "label": "Revision documentacion ENS",          "offset_weeks": -14},
    {"code": "gap_close",            "label": "Cierre gaps detectados",              "offset_weeks": -12},
    {"code": "pentest_refresh",     "label": "Pentest refresh + correccion",        "offset_weeks": -10},
    {"code": "evidencia_refresh",   "label": "Refresh evidencias caducadas",        "offset_weeks": -8},
    {"code": "dossier",              "label": "Generacion dossier auditoria",        "offset_weeks": -6},
    {"code": "auditor_contact",     "label": "Contacto auditor ENAC + briefing",    "offset_weeks": -4},
    {"code": "audit_window",         "label": "Ventana auditoria ENAC",              "offset_weeks": 0},
]


class RenewalCampaignMilestone(FullMixin, Base):
    __tablename__ = "renewal_campaign_milestones"
    __table_args__ = (
        UniqueConstraint(
            "campaign_id", "milestone_code",
            name="uq_renewal_milestone_campaign_code",
        ),
        Index(
            "ix_renewal_milestone_campaign",
            "campaign_id",
        ),
        CheckConstraint(
            "status IN ('pendiente','en_progreso','completado','bloqueado','no_aplica')",
            name="ck_renewal_milestone_status",
        ),
    )

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("renewal_campaigns.id", ondelete="CASCADE"),
        nullable=False,
    )
    milestone_code: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    due_date: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pendiente",
    )
    responsable: Mapped[str | None] = mapped_column(String(255), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
