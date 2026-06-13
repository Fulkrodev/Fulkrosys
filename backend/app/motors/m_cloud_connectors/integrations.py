"""Integrations layer · M03 DdA + M04 Plan + M07 Evidence (sub-atom 1.D.X.K v3.12).

Functions ADDITIVE · NO modifica source motors · M03/M04/M07 funcionan sin cloud.

Contract:
  - get_measure_cloud_status(project, measure_code)
      → "implemented" | "missing" | "misconfigured" | "documental" | "unknown"
      Resuelve si una ENS measure tiene evidencia cloud-verifiable.

  - iter_gaps_for_plan_actions(project, severity_min)
      → yields dict listos para crear M04 plan actions (sin escribirlos).
      Plan service decide qué hacer (refresh / auto-populate / dedup).

  - iter_evidences_for_attach(project, measure_code)
      → yields cloud_resources que pueden servir como evidencia M07
      auto-attach (no se attachan automáticamente · M07 decide).

Compatibility:
  - Si project NO tiene CloudConnector activo → status="unknown" (fallback manual M07)
  - Si CloudResources vacíos → status="unknown" para measures cloud-detectables
  - Si gap_engine no ejecutado todavía → 0 results (caller debe trigger primero)

ADR-014 read-only sostener · NO modifica motors source code · OPS-045 sostener.
"""
from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy import and_, case, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m_cloud_connectors.gap_rules import (
    RULE_CATALOG,
    list_supported_measures,
    rules_for_category,
)
from backend.app.motors.m_cloud_connectors.models import (
    CloudGap,
    CloudResource,
)


CloudMeasureStatus = Literal[
    "implemented",     # Detectado y configurado correctamente
    "missing",         # Gap structural emitido · falta la pieza
    "misconfigured",   # Gap configuration · existe pero mal configurado
    "documental",      # Cloud no detecta · cliente debe subir documento
    "unknown",         # Sin datos cloud · fallback manual M07
]


@dataclass
class MeasureCloudStatus:
    """Estado de una ENS measure visto desde cloud (M03 DdA enrichment)."""

    ens_measure_code: str
    status: CloudMeasureStatus
    has_open_gap: bool
    open_gap_severity: str | None = None
    resources_count: int = 0
    """Recursos cloud detectados ligados a esta medida (info contextual)."""


@dataclass
class PlanActionSuggestion:
    """Acción del plan M04 sugerida desde gap cloud detectado."""

    ens_measure_code: str
    title: str
    description: str
    priority: str  # critical / high / medium / low (alineado severity)
    estimated_effort_days: int | None
    source: str = "cloud_gap_engine"
    gap_id: str | None = None


@dataclass
class EvidenceSuggestion:
    """Evidencia M07 sugerida desde recurso cloud verificado."""

    ens_measure_code: str
    resource_type: str
    resource_name: str
    resource_external_id: str
    provider: str
    """Provider de origen (microsoft_365 · aws · etc) · para folder routing."""
    evidence_payload: dict[str, Any]
    """Snapshot atributos del resource para servir como evidence raw_data."""


# ==================================================================
# get_measure_cloud_status (M03 DdA)
# ==================================================================


