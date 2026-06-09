"""Admin API · m_cloud_connectors (sub-atom 1.D.X.B v3.12).

6 endpoints REST project-scoped (admin-only · ``require_owner``):

  GET    /api/v1/admin/projects/{pid}/cloud-connectors                       list
  POST   /api/v1/admin/projects/{pid}/cloud-connectors                       link M16 OAuth → CloudConnector
  POST   /api/v1/admin/projects/{pid}/cloud-connectors/{cid}/sync            trigger sync
  GET    /api/v1/admin/projects/{pid}/cloud-connectors/{cid}/resources       browse
  GET    /api/v1/admin/projects/{pid}/cloud-connectors/{cid}/sync-jobs       history
  DELETE /api/v1/admin/projects/{pid}/cloud-connectors/{cid}                 revoke

+ providers catalog endpoint cliente UI:
  GET    /api/v1/cloud-connectors/providers/catalog                           catalog

RLS enforced via ``_set_project_context`` (pattern m_live_records + departments).

R23 sostener · TODO project-scoped (NO global). R31 sostener · backend frontend
accionable (frontend cliente + admin consumirá estos endpoints en sub-fases I+J).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db, set_tenant_context
from backend.app.motors.m_cloud_connectors.diagnostic_gap_engine import (
    DiagnosisReport,
    DiagnosticGapEngine,
)
from backend.app.motors.m_cloud_connectors.gap_rules import (
    list_supported_measures,
)
from backend.app.motors.m_cloud_connectors.schemas import (
    CloudConnectorLinkBody,
    CloudConnectorListResponse,
    CloudConnectorRead,
    CloudGapListResponse,
    CloudGapRead,
    CloudGapResolveBody,
    CloudResourceListResponse,
    CloudResourceRead,
    CloudSyncJobListResponse,
    CloudSyncJobRead,
    CloudSyncTriggerResponse,
    ProviderCatalogItem,
    ProviderCatalogResponse,
)
from backend.app.motors.m_cloud_connectors.service import (
    CloudConnectorNotFoundError,
    CloudConnectorRevokedError,
    CloudConnectorService,
    CloudGapNotFoundError,
    list_provider_catalog,
)


# Project-scoped admin router (auth: require_owner)
router = APIRouter(
    prefix="/admin/projects/{project_id}/cloud-connectors",
    tags=["Cloud Connectors (1.D.X.B) - Admin"],
    dependencies=[Depends(require_owner)],
)

# Public (auth: require_owner) catalog providers
catalog_router = APIRouter(
    prefix="/cloud-connectors",
    tags=["Cloud Connectors (1.D.X.B) - Catalog"],
    dependencies=[Depends(require_owner)],
)


async def _set_project_context(
    db: AsyncSession, project_id: uuid.UUID,
) -> None:
    """Set app.current_project_id + verify project exists (404 if not)."""
    cid = (await db.execute(
        text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)},
    )).scalar()
    if not cid:
        raise HTTPException(status_code=404, detail="Project not found")
    await set_tenant_context(db, project_id=project_id)


# ==================================================================
# Catalog providers (cliente UI consume)
# ==================================================================


@catalog_router.get(
    "/providers/catalog",
    response_model=ProviderCatalogResponse,
)
async def get_providers_catalog() -> ProviderCatalogResponse:
    """Catalog providers disponibles · cliente UI consume para grid cards."""
    return ProviderCatalogResponse(
        items=[ProviderCatalogItem(**p) for p in list_provider_catalog()],
    )


# ==================================================================
# CloudConnector CRUD
# ==================================================================


@router.get("", response_model=CloudConnectorListResponse)
async def list_cloud_connectors(
    project_id: uuid.UUID,
    include_revoked: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
) -> CloudConnectorListResponse:
    await _set_project_context(db, project_id)
    svc = CloudConnectorService(db)
    items = await svc.list_connectors(
        project_id=project_id, include_revoked=include_revoked,
    )
    return CloudConnectorListResponse(
        items=[CloudConnectorRead.model_validate(i) for i in items],
        total=len(items),
    )


@router.post("", response_model=CloudConnectorRead, status_code=201)
async def link_cloud_connector(
    project_id: uuid.UUID,
    body: CloudConnectorLinkBody,
    db: AsyncSession = Depends(get_db),
) -> CloudConnectorRead:
    """Link existing M16 OAuth credentials → CloudConnector project-scoped.

    Idempotente · re-link mismo provider OK (UPSERT on UNIQUE).
    """
    await _set_project_context(db, project_id)
    svc = CloudConnectorService(db)
    connector = await svc.link_or_create_connector(
        project_id=project_id,
        provider=body.provider,
        m16_connector_config_id=body.m16_connector_config_id,
        scopes=body.scopes,
    )
    await db.commit()
    return CloudConnectorRead.model_validate(connector)


@router.delete("/{connector_id}", response_model=CloudConnectorRead)
async def revoke_cloud_connector(
    project_id: uuid.UUID,
    connector_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> CloudConnectorRead:
    await _set_project_context(db, project_id)
    svc = CloudConnectorService(db)
    try:
        connector = await svc.revoke_connector(
            project_id=project_id, connector_id=connector_id,
        )
    except CloudConnectorNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await db.commit()
    return CloudConnectorRead.model_validate(connector)


# ==================================================================
# Sync orchestration
# ==================================================================


@router.post(
    "/{connector_id}/sync", response_model=CloudSyncTriggerResponse, status_code=202,
)
async def trigger_cloud_sync(
    project_id: uuid.UUID,
    connector_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> CloudSyncTriggerResponse:
    """Dispara sync inline (sub-fase B · no Celery aún · L retainer)."""
    await _set_project_context(db, project_id)
    svc = CloudConnectorService(db)
    try:
        # #18 · trigger_sync resuelve credenciales reales desde la M16
        # ConnectorConfig enlazada (m16_connector_config_id) → discovery real.
        # Sin enlace + no MANUAL_IMPORT → guard mock_mode (requiere env).
        job = await svc.trigger_sync(
            project_id=project_id,
            connector_id=connector_id,
            triggered_by="admin_manual",
        )
    except CloudConnectorNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CloudConnectorRevokedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await db.commit()
    return CloudSyncTriggerResponse(
        job_id=job.id,
        status=job.status,
        started_at=job.started_at,
        message="Sync dispatched (discovery real si hay OAuth M16 enlazado · mock_mode si no).",
    )


@router.get(
    "/{connector_id}/resources", response_model=CloudResourceListResponse,
)
async def list_cloud_resources(
    project_id: uuid.UUID,
    connector_id: uuid.UUID,
    resource_type: Optional[str] = Query(default=None, max_length=60),
    limit: int = Query(default=200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
) -> CloudResourceListResponse:
    await _set_project_context(db, project_id)
    svc = CloudConnectorService(db)
    try:
        items, total = await svc.list_resources(
            project_id=project_id,
            connector_id=connector_id,
            resource_type=resource_type,
            limit=limit,
        )
    except CloudConnectorNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return CloudResourceListResponse(
        items=[CloudResourceRead.model_validate(i) for i in items],
        total=total,
    )


@router.get(
    "/{connector_id}/sync-jobs", response_model=CloudSyncJobListResponse,
)
async def list_cloud_sync_jobs(
    project_id: uuid.UUID,
    connector_id: uuid.UUID,
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> CloudSyncJobListResponse:
    await _set_project_context(db, project_id)
    svc = CloudConnectorService(db)
    try:
        items = await svc.list_sync_jobs(
            project_id=project_id,
            connector_id=connector_id,
            limit=limit,
        )
    except CloudConnectorNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return CloudSyncJobListResponse(
        items=[CloudSyncJobRead.model_validate(i) for i in items],
        total=len(items),
    )


# ==================================================================
# Cloud Gaps · listing + resolve (admin)
# ==================================================================


gaps_router = APIRouter(
    prefix="/admin/projects/{project_id}/cloud-gaps",
    tags=["Cloud Connectors (1.D.X.B) - Gaps"],
    dependencies=[Depends(require_owner)],
)


@gaps_router.get("", response_model=CloudGapListResponse)
async def list_cloud_gaps(
    project_id: uuid.UUID,
    severity: list[str] | None = Query(default=None),
    include_resolved: bool = Query(default=False),
    limit: int = Query(default=200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
) -> CloudGapListResponse:
    await _set_project_context(db, project_id)
    svc = CloudConnectorService(db)
    items, total = await svc.list_gaps(
        project_id=project_id,
        severities=severity,
        include_resolved=include_resolved,
        limit=limit,
    )
    return CloudGapListResponse(
        items=[CloudGapRead.model_validate(g) for g in items],
        total=total,
    )


@gaps_router.post(
    "/{gap_id}/resolve", response_model=CloudGapRead,
)
async def resolve_cloud_gap(
    project_id: uuid.UUID,
    gap_id: uuid.UUID,
    body: CloudGapResolveBody,
    db: AsyncSession = Depends(get_db),
) -> CloudGapRead:
    await _set_project_context(db, project_id)
    svc = CloudConnectorService(db)
    try:
        gap = await svc.resolve_gap(
            project_id=project_id,
            gap_id=gap_id,
            resolution_note=body.resolution_note,
            evidence_link_id=body.evidence_link_id,
        )
    except CloudGapNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await db.commit()
    return CloudGapRead.model_validate(gap)


# ==================================================================
# Diagnostic Gap Engine · trigger + catalog (sub-fase 1.D.X.H)
# ==================================================================


diagnosis_router = APIRouter(
    prefix="/admin/projects/{project_id}/cloud-diagnosis",
    tags=["Cloud Connectors (1.D.X.H) - Diagnosis"],
    dependencies=[Depends(require_owner)],
)


class DiagnosisRunBody(BaseModel):
    """Body opcional · override categoría (raro · normalmente la engine la
    resuelve desde projects.categoria_objetivo)."""

    category_override: Optional[str] = None


class DiagnosisReportResponse(BaseModel):
    project_id: uuid.UUID
    category: Optional[str]
    rules_evaluated: int
    findings_emitted: int
    gaps_created: int
    gaps_updated: int
    gaps_resolved: int
    gap_codes: list[str]
    no_cloud_data: bool


class SupportedMeasuresResponse(BaseModel):
    measures: list[str]


@diagnosis_router.post(
    "/run", response_model=DiagnosisReportResponse, status_code=200,
)
async def run_diagnosis(
    project_id: uuid.UUID,
    body: DiagnosisRunBody | None = None,
    db: AsyncSession = Depends(get_db),
) -> DiagnosisReportResponse:
    """Dispara Diagnostic Gap Engine deterministic R1.

    UPSERT idempotente · re-eval también auto-resuelve gaps que dejan de emitir.
    Pure deterministic · LLM SOLO se invoca en endpoint dedicado enrichment.
    """
    await _set_project_context(db, project_id)
    engine = DiagnosticGapEngine(db)
    category = body.category_override if body else None
    report = await engine.run_diagnosis(
        project_id=project_id, category=category,
    )
    await db.commit()
    return DiagnosisReportResponse(
        project_id=report.project_id,
        category=report.category,
        rules_evaluated=report.rules_evaluated,
        findings_emitted=report.findings_emitted,
        gaps_created=report.gaps_created,
        gaps_updated=report.gaps_updated,
        gaps_resolved=report.gaps_resolved,
        gap_codes=report.gap_codes,
        no_cloud_data=report.no_cloud_data,
    )


# Catalog ENS measures soportadas (público admin · ayuda debug + UI roadmap)
@catalog_router.get(
    "/supported-measures", response_model=SupportedMeasuresResponse,
)
async def get_supported_measures() -> SupportedMeasuresResponse:
    """Lista ENS measure codes que el engine sabe detectar desde cloud."""
    return SupportedMeasuresResponse(measures=list_supported_measures())


# ==================================================================
# Integrations · M03 DdA + M04 Plan + M07 Evidence (sub-fase 1.D.X.K)
# ==================================================================


from backend.app.motors.m_cloud_connectors.integrations import (
    consolidate_discovery_with_cloud,
    enrich_asset_inventory_with_cloud,
    get_categorization_cloud_hint,
    get_conformity_cloud_score,
    get_measures_cloud_status_bulk,
    get_risk_cloud_indicators,
    iter_evidences_for_attach,
    iter_gaps_for_plan_actions,
)


integrations_router = APIRouter(
    prefix="/admin/projects/{project_id}/cloud-integrations",
    tags=["Cloud Connectors (1.D.X.K) - Integrations"],
    dependencies=[Depends(require_owner)],
)


class MeasureStatusResponse(BaseModel):
    project_id: uuid.UUID
    measures: dict[str, dict[str, Any]]


class PlanSuggestionsResponse(BaseModel):
    project_id: uuid.UUID
    severity_min: str
    items: list[dict[str, Any]]


class EvidenceSuggestionsResponse(BaseModel):
    project_id: uuid.UUID
    measure_code: str
    items: list[dict[str, Any]]


@integrations_router.get(
    "/measure-status", response_model=MeasureStatusResponse,
)
async def get_measure_status(
    project_id: uuid.UUID,
    codes: str = Query(
        ..., description="Comma-separated ENS measure codes (e.g. op.acc.6,mp.info.3)",
    ),
    db: AsyncSession = Depends(get_db),
) -> MeasureStatusResponse:
    """M03 DdA enrichment · bulk lookup cloud_status per measure."""
    await _set_project_context(db, project_id)
    code_list = [c.strip() for c in codes.split(",") if c.strip()]
    statuses = await get_measures_cloud_status_bulk(
        db, project_id=project_id, measure_codes=code_list,
    )
    return MeasureStatusResponse(
        project_id=project_id,
        measures={
            code: {
                "status": s.status,
                "has_open_gap": s.has_open_gap,
                "open_gap_severity": s.open_gap_severity,
                "resources_count": s.resources_count,
            }
            for code, s in statuses.items()
        },
    )


@integrations_router.get(
    "/plan-suggestions", response_model=PlanSuggestionsResponse,
)
async def get_plan_suggestions(
    project_id: uuid.UUID,
    severity_min: str = Query(default="medium"),
    db: AsyncSession = Depends(get_db),
) -> PlanSuggestionsResponse:
    """M04 Plan enrichment · gaps abiertos como acciones sugeridas."""
    await _set_project_context(db, project_id)
    items = []
    async for s in iter_gaps_for_plan_actions(
        db, project_id=project_id, severity_min=severity_min,
    ):
        items.append({
            "ens_measure_code": s.ens_measure_code,
            "title": s.title,
            "description": s.description,
            "priority": s.priority,
            "estimated_effort_days": s.estimated_effort_days,
            "source": s.source,
            "gap_id": s.gap_id,
        })
    return PlanSuggestionsResponse(
        project_id=project_id, severity_min=severity_min, items=items,
    )


@integrations_router.get(
    "/evidence-suggestions/{measure_code}",
    response_model=EvidenceSuggestionsResponse,
)
async def get_evidence_suggestions(
    project_id: uuid.UUID,
    measure_code: str,
    db: AsyncSession = Depends(get_db),
) -> EvidenceSuggestionsResponse:
    """M07 Evidence enrichment · recursos cloud como evidencia auto-attach."""
    await _set_project_context(db, project_id)
    items = []
    async for s in iter_evidences_for_attach(
        db, project_id=project_id, measure_code=measure_code,
    ):
        items.append({
            "resource_type": s.resource_type,
            "resource_name": s.resource_name,
            "resource_external_id": s.resource_external_id,
            "provider": s.provider,
            "evidence_payload": s.evidence_payload,
        })
    return EvidenceSuggestionsResponse(
        project_id=project_id, measure_code=measure_code, items=items,
    )


class ConsolidatedAssetResponse(BaseModel):
    name: str
    resource_type_normalized: str
    provenance: str
    criticidad: str | None = None
    provider: str | None = None
    manual_asset_id: uuid.UUID | None = None
    cloud_resource_id: uuid.UUID | None = None
    cloud_attributes: dict[str, Any] | None = None


class DiscoveryConsolidatedResponse(BaseModel):
    project_id: uuid.UUID
    assets: list[ConsolidatedAssetResponse]
    counts: dict[str, int]


@integrations_router.get(
    "/discovery-consolidated",
    response_model=DiscoveryConsolidatedResponse,
)
async def get_discovery_consolidated(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> DiscoveryConsolidatedResponse:
    """M22 Discovery consolidation · vista unificada manual M22 + cloud detected.

    Sub-fase 1.D.J.B.M22 · resuelve UX overlap entre /discovery (manual)
    y /cloud-connectors (cloud). Pattern K-light additive · NO motor source-code
    modification · ADR-025 sostener firmísimo.
    """
    await _set_project_context(db, project_id)
    view = await consolidate_discovery_with_cloud(db, project_id=project_id)
    return DiscoveryConsolidatedResponse(
        project_id=view.project_id,
        assets=[
            ConsolidatedAssetResponse(
                name=a.name,
                resource_type_normalized=a.resource_type_normalized,
                provenance=a.provenance,
                criticidad=a.criticidad,
                provider=a.provider,
                manual_asset_id=a.manual_asset_id,
                cloud_resource_id=a.cloud_resource_id,
                cloud_attributes=a.cloud_attributes,
            )
            for a in view.assets
        ],
        counts=view.counts,
    )


class EnrichedMageritAssetResponse(BaseModel):
    asset_id: uuid.UUID
    analysis_id: uuid.UUID
    code: str
    name: str
    asset_type_code: str
    value_d: int | None = None
    value_i: int | None = None
    value_c: int | None = None
    value_a: int | None = None
    value_t: int | None = None
    cloud_verified: bool
    cloud_provider: str | None = None
    cloud_resource_id: uuid.UUID | None = None
    cloud_detected_at: str | None = None
    cloud_attributes: dict[str, Any] | None = None


class MageritEnrichedInventoryResponse(BaseModel):
    project_id: uuid.UUID
    assets: list[EnrichedMageritAssetResponse]
    counts: dict[str, int]


class CategorizationHintResponse(BaseModel):
    project_id: uuid.UUID
    hint: dict[str, Any] | None = None
    scaffold: bool = True
    activation_criteria: str


class RiskIndicatorsResponse(BaseModel):
    project_id: uuid.UUID
    indicators: dict[str, Any]
    scaffold: bool = True
    activation_criteria: str


_M01_ACTIVATION = (
    "Activate when cloud detection patterns demonstrate archetype "
    "discrimination value (post-piloto T1 demand-driven evaluation). "
    "Architectural rationale: categorization is INPUT pre-Anexo II · "
    "cloud is OUTPUT-side detection · backwards integration without value "
    "pre-piloto. Wire-up complete · activation deferred per OPS-045 audit-first."
)


_M19_ACTIVATION = (
    "Activate when L-light retainer monitoring scope splits and dedicated "
    "M19 hooks become non-redundant. Architectural rationale: incident "
    "workflow is post-detection · cloud alerts feed L-light retainer "
    "existing · redundancy pre-piloto. Wire-up complete · activation "
    "deferred per OPS-045 audit-first."
)


@integrations_router.get(
    "/categorization-hint",
    response_model=CategorizationHintResponse,
)
async def get_categorization_hint_endpoint(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> CategorizationHintResponse:
    """M01 Categorization cloud archetype hint scaffold (sub-fase 1.D.J.B.M01_M19_SCAFFOLD).

    Returns {hint: null, scaffold: true} por default. Activation criteria
    documented inline + activation path en helper docstring. Pattern K-light
    additive · NO motor M01 source-code modification · ADR-025 firmísimo.
    """
    await _set_project_context(db, project_id)
    hint = await get_categorization_cloud_hint(db, project_id=project_id)
    return CategorizationHintResponse(
        project_id=project_id,
        hint=hint,
        scaffold=True,
        activation_criteria=_M01_ACTIVATION,
    )


@integrations_router.get(
    "/risk-indicators",
    response_model=RiskIndicatorsResponse,
)
async def get_risk_indicators_endpoint(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> RiskIndicatorsResponse:
    """M19 Risk cloud-driven incident indicators scaffold (sub-fase 1.D.J.B.M01_M19_SCAFFOLD).

    Returns {indicators: {}, scaffold: true} por default. Activation criteria
    documented inline + activation path en helper docstring. Pattern K-light
    additive · NO motor M19 source-code modification · ADR-025 firmísimo.
    """
    await _set_project_context(db, project_id)
    indicators = await get_risk_cloud_indicators(db, project_id=project_id)
    return RiskIndicatorsResponse(
        project_id=project_id,
        indicators=indicators,
        scaffold=True,
        activation_criteria=_M19_ACTIVATION,
    )


class FamiliaBreakdownResponse(BaseModel):
    familia: str
    verified: int
    total: int


class ConformityCloudScoreResponse(BaseModel):
    project_id: uuid.UUID
    project_category: str | None = None
    measures_cloud_verified: int
    measures_total_aplicable: int
    score_percentage: float
    per_familia_breakdown: list[FamiliaBreakdownResponse]


@integrations_router.get(
    "/conformity-cloud-score",
    response_model=ConformityCloudScoreResponse,
)
async def get_conformity_cloud_score_endpoint(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ConformityCloudScoreResponse:
    """M27 Conformity cloud verification score · deterministic R1 count-based.

    Sub-fase 1.D.J.B.M27 · auditor ENAC pre-cert visibility cobertura cloud
    verification del project. R1 INVIOLABLE: score formula pure count-based ·
    NUNCA LLM en pipeline. Pattern K-light additive · NO motor M27 source-code
    modification · ADR-025 firmísimo.
    """
    await _set_project_context(db, project_id)
    score = await get_conformity_cloud_score(db, project_id=project_id)
    return ConformityCloudScoreResponse(
        project_id=score.project_id,
        project_category=score.project_category,
        measures_cloud_verified=score.measures_cloud_verified,
        measures_total_aplicable=score.measures_total_aplicable,
        score_percentage=score.score_percentage,
        per_familia_breakdown=[
            FamiliaBreakdownResponse(
                familia=f.familia,
                verified=f.verified,
                total=f.total,
            )
            for f in score.per_familia_breakdown
        ],
    )


@integrations_router.get(
    "/magerit-enriched-inventory",
    response_model=MageritEnrichedInventoryResponse,
)
async def get_magerit_enriched_inventory(
    project_id: uuid.UUID,
    analysis_id: uuid.UUID | None = Query(
        default=None,
        description="Filter to specific MAGERIT analysis ID (optional · default returns all)",
    ),
    db: AsyncSession = Depends(get_db),
) -> MageritEnrichedInventoryResponse:
    """M02 MAGERIT asset inventory enriquecido con cloud verification.

    Sub-fase 1.D.J.B.M02 · resuelve auditor ENAC op.exp.1 Inventario activos
    mapping cloud-detected vs manual. Pattern K-light additive · NO motor M02
    source-code modification · ADR-025 sostener firmísimo.
    """
    await _set_project_context(db, project_id)
    view = await enrich_asset_inventory_with_cloud(
        db, project_id=project_id, analysis_id=analysis_id,
    )
    return MageritEnrichedInventoryResponse(
        project_id=view.project_id,
        assets=[
            EnrichedMageritAssetResponse(
                asset_id=a.asset_id,
                analysis_id=a.analysis_id,
                code=a.code,
                name=a.name,
                asset_type_code=a.asset_type_code,
                value_d=a.value_d,
                value_i=a.value_i,
                value_c=a.value_c,
                value_a=a.value_a,
                value_t=a.value_t,
                cloud_verified=a.cloud_verified,
                cloud_provider=a.cloud_provider,
                cloud_resource_id=a.cloud_resource_id,
                cloud_detected_at=a.cloud_detected_at,
                cloud_attributes=a.cloud_attributes,
            )
            for a in view.assets
        ],
        counts=view.counts,
    )


# ==================================================================
# Monitoring · digest manual trigger admin (sub-fase 1.D.X.VERIFY 2a)
# ==================================================================


from backend.app.motors.m_cloud_connectors.digest_service import (
    DigestProjectNotFoundError,
    generate_monthly_digest_for_project,
    get_latest_digest_for_project,
)


monitoring_router = APIRouter(
    prefix="/admin/projects/{project_id}/cloud-monitoring",
    tags=["Cloud Connectors (1.D.X.VERIFY 2a) - Monitoring"],
    dependencies=[Depends(require_owner)],
)


class DigestSnapshotResponse(BaseModel):
    """Admin view del digest snapshot · full fields (sin filter)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    generated_at: datetime
    triggered_by: str
    triggered_by_user_id: Optional[uuid.UUID]
    compliance_score: int
    open_gaps_total: int
    open_gaps_by_severity: dict[str, int]
    snapshot_jsonb: dict[str, Any]


