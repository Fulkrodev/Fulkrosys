"""SIEM service · agregación de eventos de seguridad + correlación determinista.

Pure functional · raw SQL · ON-QUERY (ADR-025 · sin tablas nuevas). El caller
fija el contexto (admin cross-cliente → rol fulkro · o project-scoped). R1: las
reglas de correlación son deterministas, sin LLM en la decisión.
"""
from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from typing import Optional

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

# ── Severidad normalizada (unifica ES/EN · OLA note: incidents mezclan idioma) ──
SEVERITY_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}

_SEVERITY_ALIASES = {
    "critica": "critical", "crítica": "critical", "critico": "critical",
    "crítico": "critical", "alta": "high", "alto": "high", "media": "medium",
    "medio": "medium", "baja": "low", "bajo": "low", "informativa": "info",
}


def normalize_severity(raw: Optional[str]) -> str:
    s = (raw or "").strip().lower()
    s = _SEVERITY_ALIASES.get(s, s)
    return s if s in SEVERITY_RANK else "medium"


# ── Modelo normalizado de evento de seguridad ───────────────────────────
@dataclass
class SecurityEvent:
    source: str          # pentest | incident | escalation | compliance
    event_type: str
    severity: str        # critical|high|medium|low|info (normalizada)
    occurred_at: Optional[str]
    project_id: Optional[str]
    title: str
    ref_id: Optional[str]
    resolved: bool = False
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SiemCorrelation:
    rule_id: str
    severity: str
    title: str
    description: str
    event_count: int
    project_id: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


def _pid_clause(project_id: Optional[uuid.UUID], col: str = "project_id") -> str:
    return f" AND {col} = :pid " if project_id else ""


async def aggregate_security_events(
    db: AsyncSession,
    *,
    project_id: Optional[uuid.UUID] = None,
    limit: int = 200,
) -> list[SecurityEvent]:
    """Une los eventos de seguridad de las 4 fuentes · normaliza · ordena desc."""
    params: dict = {"lim": limit}
    if project_id:
        params["pid"] = str(project_id)
    events: list[SecurityEvent] = []

    # 1) Pentest / vuln-scan (M8 · foco principal)
    rows = (await db.execute(sa_text(
        "SELECT id, project_id, title, severity, status, created_at, cve_id, "
        "zfp_gate5_classification, affected_host "
        "FROM verification_findings "
        "WHERE deleted_at IS NULL" + _pid_clause(project_id) +
        " ORDER BY created_at DESC LIMIT :lim"
    ), params)).mappings().all()
    for r in rows:
        events.append(SecurityEvent(
            source="pentest",
            event_type=f"finding.{r['zfp_gate5_classification'] or 'open'}",
            severity=normalize_severity(r["severity"]),
            occurred_at=r["created_at"].isoformat() if r["created_at"] else None,
            project_id=str(r["project_id"]) if r["project_id"] else None,
            title=r["title"],
            ref_id=str(r["id"]),
            resolved=r["status"] in {"remediated", "false_positive", "accepted_risk"},
            details={"cve_id": r["cve_id"], "host": r["affected_host"],
                     "status": r["status"]},
        ))

    # 2) Incidentes (M19 · CCN-STIC 817)
    rows = (await db.execute(sa_text(
        "SELECT id, project_id, descripcion, severidad, fecha, workflow_state, "
        "notificado_lucia "
        "FROM incidents WHERE deleted_at IS NULL" + _pid_clause(project_id) +
        " ORDER BY fecha DESC LIMIT :lim"
    ), params)).mappings().all()
    for r in rows:
        events.append(SecurityEvent(
            source="incident",
            event_type=f"incident.{r['workflow_state'] or 'created'}",
            severity=normalize_severity(r["severidad"]),
            occurred_at=r["fecha"].isoformat() if r["fecha"] else None,
            project_id=str(r["project_id"]) if r["project_id"] else None,
            title=(r["descripcion"] or "Incidente de seguridad")[:200],
            ref_id=str(r["id"]),
            resolved=r["workflow_state"] in {"closed", "resolved", "resuelto"},
            details={"notificado_lucia": r["notificado_lucia"],
                     "workflow_state": r["workflow_state"]},
        ))

    # 3) Escalados (M18) · severidad alta por defecto (son escalados)
    rows = (await db.execute(sa_text(
        "SELECT id, project_id, trigger, descripcion, canal, resuelto, created_at "
        "FROM escalation_events WHERE deleted_at IS NULL" + _pid_clause(project_id) +
        " ORDER BY created_at DESC LIMIT :lim"
    ), params)).mappings().all()
    for r in rows:
        sev = "high" if r["canal"] in {"email_urgente", "reunion_urgente"} else "medium"
        events.append(SecurityEvent(
            source="escalation",
            event_type=f"escalation.{r['trigger']}",
            severity=sev,
            occurred_at=r["created_at"].isoformat() if r["created_at"] else None,
            project_id=str(r["project_id"]) if r["project_id"] else None,
            title=(r["descripcion"] or r["trigger"])[:200],
            ref_id=str(r["id"]),
            resolved=bool(r["resuelto"]),
            details={"trigger": r["trigger"], "canal": r["canal"]},
        ))

    # 4) Alertas de cumplimiento (m_compliance_monitor) · sin project_id (FULKRO self)
    if not project_id:
        rows = (await db.execute(sa_text(
            "SELECT id, check_name, severity, status, message, triggered_at, "
            "resolved_at FROM compliance_alerts "
            "ORDER BY triggered_at DESC LIMIT :lim"
        ), params)).mappings().all()
        for r in rows:
            events.append(SecurityEvent(
                source="compliance",
                event_type=f"compliance.{r['check_name']}",
                severity=normalize_severity(r["severity"]),
                occurred_at=(
                    r["triggered_at"].isoformat() if r["triggered_at"] else None
                ),
                project_id=None,
                title=(r["message"] or r["check_name"])[:200],
                ref_id=str(r["id"]),
                resolved=r["resolved_at"] is not None,
                details={"check_name": r["check_name"], "status": r["status"]},
            ))

    # Orden global por severidad desc, luego recencia desc
    events.sort(
        key=lambda e: (
            SEVERITY_RANK.get(e.severity, 0),
            e.occurred_at or "",
        ),
        reverse=True,
    )
    return events[:limit]