async def get_measure_cloud_status(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    measure_code: str,
) -> MeasureCloudStatus:
    """Resuelve estado de 1 ENS measure desde cloud data + gap engine.

    Used by M03 DdA service para enriquecer measure_application views.
    """
    supported = set(list_supported_measures())
    is_cloud_detectable = measure_code in supported

    # Lookup gap abierto para esta medida. NOTA: una misma medida puede tener
    # VARIOS gaps abiertos (p.ej. op.exp.8 tiene 3 reglas · varios recursos sin
    # logging → varios gaps). scalar_one_or_none() CRASHEABA (MultipleResultsFound
    # → 500 en /cloud-conformity-score). Tomamos el MÁS SEVERO (critical>high>
    # medium>low) y, a igualdad, el más reciente.
    _sev_rank = case(
        (CloudGap.severity == "critical", 0),
        (CloudGap.severity == "high", 1),
        (CloudGap.severity == "medium", 2),
        (CloudGap.severity == "low", 3),
        else_=4,
    )
    gap_q = await db.execute(
        select(CloudGap).where(
            and_(
                CloudGap.project_id == project_id,
                CloudGap.ens_measure_code == measure_code,
                CloudGap.resolved_at.is_(None),
            ),
        )
        .order_by(_sev_rank, CloudGap.created_at.desc())
        .limit(1)
    )
    open_gap = gap_q.scalars().first()

    # Resources count vinculado a esta measure (heurístico simple por rule_id)
    resources_count = await _count_resources_for_measure(
        db, project_id=project_id, measure_code=measure_code,
    )

    if not is_cloud_detectable:
        return MeasureCloudStatus(
            ens_measure_code=measure_code,
            status="unknown",
            has_open_gap=open_gap is not None,
            open_gap_severity=open_gap.severity if open_gap else None,
            resources_count=resources_count,
        )

    if open_gap is None:
        # Cloud-detectable + sin gap abierto · status implemented
        # (si la regla habría emitido finding · habría gap)
        return MeasureCloudStatus(
            ens_measure_code=measure_code,
            status="implemented",
            has_open_gap=False,
            resources_count=resources_count,
        )

    # Mapeo gap_type → status
    status_map: dict[str, CloudMeasureStatus] = {
        "structural": "missing",
        "reinforcement": "missing",
        "configuration": "misconfigured",
        "documental": "documental",
    }
    return MeasureCloudStatus(
        ens_measure_code=measure_code,
        status=status_map.get(open_gap.gap_type, "missing"),
        has_open_gap=True,
        open_gap_severity=open_gap.severity,
        resources_count=resources_count,
    )


async def get_measures_cloud_status_bulk(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    measure_codes: list[str],
) -> dict[str, MeasureCloudStatus]:
    """Bulk lookup · 1 query para todas las medidas pedidas (M03 list view)."""
    if not measure_codes:
        return {}

    gap_q = await db.execute(
        select(CloudGap).where(
            and_(
                CloudGap.project_id == project_id,
                CloudGap.resolved_at.is_(None),
                CloudGap.ens_measure_code.in_(measure_codes),
            ),
        )
        .order_by(
            case(
                (CloudGap.severity == "critical", 0),
                (CloudGap.severity == "high", 1),
                (CloudGap.severity == "medium", 2),
                (CloudGap.severity == "low", 3),
                else_=4,
            ),
            CloudGap.created_at.desc(),
        )
    )
    # Una medida puede tener VARIOS gaps abiertos (p.ej. op.exp.8 · 3 reglas).
    # Orden por severidad asc → setdefault conserva el PRIMERO = el más severo
    # (determinista · antes el dict-comp dejaba el último arbitrario).
    open_gaps: dict[str, CloudGap] = {}
    for g in gap_q.scalars().all():
        open_gaps.setdefault(g.ens_measure_code, g)

    supported = set(list_supported_measures())
    out: dict[str, MeasureCloudStatus] = {}
    for code in measure_codes:
        is_cloud_detectable = code in supported
        gap = open_gaps.get(code)
        if not is_cloud_detectable:
            out[code] = MeasureCloudStatus(
                ens_measure_code=code,
                status="unknown",
                has_open_gap=gap is not None,
                open_gap_severity=gap.severity if gap else None,
            )
            continue
        if gap is None:
            out[code] = MeasureCloudStatus(
                ens_measure_code=code,
                status="implemented",
                has_open_gap=False,
            )
            continue
        status_map: dict[str, CloudMeasureStatus] = {
            "structural": "missing",
            "reinforcement": "missing",
            "configuration": "misconfigured",
            "documental": "documental",
        }
        out[code] = MeasureCloudStatus(
            ens_measure_code=code,
            status=status_map.get(gap.gap_type, "missing"),
            has_open_gap=True,
            open_gap_severity=gap.severity,
        )
    return out


# ==================================================================
# iter_gaps_for_plan_actions (M04 Plan)
# ==================================================================


_SEVERITY_PRIORITY_ORDER = {
    "critical": 0, "high": 1, "medium": 2, "low": 3,
}


