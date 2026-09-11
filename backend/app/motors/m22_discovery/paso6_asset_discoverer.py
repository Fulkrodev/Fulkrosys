"""M22 Paso 6 — Asset Discoverer con integracion M21 + M2 MAGERIT.

Extiende el `asset_discovery` basico con:
- Resolucion de propietario a stakeholder_id (M21) via email/departamento
- Inferencia de ubicacion (on-prem / cloud-region / saas)
- Feed explicito a M2 MAGERIT: cada asset descubierto genera MageritAsset
  en la version draft de MageritAnalysis del proyecto
- Reconciliacion (upsert) por external_id para discovery incremental
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.diagnosis import Stakeholder
from backend.app.models.onboarding import DiscoveredAsset
from backend.app.motors.m02_magerit.analisis_vigente import analisis_vigente
from backend.app.motors.m02_magerit.models import MageritAnalysis, MageritAsset
from backend.app.motors.m16_onboarding.connectors.base import DiscoveredAssetDTO
from backend.app.motors.m22_discovery import asset_discovery

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# Resolucion propietario M21
# ════════════════════════════════════════════════════════════════════

async def _load_stakeholders_index(
    db: AsyncSession, project_id: uuid.UUID,
) -> dict[str, Stakeholder]:
    """Indice email/departamento -> Stakeholder para resolucion rapida."""
    r = await db.execute(
        select(Stakeholder).where(
            Stakeholder.project_id == project_id,
            Stakeholder.deleted_at.is_(None),
        )
    )
    out: dict[str, Stakeholder] = {}
    for s in r.scalars().all():
        if s.email:
            out[s.email.lower()] = s
        if s.departamento:
            out.setdefault(f"dept:{s.departamento.lower()}", s)
    return out


def resolve_owner(
    dto: DiscoveredAssetDTO,
    stakeholders_by_key: dict[str, Stakeholder],
) -> tuple[Optional[uuid.UUID], Optional[str]]:
    """Intenta resolver stakeholder_id + nombre propietario.

    Heuristicas en orden:
    1. raw_data.owner_email == stakeholder.email
    2. raw_data.owner == stakeholder.nombre
    3. raw_data.department == stakeholder.departamento (primer match)
    4. tags contain 'dept:<departamento>'
    """
    raw = dto.raw_data or {}
    # (1) email
    email = (raw.get("owner_email") or raw.get("email") or "").lower()
    if email and email in stakeholders_by_key:
        s = stakeholders_by_key[email]
        return s.id, s.nombre
    # (2) nombre literal
    owner_name = (raw.get("owner") or raw.get("propietario") or "").strip()
    if owner_name:
        for s in stakeholders_by_key.values():
            if (s.nombre or "").lower() == owner_name.lower():
                return s.id, s.nombre
    # (3) department
    dept = (raw.get("department") or raw.get("departamento") or "").lower()
    if dept and f"dept:{dept}" in stakeholders_by_key:
        s = stakeholders_by_key[f"dept:{dept}"]
        return s.id, s.nombre
    # (4) tag dept:xxx
    for t in (dto.tags or []):
        if isinstance(t, str) and t.startswith("dept:"):
            key = t.lower()
            if key in stakeholders_by_key:
                s = stakeholders_by_key[key]
                return s.id, s.nombre
    return None, owner_name or None


# ════════════════════════════════════════════════════════════════════
# Inferencia ubicacion (on-prem / cloud-region / saas)
# ════════════════════════════════════════════════════════════════════

_CLOUD_PROVIDERS = {"aws", "azure", "google_workspace", "gcp"}
_SAAS_PROVIDERS = {"microsoft_365", "github", "slack", "atlassian"}


def infer_location(dto: DiscoveredAssetDTO) -> str:
    raw = dto.raw_data or {}
    explicit = raw.get("region") or raw.get("location") or raw.get("ubicacion")
    if isinstance(explicit, str) and explicit:
        prov = (dto.provider or "").lower()
        if prov in _CLOUD_PROVIDERS:
            return f"{prov}:{explicit}"
        return explicit
    prov = (dto.provider or "").lower()
    if prov in _SAAS_PROVIDERS:
        return f"saas:{prov}"
    if prov in _CLOUD_PROVIDERS:
        return f"{prov}:unknown_region"
    return "on_prem"


# ════════════════════════════════════════════════════════════════════
# Persistencia enriquecida
# ════════════════════════════════════════════════════════════════════

async def _find_existing_asset(
    db: AsyncSession, project_id: uuid.UUID, provider: str, external_id: str,
) -> Optional[DiscoveredAsset]:
    r = await db.execute(
        select(DiscoveredAsset).where(
            DiscoveredAsset.project_id == project_id,
            DiscoveredAsset.fuente_conector == provider,
            DiscoveredAsset.identificador == external_id,
            DiscoveredAsset.deleted_at.is_(None),
        )
    )
    return r.scalar_one_or_none()


async def upsert_discovered_asset(
    db: AsyncSession,
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    provider: str,
    dto: DiscoveredAssetDTO,
    stakeholders_by_key: dict[str, Stakeholder],
) -> tuple[DiscoveredAsset, bool]:
    """Crea o actualiza DiscoveredAsset para discovery incremental.

    Returns (asset, created): created=True si es nuevo.
    """
    metadata = dict(dto.raw_data or {})
    if dto.tags:
        metadata.setdefault("tags", list(dto.tags))
    tipo = asset_discovery.classify_magerit_type(dto.asset_type, metadata)
    crit = asset_discovery.infer_criticality(tipo, metadata)
    ubicacion = infer_location(dto)
    owner_id, owner_name = resolve_owner(dto, stakeholders_by_key)
    metadata["ubicacion_paso6"] = ubicacion
    if owner_id:
        metadata["stakeholder_id"] = str(owner_id)

    existing = await _find_existing_asset(
        db, project_id, provider, dto.external_id,
    )
    if existing is not None:
        existing.discovery_run_id = run_id
        existing.tipo_magerit = tipo
        existing.criticidad_propuesta = crit
        existing.ubicacion = ubicacion
        existing.propietario_inferido = owner_name or existing.propietario_inferido
        merged_meta = dict(existing.metadata_extra or {})
        merged_meta.update(metadata)
        existing.metadata_extra = merged_meta
        await db.flush()
        return existing, False

    asset = DiscoveredAsset(
        project_id=project_id,
        discovery_run_id=run_id,
        fuente_conector=provider,
        tipo_magerit=tipo,
        nombre=dto.name,
        identificador=dto.external_id,
        descripcion=metadata.get("description"),
        criticidad_propuesta=crit,
        propietario_inferido=owner_name,
        ubicacion=ubicacion,
        metadata_extra=metadata,
    )
    db.add(asset)
    await db.flush()
    return asset, True


async def discover_and_enrich(
    db: AsyncSession,
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    provider: str,
    dtos: list[DiscoveredAssetDTO],
) -> dict[str, Any]:
    """Persiste assets con enriquecimiento propietario+ubicacion.

    Returns summary dict:
    - total_processed
    - created
    - updated
    - assigned_owner: count con stakeholder_id resuelto
    - by_tipo_magerit
    - by_ubicacion
    """
    stakeholders_index = await _load_stakeholders_index(db, project_id)
    summary: dict[str, Any] = {
        "total_processed": 0,
        "created": 0,
        "updated": 0,
        "assigned_owner": 0,
        "by_tipo_magerit": {},
        "by_ubicacion": {},
    }
    for dto in dtos or []:
        asset, created = await upsert_discovered_asset(
            db, project_id, run_id, provider, dto, stakeholders_index,
        )
        summary["total_processed"] += 1
        if created:
            summary["created"] += 1
        else:
            summary["updated"] += 1
        if (asset.metadata_extra or {}).get("stakeholder_id"):
            summary["assigned_owner"] += 1
        summary["by_tipo_magerit"][asset.tipo_magerit] = (
            summary["by_tipo_magerit"].get(asset.tipo_magerit, 0) + 1
        )
        summary["by_ubicacion"][asset.ubicacion or "unknown"] = (
            summary["by_ubicacion"].get(asset.ubicacion or "unknown", 0) + 1
        )
    return summary


# ════════════════════════════════════════════════════════════════════
# Feed a M2 MAGERIT
# ════════════════════════════════════════════════════════════════════

# DICAT base por criticidad. Valores 0-10 (escala MAGERIT v3)
_DICAT_BY_CRIT: dict[str, dict[str, int]] = {
    "muy_alta": {"D": 9, "I": 8, "C": 8, "A": 8, "T": 7},
    "alta":     {"D": 8, "I": 7, "C": 7, "A": 7, "T": 6},
    "media":    {"D": 6, "I": 6, "C": 5, "A": 5, "T": 5},
    "baja":     {"D": 4, "I": 4, "C": 3, "A": 3, "T": 3},
    "muy_baja": {"D": 2, "I": 2, "C": 2, "A": 2, "T": 2},
}


async def _get_or_create_magerit_analysis(
    db: AsyncSession, project_id: uuid.UUID,
) -> MageritAnalysis:
    # O2 · la regla "cual es el analisis vigente" se lee de su unica fuente;
    # aqui solo queda el "si no hay, crealo".
    existing = await analisis_vigente(db, project_id)
    if existing is not None:
        return existing
    analysis = MageritAnalysis(
        project_id=project_id,
        name="MAGERIT v3 — generado desde M22 Discovery",
        version=1,
        status="draft",
        calculation_mode="qualitative",
        methodology_version="MAGERIT v3",
        notes="Creado automaticamente por M22 Paso 6 (Discovery)",
    )
    db.add(analysis)
    await db.flush()
    return analysis


def _safe_code(prefix: str, external_id: str) -> str:
    clean = "".join(ch for ch in external_id if ch.isalnum() or ch in "-_")
    return f"{prefix}-{clean[:40]}"[:50]


async def feed_magerit_assets(
    db: AsyncSession, project_id: uuid.UUID,
) -> dict[str, Any]:
    """Crea/actualiza MageritAsset por cada DiscoveredAsset no-borrado.

    Idempotente: busca por (analysis_id, code). Si existe, no duplica.
    """
    analysis = await _get_or_create_magerit_analysis(db, project_id)

    r = await db.execute(
        select(DiscoveredAsset).where(
            DiscoveredAsset.project_id == project_id,
            DiscoveredAsset.deleted_at.is_(None),
        )
    )
    discovered = list(r.scalars().all())

    r = await db.execute(
        select(MageritAsset.code).where(MageritAsset.analysis_id == analysis.id)
    )
    existing_codes = {row[0] for row in r.all()}

    created = 0
    created_codes: list[str] = []
    for d in discovered:
        code = _safe_code(d.tipo_magerit or "XX", d.identificador or str(d.id))
        if code in existing_codes:
            continue
        dicat = _DICAT_BY_CRIT.get(
            (d.criticidad_propuesta or "media"), _DICAT_BY_CRIT["media"],
        )
        asset = MageritAsset(
            analysis_id=analysis.id,
            code=code,
            name=d.nombre,
            asset_type_code=d.tipo_magerit or "SW",
            description=(
                f"Derivado de M22 Discovery ({d.fuente_conector}). "
                f"Ubicacion: {d.ubicacion or 'desconocida'}."
            ),
            owner=d.propietario_inferido,
            value_d=dicat["D"], value_i=dicat["I"], value_c=dicat["C"],
            value_a=dicat["A"], value_t=dicat["T"],
        )
        db.add(asset)
        existing_codes.add(code)
        created_codes.append(code)
        created += 1

    await db.flush()
    return {
        "analysis_id": str(analysis.id),
        "analysis_status": analysis.status,
        "total_discovered": len(discovered),
        "magerit_created": created,
        "magerit_codes": created_codes,
    }


__all__ = [
    "resolve_owner",
    "infer_location",
    "upsert_discovered_asset",
    "discover_and_enrich",
    "feed_magerit_assets",
]
