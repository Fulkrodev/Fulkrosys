"""Pydantic schemas · m_cloud_connectors (sub-atom 1.D.X.B v3.12).

DTOs request/response API admin + cliente. Sin lógica de negocio.

R23 sostener · payloads project-scoped. ADR-014 read-only OAuth.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from backend.app.motors.m_cloud_connectors.models import (
    CloudConnectorProvider,
)


# ==================================================================
# CloudConnector schemas
# ==================================================================


class CloudConnectorLinkBody(BaseModel):
    """Link existing M16 ConnectorConfig to project as CloudConnector.

    Si ``m16_connector_config_id`` provisto → adopta credenciales existing.
    Si NULL → CloudConnector queda en PENDING_OAUTH (cliente debe completar flow).
    """

    provider: CloudConnectorProvider
    m16_connector_config_id: Optional[uuid.UUID] = None
    scopes: Optional[str] = Field(default=None, max_length=500)


class CloudConnectorRead(BaseModel):
    """Read schema CloudConnector · response API."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    provider: str
    status: str
    m16_connector_config_id: Optional[uuid.UUID]
    scopes: Optional[str]
    last_sync_at: Optional[datetime]
    last_sync_resources_count: int
    revoked_at: Optional[datetime]
    metadata_extra: Optional[dict[str, Any]]
    created_at: datetime
    updated_at: datetime


class CloudConnectorListResponse(BaseModel):
    items: list[CloudConnectorRead]
    total: int


# ==================================================================
# CloudResource schemas
# ==================================================================


class CloudResourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    connector_id: uuid.UUID
    resource_type: str
    resource_external_id: str
    resource_name: Optional[str]
    attributes: dict[str, Any]
    checksum: Optional[str]
    detected_at: datetime
    last_seen_at: datetime


class CloudResourceListResponse(BaseModel):
    items: list[CloudResourceRead]
    total: int


# ==================================================================
# CloudGap schemas
# ==================================================================


class CloudGapRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    connector_id: Optional[uuid.UUID]
    gap_type: str
    severity: str
    ens_measure_code: str
    title: str
    explanation_es: Optional[str]
    suggested_action: Optional[str]
    estimated_effort_days: Optional[int]
    auto_fixable: bool
    cliente_can_see: bool
    resolved_at: Optional[datetime]
    resolution_note: Optional[str]
    evidence_link_id: Optional[uuid.UUID]
    detected_at: datetime


class CloudGapResolveBody(BaseModel):
    resolution_note: Optional[str] = Field(default=None, max_length=2000)
    evidence_link_id: Optional[uuid.UUID] = None


class CloudGapListResponse(BaseModel):
    items: list[CloudGapRead]
    total: int


# ==================================================================
# CloudSyncJob schemas
# ==================================================================


class CloudSyncJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    connector_id: uuid.UUID
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    resources_count: int
    errors_jsonb: Optional[dict[str, Any]]
    triggered_by: str


class CloudSyncJobListResponse(BaseModel):
    items: list[CloudSyncJobRead]
    total: int


class CloudSyncTriggerResponse(BaseModel):
    """Response cuando admin/cliente dispara sync."""

    job_id: uuid.UUID
    status: str
    started_at: datetime
    message: str


# ==================================================================
# Cliente portal schemas (super-friendly R29)
# ==================================================================


class CloudConnectorPublicSummary(BaseModel):
    """Resumen cliente-friendly · NO expone scopes ni IDs internos M16.

    Sesión 3B-2B.8 Phase 1C: expone ``id`` (connector_id propio) para que el
    cliente pueda targetear /request-disconnect chat-mediated · NO leak M16
    internal connector_config_id (que es internal admin scope).
    """

    id: uuid.UUID
    provider: str
    status: str
    last_sync_at: Optional[datetime]
    resources_count: int
    friendly_message: str
    """Mensaje generado para cliente (R29 sin presión)."""


class CloudConnectorClientListResponse(BaseModel):
    items: list[CloudConnectorPublicSummary]
    project_id: uuid.UUID


class CloudConnectorClientInitFlowResponse(BaseModel):
    """Init OAuth flow desde cliente · reuse M16 portal_api existing."""

    authorize_url: str
    state: str
    provider: str
    expires_in: int


# ==================================================================
# ClientDigestView · cliente portal schema FILTERED (sub-fase 1.D.X.VERIFY 2b)
# ==================================================================
# CRITICAL: schema SEPARADO de DigestSnapshotResponse admin · NO leak admin
# sensitive fields (triggered_by_user_id, snapshot_jsonb raw, triggered_by
# internal codes, etc). R29 friendly · sin jerga · sin presión.


class ClientDigestView(BaseModel):
    """Cliente view del digest · filtered safe fields ONLY.

    NUNCA reusar AdminDigestSnapshot · este schema garantiza que cliente NO
    ve campos sensitive (admin user IDs · raw error details · internal codes).
    """

    has_snapshot: bool
    """False si NUNCA generado · UI muestra empty state friendly."""

    compliance_score: int = 100
    """0-100 · score actual."""

    trend_label: str = "primer_resumen"
    """'mejora' | 'igual' | 'baja' | 'primer_resumen'."""

    trend_emoji: str = "✨"
    """'↑' (mejora) | '≈' (igual) | '↓' (baja suave) | '✨' (primer)."""

    trend_color_hint: str = "neutral"
    """'verde' | 'ambar' | 'naranja_suave' | 'neutral'.
    UI mapea a Tailwind colors · NUNCA rojo (R29 sin presión)."""

    last_review_at: Optional[datetime] = None
    changes_reviewed_count: int = 0
    """Total gaps abiertos del último snapshot · NO desglose por severity
    (admin sensitive · cliente solo ve count general)."""

    consultant_name: str = "Marcos"
    summary_friendly: str = ""
    """Texto breve generado deterministic · NO LLM · sin jerga ENS."""


class ClientDigestResponse(BaseModel):
    digest: ClientDigestView


# ==================================================================
# Catalog providers schemas (para UI)
# ==================================================================


class ProviderCatalogItem(BaseModel):
    provider: str
    display_name: str
    icon_emoji: str
    requires_oauth: bool
    cliente_friendly_blurb: str


class ProviderCatalogResponse(BaseModel):
    items: list[ProviderCatalogItem]