async def iter_gaps_for_plan_actions(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    severity_min: str = "medium",
) -> AsyncIterator[PlanActionSuggestion]:
    """Yields gaps abiertos como plan action suggestions · sorted por severity.

    M04 Plan service llama esto para auto-populate acciones del plan.
    NO escribe · NO deduplica · M04 decide qué hacer (merge / refresh / skip).
    """
    min_order = _SEVERITY_PRIORITY_ORDER.get(severity_min.lower(), 2)
    allowed = {
        sev for sev, order in _SEVERITY_PRIORITY_ORDER.items() if order <= min_order
    }

    q = await db.execute(
        select(CloudGap)
        .where(
            and_(
                CloudGap.project_id == project_id,
                CloudGap.resolved_at.is_(None),
                CloudGap.severity.in_(allowed),
            ),
        )
        .order_by(CloudGap.severity, CloudGap.detected_at.desc()),
    )
    for gap in q.scalars().all():
        yield PlanActionSuggestion(
            ens_measure_code=gap.ens_measure_code,
            title=gap.title,
            description=gap.explanation_es or gap.title,
            priority=gap.severity,
            estimated_effort_days=gap.estimated_effort_days,
            gap_id=str(gap.id),
        )


# ==================================================================
# iter_evidences_for_attach (M07 Evidence)
# ==================================================================


# Heurística simple: cada rule sabe qué resource_types son evidencia válida
# (acoplado al rule catalog · mantener sync si añadimos nuevas reglas)
_MEASURE_TO_RESOURCE_TYPES: dict[str, tuple[str, ...]] = {
    "op.acc.6": ("identity.user",),       # MFA users
    "op.acc.2": ("identity.user",),       # Privilegios mínimos (antes op.acc.5)
    "op.exp.1": ("asset.repo", "asset.bucket", "asset.storage", "asset.vm"),
    "mp.si.2": ("asset.bucket", "asset.storage", "asset.volume"),  # Cifrado at-rest (antes mp.info.3)
    "mp.s.2": ("asset.bucket", "asset.storage"),
    "op.exp.8": ("asset.bucket", "asset.storage", "asset.vm"),
    "mp.info.6": ("asset.bucket", "asset.storage", "asset.volume", "asset.database"),  # Backups (antes op.cont.3)
}


async def iter_evidences_for_attach(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    measure_code: str,
    limit: int = 50,
) -> AsyncIterator[EvidenceSuggestion]:
    """Yields cloud resources servibles como evidence M07 para una measure.

    Useful cuando admin/cliente quiere "demostrar implementación" de una medida
    sin re-subir documento · usa snapshot del cloud resource.
    """
    resource_types = _MEASURE_TO_RESOURCE_TYPES.get(measure_code)
    if not resource_types:
        return

    # JOIN cloud_resources + cloud_connectors para resolver provider
    from backend.app.motors.m_cloud_connectors.models import CloudConnector
    q = await db.execute(
        select(CloudResource, CloudConnector.provider)
        .join(
            CloudConnector,
            CloudConnector.id == CloudResource.connector_id,
        )
        .where(
            and_(
                CloudResource.project_id == project_id,
                CloudResource.resource_type.in_(resource_types),
            ),
        )
        .order_by(CloudResource.detected_at.desc())
        .limit(limit)
    )

    for resource, provider in q.all():
        yield EvidenceSuggestion(
            ens_measure_code=measure_code,
            resource_type=resource.resource_type,
            resource_name=resource.resource_name or resource.resource_external_id,
            resource_external_id=resource.resource_external_id,
            provider=provider,
            evidence_payload={
                "attributes_snapshot": resource.attributes,
                "checksum": resource.checksum,
                "detected_at": resource.detected_at.isoformat()
                    if resource.detected_at else None,
            },
        )


# ==================================================================
# Helpers internos
# ==================================================================


