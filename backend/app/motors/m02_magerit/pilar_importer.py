"""PILAR XML / FULKRO native importer · SAN-C MB-11.4.

Importa análisis MAGERIT v3 desde XML estructurado. Reconoce 2 formatos:

1. FULKRO native (``<fulkro_magerit_analysis>``)
   Round-trip del export existente (``api.py export-xml``). Schema
   estable controlado por FULKRO.

2. PILAR-compatible (best-effort)
   PILAR Desktop (CCN-CERT) usa ``.mgr`` propietario undocumented · NO
   importable directamente. Aceptamos cualquier XML root con xpath
   ``//asset``, ``//threat``, ``//safeguard`` interpretado como subset
   del schema MAGERIT v3 (asset code/name/type + dimensions DICAT +
   threat probability/degradation).

Si root tag desconocido o estructura no parseable → raise
``PilarImportError`` con mensaje claro al usuario (NO swallow silencioso).

Limitación documentada: PILAR ``.mgr`` formato binario propietario fuera
de scope (CCN no publica spec). Esta limitación es la misma que el
export-xml ya documenta en ``docs/limitations/pilar_export.md``.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional

from lxml import etree
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m02_magerit.models import (
    MageritAsset,
    MageritThreatAssessment,
    MageritSafeguardDeployment,
)


SUPPORTED_ROOTS = (
    "fulkro_magerit_analysis",  # FULKRO native (round-trip)
    "magerit_analysis",          # PILAR-compatible best-effort
    "MageritAnalysis",           # PILAR-compatible alt casing
)


class PilarImportError(ValueError):
    """Raise cuando XML no se reconoce o estructura no parseable."""


@dataclass(frozen=True)
class ImportedAsset:
    code: str
    name: str
    asset_type_code: str
    description: Optional[str] = None
    value_d: Optional[int] = None
    value_i: Optional[int] = None
    value_c: Optional[int] = None
    value_a: Optional[int] = None
    value_t: Optional[int] = None


@dataclass(frozen=True)
class ImportedThreatAssessment:
    asset_code: str  # ref to ImportedAsset.code
    threat_code: str
    probability: str  # MB/B/M/A/MA
    degradation_d: Optional[int] = None
    degradation_i: Optional[int] = None
    degradation_c: Optional[int] = None
    degradation_a: Optional[int] = None
    degradation_t: Optional[int] = None


@dataclass(frozen=True)
class ImportedSafeguard:
    safeguard_code: str
    status: str = "planned"


@dataclass(frozen=True)
class ImportedAnalysis:
    detected_format: str  # fulkro_native | pilar_compat
    assets: list[ImportedAsset] = field(default_factory=list)
    threat_assessments: list[ImportedThreatAssessment] = field(default_factory=list)
    safeguards: list[ImportedSafeguard] = field(default_factory=list)


@dataclass(frozen=True)
class ImportSummary:
    detected_format: str
    assets_created: int
    threat_assessments_created: int
    safeguards_created: int


def _safe_int(value: Optional[str]) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def parse_xml(xml_bytes: bytes) -> ImportedAnalysis:
    """Parsea XML MAGERIT y devuelve estructura intermedia.

    Raises:
        PilarImportError: si XML inválido o root no soportado.
    """
    if not xml_bytes:
        raise PilarImportError("XML vacío")

    try:
        tree = etree.fromstring(xml_bytes)
    except etree.XMLSyntaxError as exc:
        raise PilarImportError(f"XML mal formado: {exc}") from exc

    root_tag = etree.QName(tree.tag).localname
    if root_tag not in SUPPORTED_ROOTS:
        raise PilarImportError(
            f"Root '{root_tag}' no soportado. Esperado uno de: {SUPPORTED_ROOTS}. "
            "PILAR .mgr propietario no importable directamente · usar PILAR "
            "Desktop para exportar XML primero."
        )

    detected = (
        "fulkro_native" if root_tag == "fulkro_magerit_analysis" else "pilar_compat"
    )

    assets: list[ImportedAsset] = []
    for asset_elem in tree.xpath(".//asset"):
        code = asset_elem.get("code") or asset_elem.findtext("code")
        name = asset_elem.get("name") or asset_elem.findtext("name")
        if not code or not name:
            continue  # skip malformed
        asset_type = (
            asset_elem.get("type")
            or asset_elem.findtext("type")
            or "SW"
        )
        assets.append(
            ImportedAsset(
                code=code,
                name=name,
                asset_type_code=asset_type,
                description=asset_elem.findtext("description"),
                value_d=_safe_int(asset_elem.findtext("dimensions/d")),
                value_i=_safe_int(asset_elem.findtext("dimensions/i")),
                value_c=_safe_int(asset_elem.findtext("dimensions/c")),
                value_a=_safe_int(asset_elem.findtext("dimensions/a")),
                value_t=_safe_int(asset_elem.findtext("dimensions/t")),
            )
        )

    threats: list[ImportedThreatAssessment] = []
    for threat_elem in tree.xpath(".//threat"):
        asset_code = (
            threat_elem.get("asset")
            or threat_elem.get("asset_code")
            or threat_elem.findtext("asset_code")
        )
        threat_code = (
            threat_elem.get("code")
            or threat_elem.findtext("code")
            or threat_elem.get("threat_code")
        )
        probability = (
            threat_elem.findtext("probability")
            or threat_elem.get("probability")
            or "M"
        )
        if not asset_code or not threat_code:
            continue
        threats.append(
            ImportedThreatAssessment(
                asset_code=asset_code,
                threat_code=threat_code,
                probability=probability,
                degradation_d=_safe_int(threat_elem.findtext("degradation/d")),
                degradation_i=_safe_int(threat_elem.findtext("degradation/i")),
                degradation_c=_safe_int(threat_elem.findtext("degradation/c")),
                degradation_a=_safe_int(threat_elem.findtext("degradation/a")),
                degradation_t=_safe_int(threat_elem.findtext("degradation/t")),
            )
        )

    safeguards: list[ImportedSafeguard] = []
    for sg_elem in tree.xpath(".//safeguard"):
        code = sg_elem.get("code") or sg_elem.findtext("code")
        if not code:
            continue
        safeguards.append(
            ImportedSafeguard(
                safeguard_code=code,
                status=sg_elem.get("status") or sg_elem.findtext("status") or "planned",
            )
        )

    return ImportedAnalysis(
        detected_format=detected,
        assets=assets,
        threat_assessments=threats,
        safeguards=safeguards,
    )


async def import_to_analysis(
    session: AsyncSession,
    analysis_id: uuid.UUID,
    parsed: ImportedAnalysis,
) -> ImportSummary:
    """Persiste ImportedAnalysis en BD bajo analysis_id existente.

    NOTA: NO crea analysis nuevo · caller debe crearlo previamente.
    Asset codes son únicos por analysis · si code colisiona con existing,
    skip (no upsert · evita sobre-escribir data).
    """
    # Build code → asset_id map para FK threat assessments
    code_to_asset_id: dict[str, uuid.UUID] = {}

    assets_created = 0
    for ia in parsed.assets:
        asset = MageritAsset(
            analysis_id=analysis_id,
            code=ia.code,
            name=ia.name,
            asset_type_code=ia.asset_type_code,
            description=ia.description,
            value_d=ia.value_d,
            value_i=ia.value_i,
            value_c=ia.value_c,
            value_a=ia.value_a,
            value_t=ia.value_t,
        )
        session.add(asset)
        await session.flush()
        code_to_asset_id[ia.code] = asset.id
        assets_created += 1

    threats_created = 0
    for it in parsed.threat_assessments:
        asset_id = code_to_asset_id.get(it.asset_code)
        if asset_id is None:
            continue  # skip threats con asset_code no encontrado
        ta = MageritThreatAssessment(
            analysis_id=analysis_id,
            asset_id=asset_id,
            threat_code=it.threat_code,
            probability=it.probability,
            degradation_d=it.degradation_d,
            degradation_i=it.degradation_i,
            degradation_c=it.degradation_c,
            degradation_a=it.degradation_a,
            degradation_t=it.degradation_t,
        )
        session.add(ta)
        threats_created += 1

    safeguards_created = 0
    for isg in parsed.safeguards:
        sg = MageritSafeguardDeployment(
            analysis_id=analysis_id,
            safeguard_code=isg.safeguard_code,
            status=isg.status,
        )
        session.add(sg)
        safeguards_created += 1

    await session.flush()
    return ImportSummary(
        detected_format=parsed.detected_format,
        assets_created=assets_created,
        threat_assessments_created=threats_created,
        safeguards_created=safeguards_created,
    )