def compute_correlations(events: list[SecurityEvent]) -> list[SiemCorrelation]:
    """Reglas de correlación DETERMINISTAS (R1). Operan sobre los eventos
    agregados (sin estado externo · puras · testables)."""
    correlations: list[SiemCorrelation] = []

    # Solo eventos NO resueltos cuentan para superficie de riesgo activa.
    active = [e for e in events if not e.resolved]

    # R1 · ≥3 hallazgos de pentest críticos/altos sin resolver.
    crit_findings = [
        e for e in active
        if e.source == "pentest" and e.severity in {"critical", "high"}
    ]
    if len(crit_findings) >= 3:
        correlations.append(SiemCorrelation(
            rule_id="multiple_critical_pentest_findings",
            severity="critical",
            title="Múltiples hallazgos críticos de pentest sin resolver",
            description=(
                f"{len(crit_findings)} hallazgos de pentest críticos/altos abiertos "
                "· prioriza remediación (mp.s.2 / op.exp.* · ENS)."
            ),
            event_count=len(crit_findings),
        ))

    # R2 · incidente abierto + vuln crítica en el MISMO proyecto.
    by_proj: dict[str, set] = {}
    for e in active:
        if e.project_id:
            by_proj.setdefault(e.project_id, set()).add(e.source)
    for pid in by_proj:
        # Precisión (fix verify N-siem): exige vuln pentest crítica/alta REAL +
        # incidente activo en el mismo proyecto · event_count = solo las vulns
        # pentest críticas (coherente con la narrativa de la regla).
        crit_vulns = [
            e for e in active
            if e.project_id == pid and e.source == "pentest"
            and e.severity in {"critical", "high"}
        ]
        has_active_incident = any(
            e.project_id == pid and e.source == "incident" for e in active
        )
        if crit_vulns and has_active_incident:
            correlations.append(SiemCorrelation(
                rule_id="incident_plus_critical_vuln",
                severity="critical",
                title="Superficie crítica: incidente + vulnerabilidad activa",
                description=(
                    f"Incidente abierto + {len(crit_vulns)} vulnerabilidad(es) "
                    "crítica(s)/alta(s) de pentest en el mismo proyecto · "
                    "correlación de superficie de ataque."
                ),
                event_count=len(crit_vulns),
                project_id=pid,
            ))

    # R3 · incidente no notificado a LUCIA (plazo Art.33 en riesgo).
    unnotified = [
        e for e in active
        if e.source == "incident"
        and e.severity in {"critical", "high"}
        and not e.details.get("notificado_lucia")
    ]
    if unnotified:
        correlations.append(SiemCorrelation(
            rule_id="incident_not_notified_lucia",
            severity="high",
            title="Incidente grave sin notificar a CCN-CERT/LUCIA (Art.33)",
            description=(
                f"{len(unnotified)} incidente(s) grave(s) sin notificación CCN-CERT/"
                "LUCIA · revisa el plazo legal Art.33 (24/72h)."
            ),
            event_count=len(unnotified),
        ))

    correlations.sort(
        key=lambda c: SEVERITY_RANK.get(c.severity, 0), reverse=True,
    )
    return correlations