async def _count_resources_for_measure(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    measure_code: str,
) -> int:
    """Aproximación count · heurística rule_to_resource_types."""
    rtypes = _MEASURE_TO_RESOURCE_TYPES.get(measure_code)
    if not rtypes:
        return 0
    from sqlalchemy import func
    q = await db.execute(
        select(func.count())
        .select_from(CloudResource)
        .where(
            and_(
                CloudResource.project_id == project_id,
                CloudResource.resource_type.in_(rtypes),
            ),
        ),
    )
    return q.scalar() or 0


# ==================================================================
# consolidate_discovery_with_cloud (M22 Discovery · sub-fase 1.D.J.B.M22)
# ==================================================================


@dataclass
class ConsolidatedAsset:
    """Asset consolidado · vista unificada M22 manual + cloud-detected.

    Logic match deterministic R1 (NO LLM): normalized name (case-insensitive trim)
    + tipo_normalized prefix · provenance derivada.
    """

    name: str
    """Nombre del asset normalizado (preserves capital from source preferred)."""

    resource_type_normalized: str
    """Tipo unificado (cloud resource_type si available · MAGERIT tipo si manual)."""

    provenance: Literal["manual", "cloud", "both"]
    """Origen del asset · manual=M22 only · cloud=CloudResource only · both=match."""

    criticidad: str | None = None
    """Criticidad propuesta M22 (manual·both) · None si cloud-only."""

    provider: str | None = None
    """Provider cloud (microsoft_365·aws·etc) si cloud o both · None si manual."""

    manual_asset_id: uuid.UUID | None = None
    """DiscoveredAsset.id si manual o both."""

    cloud_resource_id: uuid.UUID | None = None
    """CloudResource.id si cloud o both."""

    cloud_attributes: dict[str, Any] | None = None
    """JSONB snapshot cloud resource attributes (prefer cloud data si conflict)."""


@dataclass
class DiscoveryConsolidatedView:
    """Vista consolidada discovery cross-source · M22 + cloud_connectors."""

    project_id: uuid.UUID
    assets: list[ConsolidatedAsset]
    counts: dict[str, int]
    """Buckets: manual_only · cloud_only · both · total."""


def _normalize_asset_name(name: str | None) -> str:
    """Canonical key para match · lowercase + strip + collapse whitespace."""
    if not name:
        return ""
    return " ".join(name.strip().lower().split())


def _normalize_resource_type(t: str | None) -> str:
    """Canonical tipo · CloudResource resource_type (asset.X) o MAGERIT tipo crudo.

    Heuristics:
    - Cloud format `asset.bucket` → `bucket`
    - MAGERIT format `[D]` o `[HW]` → preserved
    - Otherwise lowercase prefix
    """
    if not t:
        return ""
    if t.startswith("asset."):
        return t.split(".", 1)[1].lower()
    return t.strip().lower()


