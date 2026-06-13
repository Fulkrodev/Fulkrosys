"""ORM models · m_remediation (ADR-055).

Fase 1 (cloud):
  - remediation_jobs       · RemediationJob · unidad de trabajo de remediación
  - remediation_snapshots  · RemediationSnapshot · estado previo para rollback

Tablas del agente on-prem (remediation_agents · remediation_agent_commands) se
añaden en Fase 3 (migración separada · aditiva).

R23 · project_id en todas las tablas · RLS directa project_id.
R6 · el audit de cada transición va a audit_log (writer central), NO aquí.
ADR-014 carve-out · escritura opt-in · default OFF (kill-switch 3 capas).
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, FullMixin


class RemediationJobStatus(str, enum.Enum):
    """Estados del ciclo de vida de un job (ADR-055)."""

    QUEUED = "queued"
    """Creado · pendiente de clasificación/arranque."""
    AWAITING_AUTHORIZATION = "awaiting_authorization"
    """Tier GUARDED · esperando autorización previa (cliente/admin)."""
    BLOCKED = "blocked"
    """Tier BLOCKED · nunca auto · solo plan (humano externo)."""
    SKIPPED_COMPLIANT = "skipped_compliant"
    """Preflight detectó que el recurso ya cumple → no-op idempotente."""
    PREFLIGHT = "preflight"
    SNAPSHOTTING = "snapshotting"
    APPLYING = "applying"
    VERIFYING = "verifying"
    SUCCEEDED = "succeeded"
    """Aplicado y verificado correctamente."""
    FAILED = "failed"
    """Falló (apply o verify) · sin rollback (no había snapshot aplicable)."""
    ROLLED_BACK = "rolled_back"
    """Verify falló tras apply → restaurado desde snapshot."""


# Estados terminales (no admiten más transiciones).
TERMINAL_JOB_STATES: frozenset[str] = frozenset(
    {
        RemediationJobStatus.BLOCKED.value,
        RemediationJobStatus.SKIPPED_COMPLIANT.value,
        RemediationJobStatus.SUCCEEDED.value,
        RemediationJobStatus.FAILED.value,
        RemediationJobStatus.ROLLED_BACK.value,
    }
)


class RemediationSourceKind(str, enum.Enum):
    CLOUD_GAP = "cloud_gap"
    HOST_FINDING = "host_finding"


class RemediationJob(FullMixin, Base):
    """Unidad de trabajo de remediación · origen cloud gap o host finding."""

    __tablename__ = "remediation_jobs"
    __table_args__ = (
        Index("ix_remediation_jobs_project_status", "project_id", "status"),
        Index("ix_remediation_jobs_gap", "source_gap_id"),
        Index("ix_remediation_jobs_action", "action_type"),
    )

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
        UUID(as_uuid=True), nullable=True,
    )

    source_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    """cloud_gap · host_finding."""
    source_gap_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cloud_gaps.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_finding_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )
    connector_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cloud_connectors.id", ondelete="SET NULL"),
        nullable=True,
    )
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )
    """FK lógica a remediation_agents (tabla creada en Fase 3)."""

    action_type: Mapped[str] = mapped_column(String(80), nullable=False)
    """Clave del catálogo (catalog.ACTION_CATALOG)."""
    tier: Mapped[str] = mapped_column(String(20), nullable=False)
    """Snapshot determinista del tier al crear (audit · no se recalcula)."""
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=RemediationJobStatus.QUEUED.value,
        server_default=text("'queued'"),
    )

    target_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    """ID externo del recurso (ARN · Graph ID · hostname)."""
    params: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    dry_run: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false"),
    )

    # Autorización previa (tier GUARDED)
    authorized_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )
    authorized_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )

    # Resultado / trazabilidad
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )


class RemediationSnapshot(FullMixin, Base):
    """Estado previo capturado antes de aplicar · permite rollback determinista."""

    __tablename__ = "remediation_snapshots"
    __table_args__ = (
        Index("ix_remediation_snapshots_job", "job_id"),
        Index("ix_remediation_snapshots_project", "project_id"),
    )

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
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("remediation_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    action_type: Mapped[str] = mapped_column(String(80), nullable=False)
    target_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    state_before: Mapped[dict] = mapped_column(JSONB, nullable=False)
    """Estado del recurso ANTES de aplicar (para revertir)."""
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )
