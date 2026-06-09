"""M22 Paso 6 — Seccion 3.2 del E-090 (Diagnostico Tecnico).

Construye el diccionario que alimenta el template DOCX del E-090 con
los datos de discovery tecnico. Se integra en el E-090 global despues
de la seccion organizacional (3.1) que produce M21.

Incluye:
- Inventario de activos por tipo MAGERIT
- Estado de identidades (MFA %, inactivas, privilegiadas)
- Estado de proteccion de datos (cifrado, sensibles)
- Estado de configuraciones (score por familia ENS)
- Vulnerabilidades detectadas por severidad
- Madurez tecnica L0-L5

La funcion `build_technical_section` NO usa LLM — es deterministica
y trazable (la auditora puede reproducir los calculos).
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.discovery import (
    DataFlowDiagram, DiscoveredConfiguration, DiscoveredDataStore,
    DiscoveryAlert, VulnerabilityFinding,
)
from backend.app.models.onboarding import DiscoveredAsset, DiscoveredIdentity

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# Madurez tecnica L0-L5 (CMMI-like)
# ════════════════════════════════════════════════════════════════════
#
# L0 = No existe
# L1 = Inicial-gestionada (procesos ad-hoc, dependientes de personas)
# L2 = Repetible (procesos definidos localmente)
# L3 = Definida (procesos documentados y estandarizados)
# L4 = Gestionada cuantitativamente (metricas, objetivos)
# L5 = Optimizada (mejora continua automatica)
#
# Calculo: score 0-100 a partir de % MFA, % cifrado, % logging, %
# backups, ratio vulns criticas abiertas -> mapeo a nivel.

LEVEL_THRESHOLDS = [
    (0, "L0"),
    (15, "L1"),
    (35, "L2"),
    (55, "L3"),
    (75, "L4"),
    (90, "L5"),
]


def compute_maturity_level(score_pct: float) -> str:
    """Mapea score 0-100 a nivel L0-L5."""
    last = "L0"
    for threshold, level in LEVEL_THRESHOLDS:
        if score_pct >= threshold:
            last = level
    return last


# ════════════════════════════════════════════════════════════════════
# Queries agregados
# ════════════════════════════════════════════════════════════════════

async def _assets_summary(
    db: AsyncSession, project_id: uuid.UUID,
) -> dict[str, Any]:
    base = (
        DiscoveredAsset.project_id == project_id,
        DiscoveredAsset.deleted_at.is_(None),
    )
    total = (await db.execute(
        select(func.count(DiscoveredAsset.id)).where(*base)
    )).scalar_one() or 0

    by_tipo: dict[str, int] = {}
    r = await db.execute(
        select(DiscoveredAsset.tipo_magerit, func.count(DiscoveredAsset.id))
        .where(*base).group_by(DiscoveredAsset.tipo_magerit)
    )
    for tipo, count in r.all():
        by_tipo[tipo or "unknown"] = count

    by_ubicacion: dict[str, int] = {}
    r = await db.execute(
        select(DiscoveredAsset.ubicacion, func.count(DiscoveredAsset.id))
        .where(*base).group_by(DiscoveredAsset.ubicacion)
    )
    for ubi, count in r.all():
        by_ubicacion[ubi or "unknown"] = count

    by_fuente: dict[str, int] = {}
    r = await db.execute(
        select(DiscoveredAsset.fuente_conector, func.count(DiscoveredAsset.id))
        .where(*base).group_by(DiscoveredAsset.fuente_conector)
    )
    for f, count in r.all():
        by_fuente[f or "unknown"] = count

    return {
        "total": total,
        "por_tipo_magerit": by_tipo,
        "por_ubicacion": by_ubicacion,
        "por_fuente": by_fuente,
    }


async def _identities_summary(
    db: AsyncSession, project_id: uuid.UUID,
) -> dict[str, Any]:
    base = (
        DiscoveredIdentity.project_id == project_id,
        DiscoveredIdentity.deleted_at.is_(None),
    )
    total = (await db.execute(
        select(func.count(DiscoveredIdentity.id)).where(*base)
    )).scalar_one() or 0
    privilegiadas = (await db.execute(
        select(func.count(DiscoveredIdentity.id)).where(
            *base, DiscoveredIdentity.es_privilegiada.is_(True),
        )
    )).scalar_one() or 0
    inactivas_90 = (await db.execute(
        select(func.count(DiscoveredIdentity.id)).where(
            *base, DiscoveredIdentity.dias_inactiva > 90,
        )
    )).scalar_one() or 0

    mfa_eval = (await db.execute(
        select(func.count(DiscoveredIdentity.id)).where(
            *base, DiscoveredIdentity.mfa_activo.isnot(None),
        )
    )).scalar_one() or 0
    mfa_ok = (await db.execute(
        select(func.count(DiscoveredIdentity.id)).where(
            *base, DiscoveredIdentity.mfa_activo.is_(True),
        )
    )).scalar_one() or 0
    mfa_pct = round(100.0 * mfa_ok / mfa_eval, 1) if mfa_eval else 0.0

    return {
        "total": total,
        "privilegiadas": privilegiadas,
        "inactivas_90d": inactivas_90,
        "mfa_coverage_pct": mfa_pct,
        "mfa_ok": mfa_ok,
        "mfa_evaluadas": mfa_eval,
    }


async def _data_stores_summary(
    db: AsyncSession, project_id: uuid.UUID,
) -> dict[str, Any]:
    base = (
        DiscoveredDataStore.project_id == project_id,
        DiscoveredDataStore.deleted_at.is_(None),
    )
    total = (await db.execute(
        select(func.count(DiscoveredDataStore.id)).where(*base)
    )).scalar_one() or 0
    personales = (await db.execute(
        select(func.count(DiscoveredDataStore.id)).where(
            *base, DiscoveredDataStore.tiene_datos_personales.is_(True),
        )
    )).scalar_one() or 0
    cifrado_eval = (await db.execute(
        select(func.count(DiscoveredDataStore.id)).where(
            *base, DiscoveredDataStore.cifrado_en_reposo.isnot(None),
        )
    )).scalar_one() or 0
    cifrado_ok = (await db.execute(
        select(func.count(DiscoveredDataStore.id)).where(
            *base, DiscoveredDataStore.cifrado_en_reposo.is_(True),
        )
    )).scalar_one() or 0
    cifrado_pct = (
        round(100.0 * cifrado_ok / cifrado_eval, 1) if cifrado_eval else 0.0
    )

    return {
        "total": total,
        "con_datos_personales": personales,
        "cifrado_at_rest_pct": cifrado_pct,
        "cifrado_ok": cifrado_ok,
        "cifrado_evaluado": cifrado_eval,
    }


ENS_FAMILIES = {
    "op.acc": "Control de acceso",
    "op.exp": "Explotacion",
    "op.ext": "Servicios externos",
    "op.cont": "Continuidad",
    "mp.info": "Proteccion informacion",
    "mp.com": "Proteccion comunicaciones",
    "mp.sw": "Proteccion aplicaciones",
    "mp.s": "Proteccion servicios",
    "org": "Organizacion",
}


async def _configurations_summary(
    db: AsyncSession, project_id: uuid.UUID,
) -> dict[str, Any]:
    base = (
        DiscoveredConfiguration.project_id == project_id,
        DiscoveredConfiguration.deleted_at.is_(None),
    )
    total = (await db.execute(
        select(func.count(DiscoveredConfiguration.id)).where(*base)
    )).scalar_one() or 0
    ok = (await db.execute(
        select(func.count(DiscoveredConfiguration.id)).where(
            *base, DiscoveredConfiguration.estado == "ok",
        )
    )).scalar_one() or 0

    # Agregacion por familia ENS
    r = await db.execute(
        select(DiscoveredConfiguration).where(*base)
    )
    configs = list(r.scalars().all())
    fam_totals: dict[str, dict[str, int]] = {
        k: {"total": 0, "ok": 0, "gap": 0} for k in ENS_FAMILIES
    }
    fam_totals.setdefault("otros", {"total": 0, "ok": 0, "gap": 0})
    for cfg in configs:
        families_touched: set[str] = set()
        for m in cfg.medidas_ens_afectadas or []:
            if not isinstance(m, str):
                continue
            fam_prefix = None
            for prefix in ENS_FAMILIES:
                if m.startswith(prefix):
                    fam_prefix = prefix
                    break
            families_touched.add(fam_prefix or "otros")
        if not families_touched:
            families_touched.add("otros")
        for fam in families_touched:
            fam_totals[fam]["total"] += 1
            if cfg.estado == "ok":
                fam_totals[fam]["ok"] += 1
            else:
                fam_totals[fam]["gap"] += 1

    by_family = {}
    for fam, counts in fam_totals.items():
        if counts["total"] == 0:
            continue
        pct = round(100.0 * counts["ok"] / counts["total"], 1)
        by_family[fam] = {
            **counts,
            "pct_ok": pct,
            "nombre": ENS_FAMILIES.get(fam, "Otros"),
        }

    by_severidad: dict[str, int] = {}
    for cfg in configs:
        key = cfg.gap_severidad or "info"
        by_severidad[key] = by_severidad.get(key, 0) + 1

    return {
        "total_checks": total,
        "ok": ok,
        "gaps": total - ok,
        "por_familia_ens": by_family,
        "por_severidad_gap": by_severidad,
        "ok_pct": round(100.0 * ok / total, 1) if total else 0.0,
    }


async def _vulnerabilities_summary(
    db: AsyncSession, project_id: uuid.UUID,
) -> dict[str, Any]:
    base = (
        VulnerabilityFinding.project_id == project_id,
        VulnerabilityFinding.deleted_at.is_(None),
        VulnerabilityFinding.estado == "open",
    )
    total = (await db.execute(
        select(func.count(VulnerabilityFinding.id)).where(*base)
    )).scalar_one() or 0
    by_sev: dict[str, int] = {}
    r = await db.execute(
        select(VulnerabilityFinding.cvss_severity, func.count(VulnerabilityFinding.id))
        .where(*base).group_by(VulnerabilityFinding.cvss_severity)
    )
    for s, c in r.all():
        by_sev[s or "info"] = c
    return {
        "total_abiertas": total,
        "por_severidad": by_sev,
        "critica": by_sev.get("critica", 0),
        "alta": by_sev.get("alta", 0),
        "media": by_sev.get("media", 0),
    }


async def _data_flows_summary(
    db: AsyncSession, project_id: uuid.UUID,
) -> dict[str, Any]:
    r = await db.execute(
        select(DataFlowDiagram).where(
            DataFlowDiagram.project_id == project_id,
            DataFlowDiagram.deleted_at.is_(None),
        )
    )
    dfds = list(r.scalars().all())
    critical = sum(
        1 for d in dfds
        if d.clasificacion_max_datos in {"confidencial", "reservada"}
    )
    total_observaciones = sum(
        len(d.observaciones_seguridad or []) for d in dfds
    )
    return {
        "total_dfds": len(dfds),
        "dfds_criticos": critical,
        "observaciones_seguridad": total_observaciones,
        "por_tipo": {
            d.tipo: (0) for d in dfds
        } | {
            d.tipo: sum(1 for x in dfds if x.tipo == d.tipo) for d in dfds
        },
    }


# ════════════════════════════════════════════════════════════════════
# Calculo madurez tecnica
# ════════════════════════════════════════════════════════════════════

def compute_technical_maturity(
    identities: dict[str, Any],
    data_stores: dict[str, Any],
    configurations: dict[str, Any],
    vulns: dict[str, Any],
) -> dict[str, Any]:
    """Score 0-100 ponderado + nivel L0-L5 + drivers."""
    mfa = identities.get("mfa_coverage_pct", 0.0)
    cif = data_stores.get("cifrado_at_rest_pct", 0.0)
    ok_pct = configurations.get("ok_pct", 0.0)
    # Penalizacion por vulns criticas abiertas (cap -30)
    crit = vulns.get("critica", 0)
    alt = vulns.get("alta", 0)
    penalty = min(30, crit * 5 + alt * 2)

    # Ponderacion: MFA 30%, cifrado 25%, configs ok 35%, penalty vulns
    score = (mfa * 0.30) + (cif * 0.25) + (ok_pct * 0.35) - penalty
    score = max(0.0, min(100.0, round(score, 1)))
    level = compute_maturity_level(score)
    return {
        "score_pct": score,
        "nivel": level,
        "drivers": {
            "mfa_coverage": mfa,
            "encryption_at_rest": cif,
            "configs_ok_pct": ok_pct,
            "vulns_penalty": penalty,
            "vulns_criticas": crit,
            "vulns_altas": alt,
        },
    }


# ════════════════════════════════════════════════════════════════════
# Public builder
# ════════════════════════════════════════════════════════════════════

async def build_technical_section(
    db: AsyncSession,
    project_id: uuid.UUID,
    *,
    ens_category: str = "MEDIA",
) -> dict[str, Any]:
    """Construye el dict Seccion 3.2 E-090 Tecnica."""
    assets = await _assets_summary(db, project_id)
    identities = await _identities_summary(db, project_id)
    data_stores = await _data_stores_summary(db, project_id)
    configurations = await _configurations_summary(db, project_id)
    vulns = await _vulnerabilities_summary(db, project_id)
    flows = await _data_flows_summary(db, project_id)
    maturity = compute_technical_maturity(
        identities, data_stores, configurations, vulns,
    )

    # Alertas agregadas del modulo configurations
    alerts_r = await db.execute(
        select(DiscoveryAlert.severidad, func.count(DiscoveryAlert.id))
        .where(
            DiscoveryAlert.project_id == project_id,
            DiscoveryAlert.modulo.in_(
                ["configurations", "identities", "vulnerabilities"]
            ),
        )
        .group_by(DiscoveryAlert.severidad)
    )
    alerts_by_sev = {sev or "info": c for sev, c in alerts_r.all()}

    top_gaps: list[dict[str, Any]] = []
    r = await db.execute(
        select(DiscoveredConfiguration).where(
            DiscoveredConfiguration.project_id == project_id,
            DiscoveredConfiguration.deleted_at.is_(None),
            DiscoveredConfiguration.gap_severidad.in_(["alta", "critica"]),
        ).order_by(DiscoveredConfiguration.gap_severidad.desc()).limit(10)
    )
    for cfg in r.scalars().all():
        top_gaps.append({
            "control_id": cfg.control_id,
            "sistema": cfg.sistema,
            "severidad": cfg.gap_severidad,
            "actual": cfg.valor_actual,
            "esperado": cfg.valor_esperado,
            "medidas_ens": list(cfg.medidas_ens_afectadas or []),
        })

    return {
        "ens_category": ens_category,
        "inventario_activos": assets,
        "estado_identidades": identities,
        "proteccion_datos": data_stores,
        "estado_configuraciones": configurations,
        "vulnerabilidades": vulns,
        "data_flows": flows,
        "madurez_tecnica": maturity,
        "alertas_paso6": {
            "por_severidad": alerts_by_sev,
            "total": sum(alerts_by_sev.values()),
        },
        "top_gaps": top_gaps,
    }


def merge_with_organizational(
    technical: dict[str, Any],
    organizational: dict[str, Any],
) -> dict[str, Any]:
    """Combina seccion 3.1 (M21) + 3.2 (M22) en el contexto E-090 global."""
    merged = dict(organizational or {})
    merged["seccion_32_tecnica"] = technical
    # Quick wins combinados: los de M21 + los top_gaps de M22
    qw = list(merged.get("quick_wins") or [])
    for gap in technical.get("top_gaps", [])[:3]:
        qw.append({
            "titulo": f"Cerrar gap {gap['control_id']} ({gap['severidad']})",
            "descripcion": (
                f"Sistema: {gap['sistema']} — actual: {gap['actual']}, "
                f"esperado: {gap['esperado']}"
            ),
            "esfuerzo": "medio" if gap["severidad"] == "alta" else "alto",
        })
    merged["quick_wins"] = qw
    # Recomendaciones Fase 2 extendidas con madurez
    recs = list(merged.get("recomendaciones_fase2") or [])
    nivel = technical.get("madurez_tecnica", {}).get("nivel", "L1")
    if nivel in {"L0", "L1"}:
        recs.append(
            f"Madurez tecnica actual {nivel}: priorizar quick-wins de MFA "
            "y cifrado antes de Analisis de Riesgos completo."
        )
    merged["recomendaciones_fase2"] = recs
    return merged


__all__ = [
    "compute_maturity_level",
    "compute_technical_maturity",
    "build_technical_section",
    "merge_with_organizational",
]