class DigestGenerateResponse(BaseModel):
    """Response del POST manual trigger."""

    snapshot: DigestSnapshotResponse
    message: str


@monitoring_router.post(
    "/digest/generate", response_model=DigestGenerateResponse, status_code=201,
)
async def trigger_manual_digest(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_owner),
) -> DigestGenerateResponse:
    """Dispara generación digest manual · admin trigger.

    Reuse digest_service · misma lógica que Celery monthly task.
    Audit log entry `manual_digest_triggered_by_admin` se persiste.
    """
    await _set_project_context(db, project_id)
    try:
        snapshot = await generate_monthly_digest_for_project(
            db,
            project_id=project_id,
            triggered_by="admin_manual",
            triggered_by_user_id=user.id,
        )
    except DigestProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await db.commit()
    return DigestGenerateResponse(
        snapshot=DigestSnapshotResponse.model_validate(snapshot),
        message="Digest generado manualmente · cliente notificado automáticamente.",
    )


@monitoring_router.get(
    "/digest/latest", response_model=Optional[DigestSnapshotResponse],
)
async def get_admin_latest_digest(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Optional[DigestSnapshotResponse]:
    """Admin view · último digest snapshot · None si nunca generado."""
    await _set_project_context(db, project_id)
    snapshot = await get_latest_digest_for_project(db, project_id)
    if snapshot is None:
        return None
    return DigestSnapshotResponse.model_validate(snapshot)
