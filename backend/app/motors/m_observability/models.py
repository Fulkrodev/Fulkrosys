"""ORM models · m_observability (sub-atoms 1.E.1.B.2 + 1.E.1.B.3.E v3.12).

NEW tables:
  - ai_act_transparency_events (B.2) · AI Act art.50 compliance
  - golden_eval_runs (B.3.E) · admin trigger + historical regression eval

ADR-025 sostenido firmísimo · scope diferente per table:
  - llm_interaction_log existing tracks calls técnicos (tokens · cost · latency)
  - ai_act_transparency_events tracks decisiones IA externalizadas
  - golden_eval_runs tracks regression eval RUNS metadata (NOT individual
    LLM calls · NOT decisions) · scope diferente · NO duplica
"""
from __future__ import annotations

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Date,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, FullMixin


# ==================================================================
# Enums canónicos AI Act event types
# ==================================================================


class AIActEventType(str, enum.Enum):
    """Event types tracked per AI Act art.50 transparency obligations."""

    DELIVERABLE_GENERATED = "deliverable_generated"
    PROPOSAL_DRAFTED = "proposal_drafted"
    CONTRACT_CLAUSE_GENERATED = "contract_clause_generated"
    DIAGNOSTIC_PERFORMED = "diagnostic_performed"
    GAP_ANALYSIS = "gap_analysis"
    RISK_ASSESSMENT = "risk_assessment"
    POLICY_DRAFTED = "policy_drafted"
    COPILOT_INTERACTION = "copilot_interaction"


class AIActLLMProvider(str, enum.Enum):
    """LLM providers tracked · matched con FULKRO llm_router existing."""

    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure_openai"
    BEDROCK = "bedrock"
    GOOGLE = "google"
    OTHER = "other"


# ==================================================================
# AIActTransparencyEvent · NEW table 1.E.1.B.2
# ==================================================================


class AIActTransparencyEvent(FullMixin, Base):
    """AI Act art.50 transparency event · cliente-readable audit trail.

    Cada decisión IA externalizada (deliverable generado · proposal redactada
    · cláusula contractual · diagnóstico) se registra con:
      - purpose statement cliente-readable (R29 friendly)
      - artifact link (deliverable/proposal/contract) opcional
      - retention_until computed (created_at + 6 years per AI Act guidance)

    Project-scoped (RLS) · cliente NO ve cross-project · admin full access
    via fulkro_migrate role.
    """

    __tablename__ = "ai_act_transparency_events"
    __table_args__ = (
        Index(
            "ix_ai_act_transparency_project_created",
            "project_id", "created_at",
        ),
        Index(
            "ix_ai_act_transparency_client_created",
            "client_id", "created_at",
        ),
        Index(
            "ix_ai_act_transparency_event_type", "event_type",
        ),
    )

    # LECCIÓN-OPS-046 sostener · FullMixin nullable=True vs migration NOT NULL
    updated_at: Mapped[datetime] = mapped_column(  # type: ignore[assignment]
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="SET NULL"),
        nullable=True,
    )

    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    """Canonical event type · see AIActEventType enum."""

    llm_provider: Mapped[str] = mapped_column(String(32), nullable=False)
    """LLM provider · see AIActLLMProvider enum."""

    llm_model: Mapped[str] = mapped_column(String(128), nullable=False)
    """LLM model identifier (claude-opus-4-7 · etc)."""

    agent_name: Mapped[str] = mapped_column(String(64), nullable=False)
    """FULKRO agent name (agent_04_redactor · agent_11_auditor_virtual · etc)."""

    artifact_type: Mapped[str | None] = mapped_column(
        String(64), nullable=True,
    )
    """Optional artifact type (E-XXX · P-001 · etc) when applicable."""

    artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )
    """Optional artifact UUID link (deliverable · proposal · contract)."""

    purpose: Mapped[str] = mapped_column(String(256), nullable=False)
    """Cliente-readable purpose statement (AI Act art.50 requirement)."""

    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, nullable=True,
    )
    """Extensible metadata JSONB · NO leak sensitive data."""

    retention_until: Mapped[date] = mapped_column(
        Date, nullable=False,
    )
    """Computed retention boundary: created_at::date + 6 years."""


# ==================================================================
# Enums canónicos GoldenEvalRun
# ==================================================================


class GoldenEvalRunStatus(str, enum.Enum):
    """Status lifecycle eval run · admin trigger → completion."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# ==================================================================
# GoldenEvalRun · NEW table 1.E.1.B.3.E
# ==================================================================


class GoldenEvalRun(FullMixin, Base):
    """Admin trigger + historical regression eval runs metadata.

    Platform-global · admin-only · NO RLS (mismo cement m_compliance_monitor).
    Triggered manualmente desde `/admin/llm-observability/golden-eval/` UI
    OR vía Celery beat scheduled (post B.3.E future).
    """

    __tablename__ = "golden_eval_runs"
    __table_args__ = (
        Index(
            "ix_golden_eval_runs_agent_triggered",
            "agent_name", "triggered_at",
        ),
        Index(
            "ix_golden_eval_runs_status", "status",
        ),
    )

    # LECCIÓN-OPS-046 sostener · FullMixin nullable=True vs migration NOT NULL
    updated_at: Mapped[datetime] = mapped_column(  # type: ignore[assignment]
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )

    agent_name: Mapped[str] = mapped_column(String(64), nullable=False)
    """Golden dataset agent name (deliverable_text_auditor · future agents)."""

    dataset_version: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default=text("'v1'"),
    )
    """Dataset version slug (e.g. v1 · v2 · etc)."""

    triggered_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )
    """Admin user_id que disparó el run (audit trail)."""

    triggered_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'queued'"),
    )
    """Status lifecycle · see GoldenEvalRunStatus enum."""

    regression_score: Mapped[float | None] = mapped_column(
        Float, nullable=True,
    )
    """pass_rate computed post completion · None mientras running."""

    severity: Mapped[str | None] = mapped_column(
        String(20), nullable=True,
    )
    """ok | warn | alert · None mientras running."""

    entries_in_dataset: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0"),
    )
    entries_evaluated: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0"),
    )
    entries_passed: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0"),
    )
    entries_failed: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0"),
    )

    failed_entry_ids: Mapped[list | None] = mapped_column(
        JSONB, nullable=True,
    )
    """JSON array de entry_ids fallidos · drill-down UI."""

    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )
    """Error trace si status=failed."""

    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, nullable=True,
    )
    """Extensible · cli args · git sha · env · etc."""
