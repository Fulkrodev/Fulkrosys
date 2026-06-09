"""Vulnerability Discovery Service (M22-B).

M22 NO ejecuta scanners — eso lo hace M8 Pentesting.
M22 es el IMPORTADOR: recibe JSON de OpenVAS/Nuclei/Trivy y lo normaliza
a filas de vulnerability_inventory con CVSS + mapeo ENS + MITRE.
"""
from __future__ import annotations

import re
import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.discovery import DiscoveryAlert, VulnerabilityFinding


# ========== Mapeos ==========

CVSS_SEVERITY_MAP = {
    "critical": "critica",
    "high": "alta",
    "medium": "media",
    "low": "baja",
    "info": "info",
    "informational": "info",
    "none": "info",
}

ENS_MAPPING_RULES: list[dict] = [
    {"pattern": r"ssl|tls|certificate", "medidas": ["mp.com.2", "mp.com.3"]},
    {"pattern": r"xss|injection|sqli|sql\s*injection", "medidas": ["mp.sw.1", "mp.sw.2"]},
    {"pattern": r"auth|password|credential", "medidas": ["op.acc.5", "op.acc.6"]},
    {"pattern": r"privilege|escalation", "medidas": ["op.acc.2", "op.acc.3"]},
    {"pattern": r"patch|update|outdated|obsolete", "medidas": ["op.exp.4"]},
    {"pattern": r"backup|recovery", "medidas": ["op.cont.1"]},
    {"pattern": r"log|audit|monitor", "medidas": ["op.exp.8", "op.exp.10"]},
    {"pattern": r"firewall|network|port", "medidas": ["mp.com.1", "mp.com.4"]},
    {"pattern": r"malware|virus|trojan", "medidas": ["op.exp.6"]},
    {"pattern": r"encryption|cipher|crypto", "medidas": ["mp.info.3", "mp.com.2"]},
]


class VulnImportError(ValueError):
    pass


def map_ens_measures(titulo: str, descripcion: Optional[str] = None) -> list[str]:
    text = f"{titulo or ''} {descripcion or ''}".lower()
    medidas: list[str] = []
    seen: set[str] = set()
    for rule in ENS_MAPPING_RULES:
        if re.search(rule["pattern"], text, re.IGNORECASE):
            for m in rule["medidas"]:
                if m not in seen:
                    medidas.append(m)
                    seen.add(m)
    return medidas


def _severity_from_cvss(score: Optional[float], raw_severity: Optional[str]) -> str:
    if raw_severity:
        norm = raw_severity.strip().lower()
        if norm in CVSS_SEVERITY_MAP:
            return CVSS_SEVERITY_MAP[norm]
    if score is None:
        return "info"
    if score >= 9.0:
        return "critica"
    if score >= 7.0:
        return "alta"
    if score >= 4.0:
        return "media"
    if score > 0:
        return "baja"
    return "info"


def _alert_from_finding(vf: VulnerabilityFinding) -> Optional[DiscoveryAlert]:
    if vf.cvss_severity not in {"critica", "alta"}:
        return None
    return DiscoveryAlert(
        project_id=vf.project_id,
        discovery_run_id=vf.discovery_run_id,
        modulo="vulnerabilities",
        severidad=vf.cvss_severity,
        codigo=f"VULN_{(vf.cve_id or vf.fuente).upper()}",
        titulo=vf.titulo,
        descripcion=(
            f"{vf.descripcion or vf.titulo} "
            f"(CVSS: {vf.cvss_score if vf.cvss_score is not None else 'N/A'})"
        ),
        entity_type="vulnerability_finding",
        entity_id=vf.id,
        medidas_ens_afectadas=list(vf.medidas_ens_afectadas or []),
    )