async def consolidate_discovery_with_cloud(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
) -> DiscoveryConsolidatedView:
    """Consolida assets M22 (DiscoveredAsset) + cloud (CloudResource) project-scoped.

    Used by M22 Discovery UI para mostrar inventario consolidado con badges
    manual/cloud/both. Resuelve overlap UX entre /discovery (manual) y
    /cloud-connectors (cloud).

    Match logic: por _normalize_asset_name (case-insensitive trim) · si match
    entre manual y cloud lists → provenance="both" + prefer cloud_attributes.
    Si manual_only → "manual" · cloud_only → "cloud".
    """
    from backend.app.models.onboarding import DiscoveredAsset
    from backend.app.motors.m_cloud_connectors.models import CloudConnector

    # 1. Fetch DiscoveredAsset M22 (manual)
    m22_q = await db.execute(
        select(DiscoveredAsset).where(
            and_(
                DiscoveredAsset.project_id == project_id,
                DiscoveredAsset.deleted_at.is_(None),
            ),
        )
    )
    manual_assets = list(m22_q.scalars().all())

    # 2. Fetch CloudResource (cloud-detected) con provider via JOIN
    cloud_q = await db.execute(
        select(CloudResource, CloudConnector.provider)
        .join(
            CloudConnector,
            CloudConnector.id == CloudResource.connector_id,
        )
        .where(CloudResource.project_id == project_id)
    )
    cloud_pairs = list(cloud_q.all())

    # 3. Index by normalized name
    manual_by_name: dict[str, Any] = {
        _normalize_asset_name(a.nombre): a for a in manual_assets
    }
    cloud_by_name: dict[str, tuple[Any, str]] = {}
    for resource, provider in cloud_pairs:
        key = _normalize_asset_name(resource.resource_name or resource.resource_external_id)
        cloud_by_name[key] = (resource, provider)

    # 4. Build consolidated list
    consolidated: list[ConsolidatedAsset] = []
    all_keys = set(manual_by_name.keys()) | set(cloud_by_name.keys())
    counts = {"manual_only": 0, "cloud_only": 0, "both": 0, "total": 0}

    for key in sorted(all_keys):
        if not key:
            continue
        manual = manual_by_name.get(key)
        cloud_pair = cloud_by_name.get(key)

        if manual and cloud_pair:
            resource, provider = cloud_pair
            consolidated.append(
                ConsolidatedAsset(
                    name=resource.resource_name or manual.nombre,
                    resource_type_normalized=_normalize_resource_type(
                        resource.resource_type or manual.tipo_magerit,
                    ),
                    provenance="both",
                    criticidad=manual.criticidad_propuesta,
                    provider=provider,
                    manual_asset_id=manual.id,
                    cloud_resource_id=resource.id,
                    cloud_attributes=resource.attributes,
                )
            )
            counts["both"] += 1
        elif manual:
            consolidated.append(
                ConsolidatedAsset(
                    name=manual.nombre,
                    resource_type_normalized=_normalize_resource_type(manual.tipo_magerit),
                    provenance="manual",
                    criticidad=manual.criticidad_propuesta,
                    manual_asset_id=manual.id,
                )
            )
            counts["manual_only"] += 1
        elif cloud_pair:
            resource, provider = cloud_pair
            consolidated.append(
                ConsolidatedAsset(
                    name=resource.resource_name or resource.resource_external_id,
                    resource_type_normalized=_normalize_resource_type(resource.resource_type),
                    provenance="cloud",
                    provider=provider,
                    cloud_resource_id=resource.id,
                    cloud_attributes=resource.attributes,
                )
            )
            counts["cloud_only"] += 1

    counts["total"] = len(consolidated)

    return DiscoveryConsolidatedView(
        project_id=project_id,
        assets=consolidated,
        counts=counts,
    )


# ==================================================================
# enrich_asset_inventory_with_cloud (M02 MAGERIT · sub-fase 1.D.J.B.M02)
# ==================================================================


@dataclass
class EnrichedMageritAsset:
    """Asset MAGERIT enriquecido con verificación cloud · NO modifica M02 source.

    cloud_verified=True si name (case-insensitive trim) matches CloudResource
    activo del mismo project_id. Pattern K-light additive consistente con
    M22 consolidation (sub-fase 1.D.J.B.M22 v3.12).
    """

    asset_id: uuid.UUID
    analysis_id: uuid.UUID
    code: str
    name: str
    asset_type_code: str
    value_d: int | None
    value_i: int | None
    value_c: int | None
    value_a: int | None
    value_t: int | None

    cloud_verified: bool
    """True si match con CloudResource por name normalized."""

    cloud_provider: str | None = None
    cloud_resource_id: uuid.UUID | None = None
    cloud_detected_at: str | None = None
    """ISO timestamp si detected · None si manual_only."""
    cloud_attributes: dict[str, Any] | None = None


@dataclass
class EnrichedMageritInventory:
    """Vista MAGERIT asset inventory enriquecida con cloud verification."""

    project_id: uuid.UUID
    assets: list[EnrichedMageritAsset]
    counts: dict[str, int]
    """Buckets: total · cloud_verified · manual_only."""