# Tope de barrido para correlaciones (independiente del limit de display) ·
# así las vulns críticas no se pierden tras una racha de eventos low recientes
# (fix verify N-siem · R1/R2 false-negatives).
CORRELATION_SCAN_CAP = 2000


async def security_event_counts(
    db: AsyncSession, *, project_id: Optional[uuid.UUID] = None,
) -> dict:
    """Conteos EXACTOS por severidad/fuente + total + activos · COUNT GROUP BY
    independiente del limit de display (fix verify N-siem · los tiles no mienten
    con volumen alto). Normaliza severidad ES/EN en Python."""
    params: dict = {}
    if project_id:
        params["pid"] = str(project_id)
    by_severity = {k: 0 for k in SEVERITY_RANK}
    by_source: dict[str, int] = {}
    total = 0
    active = 0

    def _acc(source: str, sev: str, resolved: bool, n: int) -> None:
        nonlocal total, active
        s = normalize_severity(sev)
        by_severity[s] = by_severity.get(s, 0) + n
        by_source[source] = by_source.get(source, 0) + n
        total += n
        if not resolved:
            active += n

    # 1) pentest
    for r in (await db.execute(sa_text(
        "SELECT severity, (status IN ('remediated','false_positive',"
        "'accepted_risk')) AS resolved, count(*) AS n FROM verification_findings "
        "WHERE deleted_at IS NULL" + _pid_clause(project_id) +
        " GROUP BY severity, resolved"
    ), params)).mappings().all():
        _acc("pentest", r["severity"], bool(r["resolved"]), int(r["n"]))

    # 2) incidentes
    for r in (await db.execute(sa_text(
        "SELECT severidad, (workflow_state IN ('closed','resolved','resuelto')) "
        "AS resolved, count(*) AS n FROM incidents WHERE deleted_at IS NULL"
        + _pid_clause(project_id) + " GROUP BY severidad, resolved"
    ), params)).mappings().all():
        _acc("incident", r["severidad"], bool(r["resolved"]), int(r["n"]))

    # 3) escalados (severidad derivada del canal)
    for r in (await db.execute(sa_text(
        "SELECT canal, resuelto, count(*) AS n FROM escalation_events "
        "WHERE deleted_at IS NULL" + _pid_clause(project_id) +
        " GROUP BY canal, resuelto"
    ), params)).mappings().all():
        sev = "high" if r["canal"] in {"email_urgente", "reunion_urgente"} else "medium"
        _acc("escalation", sev, bool(r["resuelto"]), int(r["n"]))

    # 4) compliance (platform-global · solo en vista cross-cliente)
    if not project_id:
        for r in (await db.execute(sa_text(
            "SELECT severity, (resolved_at IS NOT NULL) AS resolved, "
            "count(*) AS n FROM compliance_alerts GROUP BY severity, resolved"
        ))).mappings().all():
            _acc("compliance", r["severity"], bool(r["resolved"]), int(r["n"]))

    return {
        "total_events": total,
        "active_events": active,
        "by_severity": by_severity,
        "by_source": by_source,
    }


async def siem_overview(
    db: AsyncSession,
    *,
    project_id: Optional[uuid.UUID] = None,
    limit: int = 100,
) -> dict:
    """Resumen SIEM: conteos EXACTOS (COUNT GROUP BY · no truncados) +
    correlaciones (barrido amplio) + muestra de eventos recientes (limit).
    op.mon.2 (sistema de métricas)."""
    counts = await security_event_counts(db, project_id=project_id)
    # Barrido amplio para correlaciones (no acoplado al limit de display).
    scanned = await aggregate_security_events(
        db, project_id=project_id, limit=CORRELATION_SCAN_CAP,
    )
    correlations = compute_correlations(scanned)
    displayed = scanned[:limit]

    return {
        "total_events": counts["total_events"],
        "active_events": counts["active_events"],
        "by_severity": counts["by_severity"],
        "by_source": counts["by_source"],
        "correlations": [c.to_dict() for c in correlations],
        "correlation_count": len(correlations),
        "events": [e.to_dict() for e in displayed],
    }
