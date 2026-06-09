"""Asset Discovery Service (M22).

Normaliza assets crudos descubiertos por connectors M16 (M365, AWS, Azure,
GitHub, Google Workspace) en filas de discovered_assets con clasificacion
MAGERIT v3 y criticidad inferida. Integra con PKG-lite.
"""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.onboarding import DiscoveredAsset
from backend.app.motors.m16_onboarding import pkg_service as pkg
from backend.app.motors.m16_onboarding.connectors.base import (
    DiscoveredAssetDTO,
)
from backend.app.motors.m22_discovery.magerit_categories import MageritCategory


# Criticidad base por tipo MAGERIT (codes legacy match enum.value)
CRITICALITY_BASE: dict[str, str] = {
    MageritCategory.COMUNICACIONES.value: "alta",
    MageritCategory.INFORMACION.value: "alta",
    MageritCategory.HARDWARE.value: "media",
    MageritCategory.SOFTWARE.value: "media",
    MageritCategory.SERVICIOS.value: "media",
    MageritCategory.PERSONAL.value: "media",
    MageritCategory.AUXILIAR.value: "baja",
    MageritCategory.INSTALACIONES.value: "media",
    MageritCategory.SOPORTES.value: "media",
}

_CRIT_ORDER = ["muy_baja", "baja", "media", "alta", "muy_alta"]


def _bump_criticality(current: str, delta: int = 1) -> str:
    try:
        idx = _CRIT_ORDER.index(current)
    except ValueError:
        return current
    new_idx = max(0, min(len(_CRIT_ORDER) - 1, idx + delta))
    return _CRIT_ORDER[new_idx]


def classify_magerit_type(resource_type: str, metadata: Optional[dict] = None) -> str:
    """Clasifica un recurso en tipo MAGERIT (string code).

    Wrapper backward-compat sobre ``MageritCategory.from_resource_type``.
    Retorna ``MageritCategory.value`` (string) para preservar API previa.
    Nuevos call sites prefieren enum directo via
    ``MageritCategory.from_resource_type``.
    """
    return MageritCategory.from_resource_type(resource_type, metadata).value


def infer_criticality(tipo_magerit: str, metadata: Optional[dict] = None) -> str:
    """Heuristicas deterministas sobre metadata (production, pii, internet-facing)."""
    level = CRITICALITY_BASE.get(tipo_magerit, "media")
    md = metadata or {}
    tags_raw = md.get("tags") or []
    tags: set[str] = set()
    if isinstance(tags_raw, list):
        tags = {str(t).lower() for t in tags_raw}
    elif isinstance(tags_raw, dict):
        for k, v in tags_raw.items():
            tags.add(str(k).lower())
            tags.add(str(v).lower())

    env = str(md.get("environment") or md.get("env") or "").lower()
    is_production = env in {"prod", "production", "prd"} or "production" in tags
    has_pii = bool(md.get("has_pii")) or "pii" in tags or "personal_data" in tags
    public_exposed = (
        bool(md.get("public")) or bool(md.get("internet_facing"))
        or "public" in tags or "internet" in tags
    )

    if is_production:
        level = _bump_criticality(level, 1)
    if has_pii and _CRIT_ORDER.index(level) < _CRIT_ORDER.index("alta"):
        level = "alta"
    if public_exposed:
        level = _bump_criticality(level, 1)

    return level


def _dto_metadata(dto: DiscoveredAssetDTO) -> dict:
    md = dict(dto.raw_data or {})
    if dto.tags:
        md.setdefault("tags", list(dto.tags))
    return md


async def persist_asset_dto(
    session: AsyncSession,
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    provider: str,
    dto: DiscoveredAssetDTO,
) -> DiscoveredAsset:
    """Normaliza un DTO crudo y lo guarda como DiscoveredAsset + nodo PKG."""
    metadata = _dto_metadata(dto)
    tipo = classify_magerit_type(dto.asset_type, metadata)
    crit = infer_criticality(tipo, metadata)

    # Nodo PKG (node_type existente "asset")
    pkg_node = await pkg.add_node(
        session, project_id,
        node_type="asset",
        label=dto.name,
        external_id=f"m22:{provider}:{dto.external_id}",
        properties={
            "tipo_magerit": tipo,
            "criticidad": crit,
            "fuente_conector": provider,
            "source": "m22_discovery",
            "raw_type": dto.asset_type,
        },
    )

    asset = DiscoveredAsset(
        project_id=project_id,
        discovery_run_id=run_id,
        fuente_conector=provider,
        tipo_magerit=tipo,
        nombre=dto.name,
        identificador=dto.external_id,
        descripcion=metadata.get("description"),
        criticidad_propuesta=crit,
        propietario_inferido=metadata.get("owner") or metadata.get("propietario"),
        ubicacion=metadata.get("region") or metadata.get("ubicacion") or metadata.get("location"),
        metadata_extra=metadata,
        pkg_node_id=pkg_node,
    )
    session.add(asset)
    await session.flush()
    return asset


