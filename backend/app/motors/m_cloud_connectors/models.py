"""ORM models · m_cloud_connectors (sub-atom 1.D.X.B v3.12).

4 tables nuevas project-scoped:
  - cloud_connectors · CloudConnector · link M16 ConnectorConfig + cloud-first metadata
  - cloud_resources · CloudResource · recursos detectados (users · VMs · storage)
  - cloud_gaps · CloudGap · diagnostic gap engine resultado
  - cloud_sync_jobs · CloudSyncJob · tracking sync jobs lifecycle

R23 sostener · project_id en TODAS las tablas · RLS project-scoped.
ADR-025 sostener · NO duplicar oauth_credentials (FK a M16 ConnectorConfig existing).
ADR-014 sostener · read-only OAuth siempre (sin write tokens cliente).
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, FullMixin


# ==================================================================
# Enums canónicos
# ==================================================================


class CloudConnectorProvider(str, enum.Enum):
    """Providers soportados · matched con M16 ConnectorProvider existing."""

    MICROSOFT_365 = "microsoft_365"
    AZURE = "azure"
    AWS = "aws"
    GOOGLE_WORKSPACE = "google_workspace"
    GITHUB = "github"
    MANUAL_IMPORT = "manual_import"  # CSV/Excel fallback via m24_idms


class CloudConnectorStatus(str, enum.Enum):
    """Status lifecycle conector."""

    PENDING_OAUTH = "pending_oauth"
    CONNECTED = "connected"
    SYNCING = "syncing"
    SYNC_ERROR = "sync_error"
    REVOKED = "revoked"
    EXPIRED = "expired"


class CloudGapSeverity(str, enum.Enum):
    """Severity gap · alineada con M19 risk severity."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class CloudGapType(str, enum.Enum):
    """Categorización gap (R30 explicación admin tutor)."""

    STRUCTURAL = "structural"  # Faltan piezas core (NO MFA · NO backup)
    REINFORCEMENT = "reinforcement"  # Medio/Alto requiere refuerzos no impl
    CONFIGURATION = "configuration"  # Implementado pero mal configurado
    DOCUMENTAL = "documental"  # Realidad OK pero falta política/procedimiento


class CloudRemediationApprovalStatus(str, enum.Enum):
    """Bloque 3+5 · Lifecycle approval workflow cloud remediation.

    State machine deterministic (Phase A Enhancement refined Path B):
      detected → proposed_to_cliente → approved | rejected
        approved → executing → executed | failed
        executed → verification_pending → verified [TERMINAL]
                                       └─ back to executing (admin re-corrects)

    VERIFICATION_PENDING + VERIFIED added Bloque 3+5 Enhancement:
    admin marks executed (manual cloud action externa done) → ENTERS
    verification_pending automatically → admin reports verify success → VERIFIED.

    Sostiene ADR-014 read-only orchestrator · NO auto-execute capability.
    """

    DETECTED = "detected"
    PROPOSED_TO_CLIENTE = "proposed_to_cliente"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTING = "executing"
    EXECUTED = "executed"
    VERIFICATION_PENDING = "verification_pending"
    VERIFIED = "verified"
    FAILED = "failed"


class CloudRemediationLogAction(str, enum.Enum):
    """Acciones registradas en cloud_remediation_approval_logs (ENAC audit trail).

    Phase A Enhancement refined · added VERIFICATION_PENDING + VERIFIED + ROLLBACK_REQUESTED.
    ROLLBACK_REQUESTED es marker action · admin manual cloud rollback done after.
    """

    PROPOSED_TO_CLIENTE = "proposed_to_cliente"
    CLIENTE_APPROVED = "cliente_approved"
    CLIENTE_REJECTED = "cliente_rejected"
    EXECUTING = "executing"
    EXECUTED = "executed"
    VERIFICATION_PENDING = "verification_pending"
    VERIFIED = "verified"
    FAILED = "failed"
    ROLLBACK_REQUESTED = "rollback_requested"


class CloudRemediationFailureCategory(str, enum.Enum):
    """Phase A Enhancement · clasificación failure ON admin-reported failure.

    Admin captura categoría al marcar mark_failed para:
    - Transient: retry posible (network · cloud API hiccup) · admin re-ejecuta manual
    - Permanent: NO retry (auth · permissions denied · scope mismatch)
    - Partial: parcialmente aplicado (algunos recursos sí · otros no) · admin investigates
    - Unknown: categorización pendiente · default fallback
    """

    TRANSIENT = "transient"
    PERMANENT = "permanent"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


class CloudRemediationActorType(str, enum.Enum):
    """Tipo actor en audit log (admin Marcos vs cliente vs system automated)."""

    ADMIN = "admin"
    CLIENTE = "cliente"
    SYSTEM = "system"