async def enrich_asset_inventory_with_cloud(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    analysis_id: uuid.UUID | None = None,
) -> EnrichedMageritInventory:
    """Enriquece MageritAsset inventory con cloud verification status.

    Used by M02 MAGERIT UI para column "Cloud verified" + stats card +
    filter "Solo cloud-verified". Resuelve op.exp.1 Inventario activos
    auditor ENAC mapping cloud-detected vs manual-declared.

    Match logic deterministic R1 (consistente M22): por _normalize_asset_name
    (case-insensitive trim) · si MageritAsset.name matches CloudResource.resource_name
    → cloud_verified=True + provider/detected_at/attributes injected.

    Compatibility: project sin CloudConnector activo → all assets cloud_verified=False
    (counts.cloud_verified=0 · UI degrada gracefully).

    Pattern K-light ADDITIVE · NO motor M02 source-code modification.
    """
    from backend.app.motors.m02_magerit.models import (
        MageritAnalysis,
        MageritAsset,
    )
    from backend.app.motors.m_cloud_connectors.models import CloudConnector

    # 1. Fetch MageritAsset JOIN MageritAnalysis WHERE project_id matches
    stmt = (
        select(MageritAsset, MageritAnalysis.id)
        .join(MageritAnalysis, MageritAnalysis.id == MageritAsset.analysis_id)
        .where(
            and_(
                MageritAnalysis.project_id == project_id,
                MageritAsset.deleted_at.is_(None),
            ),
        )
    )
    if analysis_id is not None:
        stmt = stmt.where(MageritAnalysis.id == analysis_id)

    asset_q = await db.execute(stmt)
    asset_rows = list(asset_q.all())

    # 2. Fetch CloudResource project-scoped JOIN provider via CloudConnector
    cloud_q = await db.execute(
        select(CloudResource, CloudConnector.provider)
        .join(
            CloudConnector,
            CloudConnector.id == CloudResource.connector_id,
        )
        .where(CloudResource.project_id == project_id)
    )
    cloud_pairs = list(cloud_q.all())

    # 3. Index cloud por normalized name
    cloud_by_name: dict[str, tuple[Any, str]] = {}
    for resource, provider in cloud_pairs:
        key = _normalize_asset_name(
            resource.resource_name or resource.resource_external_id,
        )
        if key:
            cloud_by_name[key] = (resource, provider)

    # 4. Build enriched list
    enriched: list[EnrichedMageritAsset] = []
    counts = {"total": 0, "cloud_verified": 0, "manual_only": 0}

    for asset, ana_id in asset_rows:
        key = _normalize_asset_name(asset.name)
        cloud_match = cloud_by_name.get(key)

        if cloud_match:
            resource, provider = cloud_match
            enriched.append(
                EnrichedMageritAsset(
                    asset_id=asset.id,
                    analysis_id=ana_id,
                    code=asset.code,
                    name=asset.name,
                    asset_type_code=asset.asset_type_code,
                    value_d=asset.value_d,
                    value_i=asset.value_i,
                    value_c=asset.value_c,
                    value_a=asset.value_a,
                    value_t=asset.value_t,
                    cloud_verified=True,
                    cloud_provider=provider,
                    cloud_resource_id=resource.id,
                    cloud_detected_at=(
                        resource.detected_at.isoformat()
                        if resource.detected_at else None
                    ),
                    cloud_attributes=resource.attributes,
                )
            )
            counts["cloud_verified"] += 1
        else:
            enriched.append(
                EnrichedMageritAsset(
                    asset_id=asset.id,
                    analysis_id=ana_id,
                    code=asset.code,
                    name=asset.name,
                    asset_type_code=asset.asset_type_code,
                    value_d=asset.value_d,
                    value_i=asset.value_i,
                    value_c=asset.value_c,
                    value_a=asset.value_a,
                    value_t=asset.value_t,
                    cloud_verified=False,
                )
            )
            counts["manual_only"] += 1

    counts["total"] = len(enriched)

    return EnrichedMageritInventory(
        project_id=project_id,
        assets=enriched,
        counts=counts,
    )


# ==================================================================
# get_conformity_cloud_score (M27 Conformity · sub-fase 1.D.J.B.M27)
# ==================================================================


@dataclass
class FamiliaBreakdown:
    """Per-familia ENS aggregate · verified/total measures cubiertas cloud."""

    familia: str
    """ENS familia normalized (op.acc · op.exp · mp.s · mp.info · op.cont · org)."""

    verified: int
    total: int