async def discover_from_connector(
    session: AsyncSession,
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    provider: str,
    dtos: list[DiscoveredAssetDTO],
) -> list[DiscoveredAsset]:
    """Persiste una lista de DTOs como DiscoveredAsset normalizados."""
    out: list[DiscoveredAsset] = []
    for dto in dtos:
        asset = await persist_asset_dto(session, project_id, run_id, provider, dto)
        out.append(asset)
    return out


async def list_assets(
    session: AsyncSession,
    project_id: uuid.UUID,
    tipo_magerit: Optional[str] = None,
    criticidad: Optional[str] = None,
    fuente: Optional[str] = None,
) -> list[DiscoveredAsset]:
    stmt = select(DiscoveredAsset).where(
        DiscoveredAsset.project_id == project_id,
        DiscoveredAsset.deleted_at.is_(None),
    )
    if tipo_magerit:
        stmt = stmt.where(DiscoveredAsset.tipo_magerit == tipo_magerit)
    if criticidad:
        stmt = stmt.where(DiscoveredAsset.criticidad_propuesta == criticidad)
    if fuente:
        stmt = stmt.where(DiscoveredAsset.fuente_conector == fuente)
    r = await session.execute(stmt.order_by(DiscoveredAsset.created_at.desc()))
    return list(r.scalars().all())


async def get_asset(session: AsyncSession, asset_id: uuid.UUID) -> Optional[DiscoveredAsset]:
    r = await session.execute(
        select(DiscoveredAsset).where(
            DiscoveredAsset.id == asset_id,
            DiscoveredAsset.deleted_at.is_(None),
        )
    )
    return r.scalar_one_or_none()


async def soft_delete_asset(session: AsyncSession, asset_id: uuid.UUID) -> bool:
    asset = await get_asset(session, asset_id)
    if asset is None:
        return False
    from datetime import datetime, timezone
    asset.deleted_at = datetime.now(timezone.utc)
    await session.flush()
    return True


async def assets_summary(session: AsyncSession, project_id: uuid.UUID) -> dict:
    """Resumen agregado: counts por tipo, criticidad y fuente."""
    base_where = (
        DiscoveredAsset.project_id == project_id,
        DiscoveredAsset.deleted_at.is_(None),
    )
    total = (await session.execute(
        select(func.count(DiscoveredAsset.id)).where(*base_where)
    )).scalar_one() or 0

    by_tipo: dict[str, int] = {}
    r = await session.execute(
        select(DiscoveredAsset.tipo_magerit, func.count(DiscoveredAsset.id))
        .where(*base_where)
        .group_by(DiscoveredAsset.tipo_magerit)
    )
    for tipo, count in r.all():
        by_tipo[tipo or "unknown"] = count

    by_criticidad: dict[str, int] = {}
    r = await session.execute(
        select(DiscoveredAsset.criticidad_propuesta, func.count(DiscoveredAsset.id))
        .where(*base_where)
        .group_by(DiscoveredAsset.criticidad_propuesta)
    )
    for c, count in r.all():
        by_criticidad[c or "unknown"] = count

    by_fuente: dict[str, int] = {}
    r = await session.execute(
        select(DiscoveredAsset.fuente_conector, func.count(DiscoveredAsset.id))
        .where(*base_where)
        .group_by(DiscoveredAsset.fuente_conector)
    )
    for f, count in r.all():
        by_fuente[f or "unknown"] = count

    return {
        "total": total,
        "by_tipo_magerit": by_tipo,
        "by_criticidad": by_criticidad,
        "by_fuente": by_fuente,
    }
