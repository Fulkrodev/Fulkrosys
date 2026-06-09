"""M22 Paso 6 — Vulnerability Inventory wrapper (read-only, alimenta M8 v5.1).

M22 NO ataca ni ejecuta scanners: importa hallazgos ya existentes y los
mantiene como contexto inicial para M8 Pentesting (Fase 1 Diagnostico).

Fuentes Paso 6:
- AWS Security Hub findings (ASFF schema)
- M365 Defender alerts (security/alerts_v2)
- Nuclei JSON lines (templates ejecutados externamente)

Salida: filas en `vulnerability_inventory` con origen=m22_paso6,
marcadas como contexto inicial (estado='open', origen_m22=True).

`feed_m8_initial_context` devuelve el subset que M8 debe consumir en
su fase 1 (lectura, sin priorizacion).
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.discovery import DiscoveryAlert, VulnerabilityFinding
from backend.app.motors.m22_discovery import vuln_discovery as legacy

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# Normalizadores Paso 6
# ════════════════════════════════════════════════════════════════════

def _normalize_security_hub(finding: dict) -> dict:
    """ASFF → formato interno VulnerabilityFinding."""
    resources = finding.get("Resources", []) or []
    resource = resources[0] if resources else {}
    cvss = finding.get("Severity", {}) or {}
    score = cvss.get("Normalized") or cvss.get("Score")
    severity_label = (cvss.get("Label") or finding.get("Severity", {}).get("Label") or "").lower()
    types = finding.get("Types", []) or []
    compliance = (finding.get("Compliance") or {}).get("Status")
    # Solo importamos findings con Compliance=FAILED o Severity >= MEDIUM
    return {
        "titulo": finding.get("Title") or finding.get("Id") or "Security Hub finding",
        "descripcion": finding.get("Description"),
        "cve_id": None,
        "cvss_score": float(score) if score is not None else None,
        "cvss_severity": severity_label or None,
        "asset_afectado": resource.get("Id") or resource.get("ResourceRole"),
        "remediacion_sugerida": (finding.get("Remediation") or {})
            .get("Recommendation", {}).get("Text"),
        "mitre_tactics": [
            t for t in types if isinstance(t, str) and "/" in t
        ],
        "raw": {
            "Id": finding.get("Id"),
            "ProductArn": finding.get("ProductArn"),
            "Types": types,
            "Compliance": compliance,
        },
    }


def _normalize_m365_defender(alert: dict) -> dict:
    """M365 Defender alert_v2 → formato interno.

    Preserva el nombre ingles de severity ('high', 'medium', ...) para que
    el normalizador legacy `_severity_from_cvss` lo mapee a alta/media/baja.
    """
    evidence = alert.get("evidence", []) or []
    target = None
    for e in evidence:
        if e.get("@odata.type") == "#microsoft.graph.security.userEvidence":
            target = (e.get("userAccount") or {}).get("userPrincipalName")
            break
        if e.get("@odata.type") == "#microsoft.graph.security.deviceEvidence":
            target = (e.get("mdeDeviceId") or e.get("deviceDnsName"))
            break
    return {
        "titulo": alert.get("title") or "M365 Defender alert",
        "descripcion": alert.get("description"),
        "cvss_severity": (alert.get("severity") or "medium").lower(),
        "asset_afectado": target,
        "mitre_tactics": list(alert.get("mitreTechniques") or []),
        "raw": {
            "id": alert.get("id"),
            "category": alert.get("category"),
            "status": alert.get("status"),
        },
    }


# ════════════════════════════════════════════════════════════════════
# Importadores (persisten en vulnerability_inventory)
# ════════════════════════════════════════════════════════════════════

async def import_security_hub(
    db: AsyncSession,
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    findings: list[dict],
) -> tuple[list[VulnerabilityFinding], list[DiscoveryAlert]]:
    out: list[VulnerabilityFinding] = []
    alerts: list[DiscoveryAlert] = []
    for f in findings or []:
        normalized = _normalize_security_hub(f)
        normalized["raw"]["origen_m22_paso6"] = True
        vf = await _persist_with_origin(
            db, project_id, run_id, "aws_security_hub", normalized,
        )
        out.append(vf)
        alert = legacy._alert_from_finding(vf)
        if alert is not None:
            db.add(alert)
            alerts.append(alert)
    await db.flush()
    return out, alerts


async def import_m365_defender(
    db: AsyncSession,
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    alerts_v2: list[dict],
) -> tuple[list[VulnerabilityFinding], list[DiscoveryAlert]]:
    out: list[VulnerabilityFinding] = []
    alerts: list[DiscoveryAlert] = []
    for a in alerts_v2 or []:
        normalized = _normalize_m365_defender(a)
        normalized["raw"]["origen_m22_paso6"] = True
        vf = await _persist_with_origin(
            db, project_id, run_id, "m365_defender", normalized,
        )
        out.append(vf)
        alert = legacy._alert_from_finding(vf)
        if alert is not None:
            db.add(alert)
            alerts.append(alert)
    await db.flush()
    return out, alerts


async def import_nuclei(
    db: AsyncSession,
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    jsonl: list[dict],
) -> tuple[list[VulnerabilityFinding], list[DiscoveryAlert]]:
    normalized = [legacy._normalize_nuclei(line) for line in jsonl or []]
    for n in normalized:
        n.setdefault("raw", {})["origen_m22_paso6"] = True
    out: list[VulnerabilityFinding] = []
    alerts: list[DiscoveryAlert] = []
    for n in normalized:
        vf = await _persist_with_origin(
            db, project_id, run_id, "nuclei", n,
        )
        out.append(vf)
        alert = legacy._alert_from_finding(vf)
        if alert is not None:
            db.add(alert)
            alerts.append(alert)
    await db.flush()
    return out, alerts


async def _persist_with_origin(
    db: AsyncSession,
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    fuente: str,
    data: dict,
) -> VulnerabilityFinding:
    """Variante local de legacy._persist_finding que fuerza origen Paso 6."""
    raw = dict(data.get("raw") or {})
    raw.setdefault("origen_m22_paso6", True)
    data = {**data, "raw": raw}
    return await legacy._persist_finding(db, project_id, run_id, fuente, data)


# ════════════════════════════════════════════════════════════════════
# Feed a M8 Pentesting (Fase 1 Diagnostico)
# ════════════════════════════════════════════════════════════════════

async def feed_m8_initial_context(
    db: AsyncSession,
    project_id: uuid.UUID,
) -> dict[str, Any]:
    """Devuelve el inventario de vulns existente que M8 usa como contexto.

    M8 v5.1 lo consume en `_read_initial_context_from_m22` al iniciar un
    verification_run. No modifica nada aqui, solo empaqueta.
    """
    r = await db.execute(
        select(VulnerabilityFinding).where(
            VulnerabilityFinding.project_id == project_id,
            VulnerabilityFinding.deleted_at.is_(None),
            VulnerabilityFinding.estado == "open",
        ).order_by(VulnerabilityFinding.descubierto_at.desc())
    )
    findings = list(r.scalars().all())

    summary: dict[str, Any] = {
        "total": len(findings),
        "by_severidad": {},
        "by_fuente": {},
        "por_asset": {},
        "top_10": [],
    }
    _SEV_ORDER = {"critica": 0, "alta": 1, "media": 2, "baja": 3, "info": 4}
    for vf in findings:
        sev = vf.cvss_severity or "info"
        summary["by_severidad"][sev] = summary["by_severidad"].get(sev, 0) + 1
        summary["by_fuente"][vf.fuente] = summary["by_fuente"].get(vf.fuente, 0) + 1
        key = vf.asset_afectado or "unknown"
        summary["por_asset"][key] = summary["por_asset"].get(key, 0) + 1
    # Top 10 por severidad + cvss_score desc
    ordered = sorted(
        findings,
        key=lambda v: (
            _SEV_ORDER.get(v.cvss_severity or "info", 5),
            -(v.cvss_score or 0.0),
        ),
    )
    for vf in ordered[:10]:
        summary["top_10"].append({
            "id": str(vf.id),
            "titulo": vf.titulo,
            "severidad": vf.cvss_severity,
            "score": vf.cvss_score,
            "asset": vf.asset_afectado,
            "fuente": vf.fuente,
            "cve_id": vf.cve_id,
        })
    summary["m8_ready"] = len(findings) > 0
    return summary


# ════════════════════════════════════════════════════════════════════
# Orquestador Paso 6 (un solo call)
# ════════════════════════════════════════════════════════════════════

async def run_paso6_import(
    db: AsyncSession,
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    *,
    security_hub_findings: Optional[list[dict]] = None,
    m365_defender_alerts: Optional[list[dict]] = None,
    nuclei_results: Optional[list[dict]] = None,
) -> dict[str, Any]:
    totals = {"aws_security_hub": 0, "m365_defender": 0, "nuclei": 0}
    alerts_total = 0
    if security_hub_findings:
        vs, al = await import_security_hub(
            db, project_id, run_id, security_hub_findings,
        )
        totals["aws_security_hub"] = len(vs)
        alerts_total += len(al)
    if m365_defender_alerts:
        vs, al = await import_m365_defender(
            db, project_id, run_id, m365_defender_alerts,
        )
        totals["m365_defender"] = len(vs)
        alerts_total += len(al)
    if nuclei_results:
        vs, al = await import_nuclei(
            db, project_id, run_id, nuclei_results,
        )
        totals["nuclei"] = len(vs)
        alerts_total += len(al)
    context = await feed_m8_initial_context(db, project_id)
    return {
        "by_source": totals,
        "alerts_generated": alerts_total,
        "m8_context": context,
    }


__all__ = [
    "import_security_hub",
    "import_m365_defender",
    "import_nuclei",
    "feed_m8_initial_context",
    "run_paso6_import",
]