@dataclass
class ConformityCloudScore:
    """M27 Conformity cloud verification score · deterministic R1 count-based.

    score_percentage es ratio verified/total · NUNCA LLM · trazabilidad ENAC
    pre-cert. Pattern K-light additive · NO motor M27 source-code modification.
    """

    project_id: uuid.UUID
    project_category: str | None
    """BASICA · MEDIA · ALTA · None si project sin categoria_objetivo."""

    measures_cloud_verified: int
    measures_total_aplicable: int
    score_percentage: float
    """0.0-100.0 · 1 decimal · 0 si total_aplicable=0 (degradado gracefully)."""

    per_familia_breakdown: list[FamiliaBreakdown]
    """Ordenado alfabéticamente por familia name (deterministic)."""


def _familia_for_measure(code: str) -> str:
    """ENS familia normalized · 'op.acc.6' → 'op.acc' · 'org.1' → 'org'."""
    parts = code.split(".")
    if not parts:
        return code
    if parts[0] == "org":
        return "org"
    if len(parts) >= 2:
        return f"{parts[0]}.{parts[1]}"
    return parts[0]


async def get_conformity_cloud_score(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
) -> ConformityCloudScore:
    """Calcula conformity cloud verification score deterministic R1.

    Used by M27 Conformity UI para stats card + familia breakdown + declaration
    badge. Auditor ENAC pre-cert ve cobertura cloud verification del project.

    Logic:
    - 1. Resolve project.categoria_objetivo · filter rules_for_category() si set
         · else use full RULE_CATALOG (8 measures base)
    - 2. Check has_connectors · si 0 conectores activos → all measures unknown
         (counts.verified=0 · UI degrada gracefully · R29 NO presión)
    - 3. Per measure: get_measure_cloud_status status
         · 'implemented' OR 'misconfigured' → verified=True (cloud evidence)
         · 'missing' · 'documental' · 'unknown' → verified=False
    - 4. Aggregate per familia normalized
    - 5. score_percentage = verified/total * 100 (1 decimal)

    NUNCA LLM en pipeline · R1 INVIOLABLE sostener. score formula pure count-based.

    Compatibility:
    - Project sin CloudConnector → 0/N verified (graceful UI empty state)
    - Project sin categoria_objetivo → RULE_CATALOG full (8 measures)
    - 0 cloud_resources · 0 gaps emitted → measures con get_measure_cloud_status
      retornan 'unknown' (NO false positive 'implemented' si sin scan)

    Pattern K-light ADDITIVE · NO motor M27 source-code modification · ADR-025.
    """
    from backend.app.models.core import Project
    from backend.app.motors.m_cloud_connectors.models import (
        CloudConnector,
        CloudConnectorStatus,
    )
    from sqlalchemy import func

    # 1. Project category lookup
    pj_q = await db.execute(
        select(Project.categoria_objetivo).where(Project.id == project_id)
    )
    category = pj_q.scalar_one_or_none()

    # 2. Applicable rules · category-filtered if known · else full catalog
    if category and category.upper() in {"BASICA", "MEDIA", "ALTA"}:
        applicable_rules = rules_for_category(category)
    else:
        applicable_rules = RULE_CATALOG

    measures_codes = sorted({r.ens_measure_code for r in applicable_rules})

    # 3. Connectors activos check · si 0 → measures unknown (graceful)
    conn_q = await db.execute(
        select(func.count())
        .select_from(CloudConnector)
        .where(
            and_(
                CloudConnector.project_id == project_id,
                CloudConnector.status != CloudConnectorStatus.REVOKED.value,
            ),
        )
    )
    has_connectors = (conn_q.scalar() or 0) > 0

    # 4. Per measure: determine verified · aggregate familia counts
    verified_count = 0
    familia_counts: dict[str, dict[str, int]] = {}

    for measure_code in measures_codes:
        familia = _familia_for_measure(measure_code)
        if familia not in familia_counts:
            familia_counts[familia] = {"verified": 0, "total": 0}
        familia_counts[familia]["total"] += 1

        if not has_connectors:
            # Sin conectores · NO cloud verification posible · skip status check
            continue

        status = await get_measure_cloud_status(
            db, project_id=project_id, measure_code=measure_code,
        )
        # Brief R1 INVIOLABLE: implemented OR misconfigured = verified
        # (cloud detected evidence presence · misconfigured still has detection)
        if status.status in ("implemented", "misconfigured"):
            verified_count += 1
            familia_counts[familia]["verified"] += 1

    total_applicable = len(measures_codes)
    if total_applicable > 0:
        score_pct = round((verified_count / total_applicable) * 100, 1)
    else:
        score_pct = 0.0

    breakdown = [
        FamiliaBreakdown(
            familia=f,
            verified=c["verified"],
            total=c["total"],
        )
        for f, c in sorted(familia_counts.items())
    ]

    return ConformityCloudScore(
        project_id=project_id,
        project_category=category,
        measures_cloud_verified=verified_count,
        measures_total_aplicable=total_applicable,
        score_percentage=score_pct,
        per_familia_breakdown=breakdown,
    )


