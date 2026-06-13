"""ORM models · agente on-prem m_remediation (ADR-055 Fase 3).

  - remediation_agents          · agente enrolado en la infra del cliente
  - remediation_agent_commands  · comandos firmados que el agente hace pull

RLS directa project_id. La resolución del agente por token (cross-RLS) la hace
la función SECURITY DEFINER `fn_resolve_remediation_agent` (migración).
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, FullMixin


class RemediationAgentStatus(str, enum.Enum):
    PENDING = "pending"      # token emitido · aún no canjeado
    ACTIVE = "active"        # enrolado · operativo
    REVOKED = "revoked"      # kill-switch · no recibe comandos


class RemediationAgentCommandStatus(str, enum.Enum):
    PENDING = "pending"      # encolado · sin entregar
    DELIVERED = "delivered"  # el agente lo hizo pull
    REPORTED = "reported"    # el agente reportó resultado


class RemediationAgent(FullMixin, Base):
    """Agente desplegado en un host del cliente · auth mutua Ed25519."""

    __tablename__ = "remediation_agents"
    __table_args__ = (
        Index("ix_remediation_agents_project_status", "project_id", "status"),
        Index("ix_remediation_agents_token", "agent_token_hash"),
        Index("ix_remediation_agents_enroll", "enrollment_token_hash"),
    )

    updated_at: Mapped[datetime] = mapped_column(  # type: ignore[assignment]
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False,
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False,
    )
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )
    hostname: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=RemediationAgentStatus.PENDING.value,
        server_default=text("'pending'"),
    )

    # Enrollment de un solo uso (hash del token · se limpia al canjear).
    enrollment_token_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True,
    )
    enrollment_expires_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )

    # Identidad del agente (clave pública Ed25519 hex · fijada al canjear).
    agent_pubkey_hex: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Token bearer del canal (hash · el agente lo usa para poll/report).
    agent_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    agent_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    capabilities: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    """Lista de playbook_ids que el agente declara soportar."""

    enrolled_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )


class RemediationAgentCommand(FullMixin, Base):
    """Comando firmado que el agente hace pull · resultado reportado y firmado."""

    __tablename__ = "remediation_agent_commands"
    __table_args__ = (
        Index("ix_remediation_agent_cmds_agent", "agent_id", "status"),
        Index("ix_remediation_agent_cmds_project", "project_id"),
    )

    updated_at: Mapped[datetime] = mapped_column(  # type: ignore[assignment]
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False,
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False,
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("remediation_agents.id", ondelete="CASCADE"), nullable=False,
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("remediation_jobs.id", ondelete="SET NULL"), nullable=True,
    )
    playbook_id: Mapped[str] = mapped_column(String(80), nullable=False)
    params: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    issued_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"),
    )
    server_signature: Mapped[str] = mapped_column(Text, nullable=False)
    """Firma Ed25519 hex del servidor sobre el payload canónico del comando."""

    status: Mapped[str] = mapped_column(
        String(20), nullable=False,
        default=RemediationAgentCommandStatus.PENDING.value,
        server_default=text("'pending'"),
    )
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    report_signature: Mapped[str | None] = mapped_column(Text, nullable=True)
    """Firma Ed25519 hex del agente sobre el payload del resultado."""
    delivered_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    reported_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