async def _persist_finding(
    session: AsyncSession,
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    fuente: str,
    data: dict,
) -> VulnerabilityFinding:
    cvss_score = data.get("cvss_score")
    if cvss_score is not None:
        try:
            cvss_score = float(cvss_score)
        except (TypeError, ValueError):
            cvss_score = None

    raw_severity = data.get("cvss_severity") or data.get("severity")
    severity = _severity_from_cvss(cvss_score, raw_severity)

    titulo = (data.get("titulo") or data.get("title") or data.get("name")
              or data.get("cve_id") or "Unnamed finding")
    descripcion = data.get("descripcion") or data.get("description")

    medidas = data.get("medidas_ens_afectadas")
    if not medidas:
        medidas = map_ens_measures(titulo, descripcion)

    vf = VulnerabilityFinding(
        project_id=project_id,
        discovery_run_id=run_id,
        fuente=fuente,
        titulo=titulo,
        descripcion=descripcion,
        cve_id=data.get("cve_id") or data.get("cve"),
        cvss_score=cvss_score,
        cvss_vector=data.get("cvss_vector"),
        cvss_severity=severity,
        asset_afectado=data.get("asset_afectado") or data.get("host") or data.get("target"),
        asset_id=data.get("asset_id"),
        es_explotable=data.get("es_explotable"),
        exploit_disponible=data.get("exploit_disponible"),
        remediacion_sugerida=data.get("remediacion_sugerida") or data.get("remediation"),
        medidas_ens_afectadas=list(medidas or []),
        mitre_tactics=list(data.get("mitre_tactics") or []),
        estado=data.get("estado", "open"),
        raw_finding=dict(data.get("raw") or data),
    )
    session.add(vf)
    await session.flush()
    return vf


async def _import_batch(
    session: AsyncSession,
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    fuente: str,
    findings: list[dict],
) -> tuple[list[VulnerabilityFinding], list[DiscoveryAlert]]:
    out: list[VulnerabilityFinding] = []
    alerts: list[DiscoveryAlert] = []
    for f in findings or []:
        vf = await _persist_finding(session, project_id, run_id, fuente, f)
        out.append(vf)
        alert = _alert_from_finding(vf)
        if alert is not None:
            session.add(alert)
            alerts.append(alert)
    await session.flush()
    return out, alerts


def _normalize_openvas(data: dict) -> dict:
    """Adapta un result de OpenVAS/Greenbone (nvt block) a formato interno."""
    nvt = data.get("nvt") or {}
    refs = nvt.get("refs", {}).get("ref") or []
    if isinstance(refs, dict):
        refs = [refs]
    cve = next(
        (r.get("id") for r in refs if isinstance(r, dict) and r.get("type") == "cve"),
        None,
    )
    return {
        "titulo": nvt.get("name") or data.get("name") or "Unnamed",
        "descripcion": data.get("description") or nvt.get("tags"),
        "cve_id": cve,
        "cvss_score": data.get("severity") or nvt.get("cvss_base"),
        "cvss_severity": data.get("threat"),
        "asset_afectado": data.get("host"),
        "raw": data,
    }


def _normalize_nuclei(line: dict) -> dict:
    info = line.get("info") or {}
    cve_refs = info.get("classification", {}).get("cve-id") or []
    if isinstance(cve_refs, list) and cve_refs:
        cve = cve_refs[0]
    elif isinstance(cve_refs, str):
        cve = cve_refs
    else:
        cve = None
    return {
        "titulo": info.get("name") or line.get("template-id") or "Nuclei finding",
        "descripcion": info.get("description"),
        "cve_id": cve,
        "cvss_score": info.get("classification", {}).get("cvss-score"),
        "cvss_severity": info.get("severity"),
        "cvss_vector": info.get("classification", {}).get("cvss-metrics"),
        "asset_afectado": line.get("matched-at") or line.get("host"),
        "raw": line,
    }


def _normalize_trivy_vuln(v: dict, target: str) -> dict:
    return {
        "titulo": v.get("Title") or v.get("VulnerabilityID") or "Trivy finding",
        "descripcion": v.get("Description"),
        "cve_id": v.get("VulnerabilityID"),
        "cvss_score": (v.get("CVSS") or {}).get("nvd", {}).get("V3Score"),
        "cvss_severity": v.get("Severity"),
        "asset_afectado": target,
        "remediacion_sugerida": v.get("FixedVersion"),
        "raw": v,
    }


# ========== Importadores publicos ==========

async def import_openvas_results(
    session: AsyncSession,
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    results: list[dict],
) -> tuple[list[VulnerabilityFinding], list[DiscoveryAlert]]:
    normalized = [_normalize_openvas(r) for r in results or []]
    return await _import_batch(session, project_id, run_id, "openvas", normalized)


async def import_nuclei_results(
    session: AsyncSession,
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    jsonl: list[dict],
) -> tuple[list[VulnerabilityFinding], list[DiscoveryAlert]]:
    normalized = [_normalize_nuclei(line) for line in jsonl or []]
    return await _import_batch(session, project_id, run_id, "nuclei", normalized)