# ==================================================================
# M01 + M19 scaffolds · sub-fase 1.D.J.B.M01_M19_SCAFFOLD
# ==================================================================
# Wire-up complete · activation deferred per OPS-045 audit-first.
# Cumple directiva "5 motores wired pre-1.E" architect "todo perfecto literalmente".
# 0 silent debt · 0 over-engineering · scaffolds invisibles audit-friendly.


async def get_categorization_cloud_hint(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
) -> None:
    """Reserved for future M01 cloud archetype hints (D/I/C/A/T discrimination).

    Activate when cloud detection patterns demonstrate archetype value
    (post-piloto T1 demand-driven evaluation).

    Architectural rationale: categorization is INPUT pre-Anexo II · cloud is
    OUTPUT-side detection · backwards integration without value pre-piloto.
    Wire-up complete · activation deferred per OPS-045 audit-first.

    Currently returns None (scaffold default). Activation path:
    1. Define heuristics CloudResource composition → archetype suggestion
       (e.g. heavy data.* presence → "PYME datos críticos" archetype)
    2. Return ArchetypeCloudHint dataclass con suggested_category + rationale
    3. Wire M01 archetype_api consumer optional · NO replace manual choice
    """
    _ = db, project_id  # Reserved · NO side effects scaffold default
    return None


async def get_risk_cloud_indicators(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
) -> dict[str, Any]:
    """Reserved for future M19 cloud-driven incident indicators.

    Activate when L-light retainer monitoring scope splits and dedicated M19
    hooks become non-redundant.

    Architectural rationale: incident workflow is post-detection · cloud
    alerts feed L-light retainer existing · redundancy pre-piloto. Wire-up
    complete · activation deferred per OPS-045 audit-first.

    Currently returns {} (scaffold default). Activation path:
    1. Aggregate CloudGap.severity counts → risk_level indicators per familia
    2. Map to M19 incident_workflow precursor signals (NO trigger incidents
       directly · M19 service owns workflow R1)
    3. Wire M19 BIA service optional · NO replace manual risk assessment
    """
    _ = db, project_id  # Reserved · NO side effects scaffold default
    return {}


# ==================================================================
# Convenience: helpers exportados para UIs/services consumidores
# ==================================================================


__all__ = [
    "CloudMeasureStatus",
    "ConformityCloudScore",
    "ConsolidatedAsset",
    "DiscoveryConsolidatedView",
    "EnrichedMageritAsset",
    "EnrichedMageritInventory",
    "EvidenceSuggestion",
    "FamiliaBreakdown",
    "MeasureCloudStatus",
    "PlanActionSuggestion",
    "consolidate_discovery_with_cloud",
    "enrich_asset_inventory_with_cloud",
    "get_categorization_cloud_hint",
    "get_conformity_cloud_score",
    "get_measure_cloud_status",
    "get_measures_cloud_status_bulk",
    "get_risk_cloud_indicators",
    "iter_evidences_for_attach",
    "iter_gaps_for_plan_actions",
]