class CloudSyncJobStatus(str, enum.Enum):
    """Status lifecycle sync job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ==================================================================
# CloudConnector · unified layer sobre M16 ConnectorConfig
# ==================================================================


class CloudConnector(FullMixin, Base):
    """Conector cloud project-scoped · link M16 OAuth credentials existing.

    project_id + provider unique · 1 conector activo per provider per project.
    """

    __tablename__ = "cloud_connectors"
    __table_args__ = (
        UniqueConstraint(
            "project_id", "provider",
            name="uq_cloud_connectors_project_provider",
        ),
        Index("ix_cloud_connectors_project_status", "project_id", "status"),
    )

    # Override TimestampMixin.updated_at · migración usa NOT NULL DEFAULT now().
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
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default=CloudConnectorStatus.PENDING_OAUTH.value,
    )

    # FK opcional a M16 ConnectorConfig existing · NULL si MANUAL_IMPORT
    m16_connector_config_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("connector_configs.id", ondelete="SET NULL"),
        nullable=True,
    )

    scopes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    last_sync_resources_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, server_default=text("0"),
    )

    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    metadata_extra: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


# ==================================================================
# CloudResource · recursos detectados
# ==================================================================


class CloudResource(FullMixin, Base):
    """Recurso cloud detectado · tipo + atributos JSONB flexibles."""

    __tablename__ = "cloud_resources"
    __table_args__ = (
        UniqueConstraint(
            "connector_id", "resource_external_id", "resource_type",
            name="uq_cloud_resources_external_id",
        ),
        Index("ix_cloud_resources_connector_type", "connector_id", "resource_type"),
        Index("ix_cloud_resources_project", "project_id"),
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
    connector_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cloud_connectors.id", ondelete="CASCADE"),
        nullable=False,
    )
    resource_type: Mapped[str] = mapped_column(String(60), nullable=False)
    """user · group · vm · storage_bucket · iam_role · etc."""

    resource_external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    """ID provider-side (Graph ID · ARN · etc)."""

    resource_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attributes: Mapped[dict] = mapped_column(JSONB, nullable=False)
    """JSONB flexible attributes per resource_type."""

    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    """SHA-256 checksum attributes para detectar cambios MoM."""

    detected_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"),
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"),
    )


# ==================================================================
# CloudGap · diagnostic gap engine resultado
# ==================================================================


class CloudGap(FullMixin, Base):
    """Gap detectado por Diagnostic Gap Engine · ENS measure + suggested action."""

    __tablename__ = "cloud_gaps"
    __table_args__ = (
        Index("ix_cloud_gaps_project_severity", "project_id", "severity"),
        Index("ix_cloud_gaps_measure", "ens_measure_code"),
        Index("ix_cloud_gaps_resolved", "project_id", "resolved_at"),
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
    connector_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cloud_connectors.id", ondelete="SET NULL"),
        nullable=True,
    )
    gap_type: Mapped[str] = mapped_column(String(40), nullable=False)
    """structural · reinforcement · configuration · documental."""

    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    """critical · high · medium · low."""

    ens_measure_code: Mapped[str] = mapped_column(String(50), nullable=False)
    """ENS Anexo II code (op.acc.5 · mp.if.4 · etc)."""

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    explanation_es: Mapped[str | None] = mapped_column(Text, nullable=True)
    """LLM enriched · primer-principios cliente-friendly R29/R30."""

    suggested_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    """Deterministic suggested action · NO LLM."""

    estimated_effort_days: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
    )
    auto_fixable: Mapped[bool] = mapped_column(
        default=False, server_default=text("false"),
    )
    cliente_can_see: Mapped[bool] = mapped_column(
        default=True, server_default=text("true"),
    )

    # Resolución
    resolved_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    resolved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_link_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )

    # Diagnostic metadata
    detected_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"),
    )
    raw_evidence: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    """Raw data del CloudResource que justifica el gap (trazabilidad ENAC)."""

    # ==================================================================
    # Bloque 3+5 cloud remediation orchestrator · approval workflow
    # ==================================================================

    approval_status: Mapped[str] = mapped_column(
        String(30), nullable=False,
        default=CloudRemediationApprovalStatus.DETECTED.value,
        server_default=text("'detected'"),
    )
    """State machine: detected → proposed_to_cliente → approved | rejected
    → executing → executed | failed."""

    proposed_to_cliente_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    """Cuándo Marcos admin disparó propuesta hacia cliente portal."""

    cliente_approval_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    """Cuándo cliente aprobó o rechazó (set in both cases)."""

    cliente_approval_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )
    """ClientUser que aprobó/rechazó (ENAC trazabilidad cliente decision)."""

    # Phase A Enhancement Bloque 3+5 · VERIFICATION_PENDING + VERIFIED state
    verification_pending_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    """Cuándo gap entered VERIFICATION_PENDING state (post mark_executed)."""

    verified_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    """Cuándo admin reportó verify success · estado TERMINAL VERIFIED."""

    verified_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )
    """Admin User que reportó verify success."""


# ==================================================================
# CloudRemediationApprovalLog · audit trail inmutable per transition
# ==================================================================


class CloudRemediationApprovalLog(Base):
    """Audit trail inmutable per state transition · ADR-031 ENAC-ready.

    NUNCA update · solo INSERT. Per transition del approval_status del CloudGap
    se persiste 1 row con action + actor + timestamp + notes + metadata JSONB.

    RLS project-scoped vía project_id field directo (NO JOIN required).

    NO FullMixin · este model NO necesita updated_at/deleted_at (audit log
    inmutable). Solo created_at autogenerado.
    """

    __tablename__ = "cloud_remediation_approval_logs"
    __table_args__ = (
        Index(
            "ix_cloud_remediation_logs_gap_ts",
            "gap_id", "created_at",
        ),
        Index(
            "ix_cloud_remediation_logs_project_ts",
            "project_id", "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    gap_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cloud_gaps.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    """Una de CloudRemediationLogAction values."""

    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )
    """User que ejecutó la acción · NULL solo si actor_type=system."""

    actor_type: Mapped[str] = mapped_column(String(20), nullable=False)
    """Una de CloudRemediationActorType values."""

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    """Notas opcionales del actor (e.g. rationale rejection)."""

    metadata_jsonb: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    """Metadata extensible (e.g. error_details · execution_logs · etc).

    Phase A Enhancement enriquecido con cross-references:
    - cloud_gap_id (siempre via gap_id field directo)
    - compliance_checks_affected (list[uuid])
    - evidence_files (list[path · sha256])
    - adenda_id (uuid si material change)
    - pre_state_snapshot (dict cloud_gap state pre-transition)
    - post_state_snapshot (dict cloud_gap state post-transition)
    - technical_detail (str admin tone)
    - friendly_message (str cliente R29 tone)
    """

    # Phase A Enhancement · idempotency + categorization
    idempotency_key: Mapped[str | None] = mapped_column(
        String(128), nullable=True,
    )
    """Idempotency key (SHA-256 hash o caller-provided) · UNIQUE (gap_id+action+key).
    NULL backward-compat existing logs · NOT NULL para NEW logs prevent duplicate."""

    failure_category: Mapped[str | None] = mapped_column(
        String(20), nullable=True,
    )
    """CloudRemediationFailureCategory · solo si action=FAILED."""

    correlation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )
    """UUID per lifecycle correlation cross-events bus (M22 + SSE)."""

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        # OPS-047: el audit trail se ordena por created_at; server_default now()
        # da timestamp idéntico a todas las filas insertadas en la MISMA
        # transacción (ordenación inestable → flaky bajo carga). default Python
        # por-objeto da microsegundos distintos por cada llamada awaited del
        # orchestrator (propose→approve→execute→executed). Ejecutable 8 Pasada 16.
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )


# ==================================================================
# CloudSyncJob · tracking sync jobs
# ==================================================================


class CloudSyncJob(FullMixin, Base):
    """Tracking sync job lifecycle · idempotente · retry · status."""

    __tablename__ = "cloud_sync_jobs"
    __table_args__ = (
        Index("ix_cloud_sync_jobs_connector", "connector_id", "started_at"),
        Index("ix_cloud_sync_jobs_status", "status"),
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
    connector_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cloud_connectors.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=CloudSyncJobStatus.PENDING.value,
    )
    started_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    resources_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, server_default=text("0"),
    )
    errors_jsonb: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    """{errors: [...], warnings: [...]}."""

    triggered_by: Mapped[str] = mapped_column(
        String(40), default="manual", nullable=False,
    )
    """manual · scheduled_daily · cliente_oauth_callback · admin_force."""


# ==================================================================
# CloudDigestSnapshot · digest mensual persistido (1.D.X.VERIFY 2a)
# ==================================================================


class CloudDigestSnapshot(FullMixin, Base):
    """Snapshot digest mensual · histórico para trend MoM (commit 2b cliente).

    Persiste cada generación (Celery beat OR admin manual trigger) · permite
    diff con snapshot anterior + endpoint cliente "Tu último resumen mensual".
    """

    __tablename__ = "cloud_digest_snapshots"
    __table_args__ = (
        Index(
            "ix_cloud_digest_snapshots_project_generated",
            "project_id", "generated_at",
        ),
        Index(
            "ix_cloud_digest_snapshots_triggered_by", "triggered_by",
        ),
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
    generated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"),
    )
    triggered_by: Mapped[str] = mapped_column(
        String(40), nullable=False, default="celery_monthly",
    )
    """celery_monthly · admin_manual (audit context)."""

    triggered_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )
    """Si triggered_by=admin_manual · user id de quien pulsó botón."""

    compliance_score: Mapped[int] = mapped_column(
        Integer, nullable=False, default=100, server_default=text("100"),
    )
    """0-100 · formula deterministic from gaps abiertos."""

    open_gaps_total: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0"),
    )
    open_gaps_by_severity: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"),
    )
    """{critical: N, high: N, medium: N, low: N}."""

    snapshot_jsonb: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"),
    )
    """Snapshot completo · UI admin y cliente filtran fields."""