async def import_trivy_results(
    session: AsyncSession,
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    trivy_json: dict,
) -> tuple[list[VulnerabilityFinding], list[DiscoveryAlert]]:
    normalized: list[dict] = []
    for res in (trivy_json or {}).get("Results", []) or []:
        target = res.get("Target") or ""
        for v in res.get("Vulnerabilities") or []:
            normalized.append(_normalize_trivy_vuln(v, target))
    return await _import_batch(session, project_id, run_id, "trivy", normalized)


async def import_generic(
    session: AsyncSession,
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    findings: list[dict],
    source: str,
) -> tuple[list[VulnerabilityFinding], list[DiscoveryAlert]]:
    return await _import_batch(session, project_id, run_id, source, findings or [])


# ========== Queries ==========

async def list_vulnerabilities(
    session: AsyncSession,
    project_id: uuid.UUID,
    cvss_severity: Optional[str] = None,
    fuente: Optional[str] = None,
    estado: Optional[str] = None,
) -> list[VulnerabilityFinding]:
    stmt = select(VulnerabilityFinding).where(
        VulnerabilityFinding.project_id == project_id,
        VulnerabilityFinding.deleted_at.is_(None),
    )
    if cvss_severity:
        stmt = stmt.where(VulnerabilityFinding.cvss_severity == cvss_severity)
    if fuente:
        stmt = stmt.where(VulnerabilityFinding.fuente == fuente)
    if estado:
        stmt = stmt.where(VulnerabilityFinding.estado == estado)
    r = await session.execute(stmt.order_by(VulnerabilityFinding.created_at.desc()))
    return list(r.scalars().all())


async def get_vulnerability(
    session: AsyncSession, finding_id: uuid.UUID
) -> Optional[VulnerabilityFinding]:
    r = await session.execute(
        select(VulnerabilityFinding).where(
            VulnerabilityFinding.id == finding_id,
            VulnerabilityFinding.deleted_at.is_(None),
        )
    )
    return r.scalar_one_or_none()


async def update_finding_status(
    session: AsyncSession, finding_id: uuid.UUID, estado: str,
) -> Optional[VulnerabilityFinding]:
    if estado not in {"open", "accepted", "mitigated", "false_positive"}:
        raise VulnImportError(f"estado invalido: {estado}")
    vf = await get_vulnerability(session, finding_id)
    if vf is None:
        return None
    vf.estado = estado
    await session.flush()
    return vf


async def vulnerabilities_summary(session: AsyncSession, project_id: uuid.UUID) -> dict:
    base = (
        VulnerabilityFinding.project_id == project_id,
        VulnerabilityFinding.deleted_at.is_(None),
    )
    total = (await session.execute(
        select(func.count(VulnerabilityFinding.id)).where(*base)
    )).scalar_one() or 0

    by_sev: dict[str, int] = {}
    r = await session.execute(
        select(
            VulnerabilityFinding.cvss_severity, func.count(VulnerabilityFinding.id)
        )
        .where(*base)
        .group_by(VulnerabilityFinding.cvss_severity)
    )
    for s, c in r.all():
        by_sev[s or "unknown"] = c

    by_fuente: dict[str, int] = {}
    r = await session.execute(
        select(VulnerabilityFinding.fuente, func.count(VulnerabilityFinding.id))
        .where(*base)
        .group_by(VulnerabilityFinding.fuente)
    )
    for f, c in r.all():
        by_fuente[f or "unknown"] = c

    by_estado: dict[str, int] = {}
    r = await session.execute(
        select(VulnerabilityFinding.estado, func.count(VulnerabilityFinding.id))
        .where(*base)
        .group_by(VulnerabilityFinding.estado)
    )
    for e, c in r.all():
        by_estado[e or "open"] = c

    top_cves: list[dict] = []
    r = await session.execute(
        select(
            VulnerabilityFinding.cve_id, func.count(VulnerabilityFinding.id)
        )
        .where(*base, VulnerabilityFinding.cve_id.isnot(None))
        .group_by(VulnerabilityFinding.cve_id)
        .order_by(func.count(VulnerabilityFinding.id).desc())
        .limit(5)
    )
    for cve, c in r.all():
        top_cves.append({"cve_id": cve, "count": c})

    return {
        "total": total,
        "by_severity": by_sev,
        "by_fuente": by_fuente,
        "by_estado": by_estado,
        "top_cves": top_cves,
    }
