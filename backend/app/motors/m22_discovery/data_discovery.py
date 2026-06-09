"""Data Discovery Service (M22-B).

Descubre data stores desde connectors y los clasifica por patrones
regex (DNI, NIF, IBAN, tarjetas, datos salud). Output: discovered_data_stores
con clasificacion de sensibilidad + alertas para datos criticos sin cifrado.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Awaitable, Callable, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.discovery import DiscoveredDataStore, DiscoveryAlert
from backend.app.motors.m16_onboarding import pkg_service as pkg


# ========== Patrones de sensibilidad ==========

_DNI_RE = re.compile(r"\b\d{8}[A-Z]\b|\b[XYZ]\d{7}[A-Z]\b")
# Para evitar solapar con DNI puro (9 caracteres), NIF es "letra+7 digitos+letra" (CIF moderno)
_NIF_CIF_RE = re.compile(r"\b[ABCDEFGHJNPQRSUVW]\d{7}[0-9A-J]\b")
_IBAN_ES_RE = re.compile(r"\bES\d{22}\b")
# Tarjeta: 16 digitos que empiezan por 4 / 51-55 / 34-37 / 6011 (permitir grupos opcionales)
_CC_RE = re.compile(r"\b(?:4\d{3}|5[1-5]\d{2}|3[47]\d{2}|6011)[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b")
_NSS_RE = re.compile(r"\b\d{2}/\d{8,10}/\d{2}\b")
_PHONE_ES_RE = re.compile(r"(?:\+34|0034)?\s?[6789]\d{8}\b")
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_SALUD_RE = re.compile(
    r"\b(?:diagn[oó]stico|patolog[ií]a|historia\s+cl[ií]nica|medicaci[oó]n|alergia|CIE-10|SNOMED)\b",
    re.IGNORECASE,
)


SENSITIVITY_PATTERNS: list[dict] = [
    {
        "tipo": "DATOS_SALUD",
        "regex": _SALUD_RE,
        "clasificacion": "reservada",
        "es_datos_personales": True,
        "es_datos_salud": True,
    },
    {
        "tipo": "TARJETA_CREDITO",
        "regex": _CC_RE,
        "clasificacion": "reservada",
        "es_datos_personales": True,
        "es_datos_financieros": True,
    },
    {
        "tipo": "IBAN_ES",
        "regex": _IBAN_ES_RE,
        "clasificacion": "confidencial",
        "es_datos_personales": True,
        "es_datos_financieros": True,
    },
    {
        "tipo": "DNI_NIE",
        "regex": _DNI_RE,
        "clasificacion": "confidencial",
        "es_datos_personales": True,
    },
    {
        "tipo": "NSS",
        "regex": _NSS_RE,
        "clasificacion": "confidencial",
        "es_datos_personales": True,
    },
    {
        "tipo": "NIF_CIF",
        "regex": _NIF_CIF_RE,
        "clasificacion": "interna",
        "es_datos_personales": False,
    },
    {
        "tipo": "TELEFONO_ES",
        "regex": _PHONE_ES_RE,
        "clasificacion": "interna",
        "es_datos_personales": True,
    },
    {
        "tipo": "EMAIL",
        "regex": _EMAIL_RE,
        "clasificacion": "interna",
        "es_datos_personales": True,
    },
]

_CLASSIF_ORDER = ["sin_clasificar", "publica", "interna", "confidencial", "reservada"]


def _max_classification(a: str, b: str) -> str:
    try:
        return _CLASSIF_ORDER[
            max(_CLASSIF_ORDER.index(a), _CLASSIF_ORDER.index(b))
        ]
    except ValueError:
        return b


def analyze_sensitivity(metadata_text: str) -> tuple[str, list[dict], dict]:
    """Analiza texto y devuelve (clasificacion, patrones, flags)."""
    flags = {
        "tiene_datos_personales": False,
        "tiene_datos_salud": False,
        "tiene_datos_financieros": False,
    }
    patrones: list[dict] = []
    clasificacion = "sin_clasificar"
    if not metadata_text:
        return clasificacion, patrones, flags

    for p in SENSITIVITY_PATTERNS:
        matches = p["regex"].findall(metadata_text)
        count = len(matches)
        if count == 0:
            continue
        patrones.append({"tipo": p["tipo"], "count_estimado": count})
        clasificacion = _max_classification(clasificacion, p["clasificacion"])
        if p.get("es_datos_personales"):
            flags["tiene_datos_personales"] = True
        if p.get("es_datos_salud"):
            flags["tiene_datos_salud"] = True
        if p.get("es_datos_financieros"):
            flags["tiene_datos_financieros"] = True
    return clasificacion, patrones, flags


# ========== Discovery fetcher (inyectable para tests) ==========

# Fetcher signature: async (provider: str, config: dict) -> list[dict]
# Cada dict puede tener: nombre, tipo, ubicacion, metadata, cifrado_en_reposo,
# cifrado_en_transito, control_acceso, tiene_backup, volumen_estimado_gb,
# sample_text (para analyze_sensitivity)
DataStoreFetcher = Callable[[str, dict], Awaitable[list[dict]]]


async def _noop_fetcher(provider: str, config: dict) -> list[dict]:
    return []


async def _persist_store(
    session: AsyncSession,
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    provider: str,
    raw: dict,
) -> DiscoveredDataStore:
    sample_text = " ".join(
        str(raw.get(k) or "") for k in ("sample_text", "description", "metadata_text")
    )
    if not sample_text.strip():
        sample_text = " ".join(
            str(v) for v in (raw.get("metadata") or {}).values() if isinstance(v, str)
        )
    clasif, patrones, flags = analyze_sensitivity(sample_text)

    pkg_node = await pkg.add_node(
        session, project_id,
        node_type="information",
        label=raw.get("nombre") or raw.get("name") or "data_store",
        external_id=f"m22:datastore:{provider}:{raw.get('id') or raw.get('nombre') or uuid.uuid4().hex}",
        properties={
            "tipo": raw.get("tipo") or "cloud_storage",
            "clasificacion": clasif,
            "fuente": provider,
            "source": "m22_discovery",
        },
    )

    store = DiscoveredDataStore(
        project_id=project_id,
        discovery_run_id=run_id,
        fuente_conector=provider,
        tipo=raw.get("tipo") or "cloud_storage",
        nombre=raw.get("nombre") or raw.get("name") or "unknown",
        ubicacion=raw.get("ubicacion") or raw.get("location") or "unknown",
        volumen_estimado_gb=raw.get("volumen_estimado_gb") or raw.get("size_gb"),
        clasificacion_inicial=clasif,
        patrones_detectados=patrones,
        tiene_datos_personales=flags["tiene_datos_personales"],
        tiene_datos_salud=flags["tiene_datos_salud"],
        tiene_datos_financieros=flags["tiene_datos_financieros"],
        cifrado_en_reposo=raw.get("cifrado_en_reposo"),
        cifrado_en_transito=raw.get("cifrado_en_transito"),
        control_acceso=raw.get("control_acceso"),
        tiene_backup=raw.get("tiene_backup"),
        metadata_extra=dict(raw.get("metadata") or {}),
        pkg_node_id=pkg_node,
    )
    session.add(store)
    await session.flush()
    return store


def _alert_from_store(store: DiscoveredDataStore) -> Optional[DiscoveryAlert]:
    # Alerta cuando clasificacion reservada/confidencial y cifrado en reposo no activo
    if store.clasificacion_inicial not in {"reservada", "confidencial"}:
        return None
    if store.cifrado_en_reposo is True:
        return None  # Ya cifrado, sin alerta
    sev = "critica" if store.clasificacion_inicial == "reservada" else "alta"
    codigo = "DATA_RESERVADA_SIN_CIFRADO" if sev == "critica" else "DATA_CONFIDENCIAL_SIN_CIFRADO"
    return DiscoveryAlert(
        project_id=store.project_id,
        discovery_run_id=store.discovery_run_id,
        modulo="data",
        severidad=sev,
        codigo=codigo,
        titulo=(
            f"Datos {store.clasificacion_inicial} sin cifrado en reposo en "
            f"{store.nombre}"
        ),
        descripcion=(
            f"El almacen '{store.nombre}' ({store.ubicacion}) contiene datos "
            f"clasificados como {store.clasificacion_inicial} y no tiene cifrado "
            f"en reposo confirmado. Patrones: "
            f"{', '.join(p['tipo'] for p in (store.patrones_detectados or []))}."
        ),
        entity_type="discovered_data_store",
        entity_id=store.id,
        medidas_ens_afectadas=["mp.info.3", "mp.si.2"],
    )


async def discover_all_data_stores(
    session: AsyncSession,
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    connector_sources: dict,
    fetcher: Optional[DataStoreFetcher] = None,
) -> tuple[list[DiscoveredDataStore], list[DiscoveryAlert]]:
    fetcher = fetcher or _noop_fetcher
    stores: list[DiscoveredDataStore] = []
    alerts: list[DiscoveryAlert] = []
    for provider, cfg in (connector_sources or {}).items():
        raw_items = await fetcher(provider, cfg or {})
        for raw in raw_items:
            store = await _persist_store(session, project_id, run_id, provider, raw)
            stores.append(store)
            alert = _alert_from_store(store)
            if alert is not None:
                session.add(alert)
                alerts.append(alert)
    await session.flush()
    return stores, alerts


async def list_data_stores(
    session: AsyncSession,
    project_id: uuid.UUID,
    clasificacion: Optional[str] = None,
    tiene_datos_personales: Optional[bool] = None,
) -> list[DiscoveredDataStore]:
    stmt = select(DiscoveredDataStore).where(
        DiscoveredDataStore.project_id == project_id,
        DiscoveredDataStore.deleted_at.is_(None),
    )
    if clasificacion:
        stmt = stmt.where(DiscoveredDataStore.clasificacion_inicial == clasificacion)
    if tiene_datos_personales is not None:
        stmt = stmt.where(
            DiscoveredDataStore.tiene_datos_personales.is_(tiene_datos_personales)
        )
    r = await session.execute(stmt.order_by(DiscoveredDataStore.created_at.desc()))
    return list(r.scalars().all())


async def get_data_store(
    session: AsyncSession, store_id: uuid.UUID
) -> Optional[DiscoveredDataStore]:
    r = await session.execute(
        select(DiscoveredDataStore).where(
            DiscoveredDataStore.id == store_id,
            DiscoveredDataStore.deleted_at.is_(None),
        )
    )
    return r.scalar_one_or_none()


async def soft_delete_data_store(session: AsyncSession, store_id: uuid.UUID) -> bool:
    store = await get_data_store(session, store_id)
    if store is None:
        return False
    store.deleted_at = datetime.now(timezone.utc)
    await session.flush()
    return True


async def data_summary(session: AsyncSession, project_id: uuid.UUID) -> dict:
    base = (
        DiscoveredDataStore.project_id == project_id,
        DiscoveredDataStore.deleted_at.is_(None),
    )
    total = (await session.execute(
        select(func.count(DiscoveredDataStore.id)).where(*base)
    )).scalar_one() or 0

    by_clasif: dict[str, int] = {}
    r = await session.execute(
        select(
            DiscoveredDataStore.clasificacion_inicial,
            func.count(DiscoveredDataStore.id),
        )
        .where(*base)
        .group_by(DiscoveredDataStore.clasificacion_inicial)
    )
    for c, count in r.all():
        by_clasif[c or "sin_clasificar"] = count

    con_personales = (await session.execute(
        select(func.count(DiscoveredDataStore.id)).where(
            *base, DiscoveredDataStore.tiene_datos_personales.is_(True)
        )
    )).scalar_one() or 0

    con_salud = (await session.execute(
        select(func.count(DiscoveredDataStore.id)).where(
            *base, DiscoveredDataStore.tiene_datos_salud.is_(True)
        )
    )).scalar_one() or 0

    con_financieros = (await session.execute(
        select(func.count(DiscoveredDataStore.id)).where(
            *base, DiscoveredDataStore.tiene_datos_financieros.is_(True)
        )
    )).scalar_one() or 0

    volumen_total = (await session.execute(
        select(func.sum(DiscoveredDataStore.volumen_estimado_gb)).where(*base)
    )).scalar_one() or 0

    return {
        "total": total,
        "by_clasificacion": by_clasif,
        "con_datos_personales": con_personales,
        "con_datos_salud": con_salud,
        "con_datos_financieros": con_financieros,
        "volumen_total_gb": float(volumen_total or 0),
    }
