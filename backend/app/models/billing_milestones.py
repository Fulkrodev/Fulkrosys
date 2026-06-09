"""Modelos MB-18 auto-billing milestone + retainer health (ADR-040).

- ``ContractMilestone`` audit per milestone con lifecycle + tracking
  reconciliación manual.
- ``RetainerHealthSignal`` snapshot per scan ChurnPredictor heurístico.

Tablas migradas en ``sand_billing_milestones_001`` y
``sand_retainer_health_001``.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, FullMixin


VALID_MILESTONE_STATUSES = (
    "pending",
    "billed",
    "invoice_issued",
    "payment_pending",
    "paid",
    "disputed",
    "refunded",
)

VALID_BILLING_TRIGGERS = (
    "phase_complete",
    "phase_start",
    "manual",
    "scheduled_date",
)

VALID_RISK_LEVELS = ("low", "medium", "high", "critical")


class ContractMilestone(FullMixin, Base):
    """Tracking persistente per milestone contract.

    Enriquece ``MilestoneSpec`` NamedTuple existing
    (``backend/app/core/pricing/rules.py:75``) con lifecycle +
    reconciliación manual:
    - ``billing_trigger`` controla cuándo auto-bill
      (``phase_complete`` MVP)
    - ``status`` lifecycle: pending → billed → invoice_issued →
      payment_pending → paid | disputed | refunded
    - ``paid_marked_by_user_id`` + ``payment_reference`` audit Marcos
      reconciliación
    - ``blocking_next_phase`` controla auto-advance projects.fase
      post-payment

    UNIQUE (contract_id, milestone_index) garantiza idempotencia
    MilestoneFactory regen.
    """

    __tablename__ = "contract_milestones"
    __table_args__ = (
        CheckConstraint(
            f"status IN {VALID_MILESTONE_STATUSES}",
            name="ck_contract_milestones_status",
        ),
        CheckConstraint(
            f"billing_trigger IN {VALID_BILLING_TRIGGERS}",
            name="ck_contract_milestones_trigger",
        ),
        CheckConstraint(
            "amount_eur >= 0",
            name="ck_contract_milestones_amount_nonneg",
        ),
        CheckConstraint(
            "percent_of_total >= 0 AND percent_of_total <= 100",
            name="ck_contract_milestones_percent_range",
        ),
        UniqueConstraint(
            "contract_id",
            "milestone_index",
            name="uq_contract_milestones_idx",
        ),
        Index(
            "ix_contract_milestones_project",
            "project_id",
        ),
        Index(
            "ix_contract_milestones_contract",
            "contract_id",
        ),
        Index(
            "ix_contract_milestones_phase",
            "workflow_phase_index",
        ),
        Index(
            "ix_contract_milestones_status",
            "status",
        ),
        Index(
            "ix_contract_milestones_paid_at",
            "paid_at",
        ),
        Index(
            "ix_contract_milestones_scheduled_date",
            "scheduled_date",
        ),
    )

    contract_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contracts.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    milestone_index: Mapped[int] = mapped_column(Integer, nullable=False)
    milestone_name: Mapped[str] = mapped_column(String(100), nullable=False)
    workflow_phase_index: Mapped[int] = mapped_column(
        Integer, nullable=False,
    )
    billing_trigger: Mapped[str] = mapped_column(
        String(50), nullable=False, default="phase_complete",
    )
    amount_eur: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False,
    )
    vat_percent: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), nullable=False, default=Decimal("21.00"),
    )
    percent_of_total: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending",
    )
    billed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    # #28 · fecha prevista de cobro/factura por hito (calendario de pagos).
    scheduled_date: Mapped[date | None] = mapped_column(
        Date, nullable=True,
    )
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="SET NULL"),
        nullable=True,
    )
    paid_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    paid_marked_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )
    payment_reference: Mapped[str | None] = mapped_column(
        String(200), nullable=True,
    )
    payment_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    auto_billing_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
    )
    blocking_next_phase: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
    )
    metadata_jsonb: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict,
    )


class RetainerHealthSignal(FullMixin, Base):
    """Snapshot per scan ChurnPredictor heurístico explicable.

    7 signals + computed score 0-100 + risk_level + recommended_action.
    Persistido per scan (Celery beat weekly Monday 09:30) para
    histórico trend y audit trail decisiones intervención Marcos.
    """

    __tablename__ = "retainer_health_signals"
    __table_args__ = (
        CheckConstraint(
            f"risk_level IN {VALID_RISK_LEVELS}",
            name="ck_retainer_health_risk_level",
        ),
        CheckConstraint(
            "churn_risk_score >= 0 AND churn_risk_score <= 100",
            name="ck_retainer_health_score_range",
        ),
        CheckConstraint(
            "tasks_overdue_count >= 0",
            name="ck_retainer_health_tasks_nonneg",
        ),
        CheckConstraint(
            "invoices_overdue_count >= 0",
            name="ck_retainer_health_invoices_nonneg",
        ),
        Index(
            "ix_retainer_health_project_recent",
            "project_id", text("computed_at DESC"),
        ),
        Index(
            "ix_retainer_health_retainer_recent",
            "retainer_id", text("computed_at DESC"),
        ),
        Index(
            "ix_retainer_health_risk_level",
            "risk_level", text("computed_at DESC"),
        ),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    retainer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("retainer_contracts.id", ondelete="CASCADE"),
        nullable=False,
    )
    computed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False,
    )
    days_since_portal_login: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
    )
    days_since_chat_msg_client: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
    )
    tasks_overdue_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    invoices_overdue_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    avg_response_time_hours: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 2), nullable=True,
    )
    nps_last_score: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
    )
    renewal_in_days: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
    )
    churn_risk_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False,
    )
    risk_level: Mapped[str] = mapped_column(
        String(20), nullable=False,
    )
    primary_risk_factors: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list,
    )
    recommended_action: Mapped[str | None] = mapped_column(
        String(500), nullable=True,
    )


__all__ = [
    "ContractMilestone",
    "RetainerHealthSignal",
    "VALID_MILESTONE_STATUSES",
    "VALID_BILLING_TRIGGERS",
    "VALID_RISK_LEVELS",
]
