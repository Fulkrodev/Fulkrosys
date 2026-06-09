"""M8 v5.1 — Calculo de SLA por severidad (spec §5.4).

SLA por severity:
- critical: 48 horas
- high    : 7 dias
- medium  : 30 dias
- low     : 90 dias
- info    : 180 dias (no bloquea auditoria, solo info)

``deadline`` siempre se calcula a partir de ``finding.created_at``
(o del timestamp explicito que pase el llamante).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional


SLA_HOURS: dict[str, int] = {
    "critical": 48,
    "high":     7 * 24,
    "medium":   30 * 24,
    "low":      90 * 24,
    "info":     180 * 24,
}


@dataclass(frozen=True)
class SlaDeadline:
    severity: str
    calculated_from: datetime
    deadline: datetime
    hours_total: int
    hours_remaining: float
    overdue: bool

    def to_dict(self) -> dict:
        return {
            "severity": self.severity,
            "calculated_from": self.calculated_from.isoformat(),
            "deadline": self.deadline.isoformat(),
            "hours_total": self.hours_total,
            "hours_remaining": round(self.hours_remaining, 2),
            "overdue": self.overdue,
        }


def calculate_deadline(
    severity: str,
    calculated_from: datetime,
    *,
    now: Optional[datetime] = None,
) -> SlaDeadline:
    """Calcula deadline absoluto para un finding.

    ``calculated_from`` debe ser timezone-aware (UTC). Si no lo es, se
    asume UTC.
    """
    severity_norm = (severity or "info").lower()
    hours = SLA_HOURS.get(severity_norm, SLA_HOURS["info"])
    if calculated_from.tzinfo is None:
        calculated_from = calculated_from.replace(tzinfo=timezone.utc)
    deadline = calculated_from + timedelta(hours=hours)
    reference = now or datetime.now(timezone.utc)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    remaining = (deadline - reference).total_seconds() / 3600.0
    return SlaDeadline(
        severity=severity_norm,
        calculated_from=calculated_from,
        deadline=deadline,
        hours_total=hours,
        hours_remaining=remaining,
        overdue=remaining < 0,
    )


def prioritize_findings(findings: list) -> list:
    """Ordena findings por (severity desc, effort asc).

    Recibe cualquier iterable con atributos ``severity`` y
    ``remediation_effort`` (o dict con las mismas claves). Devuelve lista
    ordenada apta para generar el plan de remediacion (quick wins primero
    dentro de cada severidad).
    """
    sev_rank = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
    effort_rank = {"quick_win": 0, "short_term": 1, "long_term": 2}

    def _get(f, key: str, default=""):
        if isinstance(f, dict):
            return f.get(key, default)
        return getattr(f, key, default)

    def key(f):
        sev = (_get(f, "severity", "info") or "info").lower()
        eff = (_get(f, "remediation_effort", "") or "").lower()
        return (-sev_rank.get(sev, 0), effort_rank.get(eff, 99))

    return sorted(findings, key=key)
