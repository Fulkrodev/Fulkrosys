"""M8 v5.1 - Delta report vs run anterior (spec §7.1).

Compara dos listas de findings y produce la estructura:

    {
      "new":              [finding_hash, ...],
      "resolved":         [finding_hash, ...],
      "persistent":       [finding_hash, ...],
      "severity_changes": [{finding_hash, from_sev, to_sev}, ...],
      "overall_trend":    "mejorando" | "estable" | "empeorando",
    }

Trend se calcula comparando el peso agregado de severity (critical=4,
high=3, medium=2, low=1):

- mejorando: peso_curr < peso_prev * 0.8
- empeorando: peso_curr > peso_prev * 1.2
- estable: entre los dos umbrales
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


SEV_WEIGHT = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}


@dataclass(frozen=True)
class SeverityChange:
    finding_hash: str
    title: str
    from_sev: str
    to_sev: str

    def to_dict(self) -> dict:
        return {
            "finding_hash": self.finding_hash,
            "title": self.title,
            "from_sev": self.from_sev,
            "to_sev": self.to_sev,
        }


@dataclass(frozen=True)
class DeltaReport:
    new: list[dict]
    resolved: list[dict]
    persistent: list[dict]
    severity_changes: list[SeverityChange]
    overall_trend: str
    weight_previous: int
    weight_current: int

    def to_dict(self) -> dict:
        return {
            "new": self.new,
            "resolved": self.resolved,
            "persistent": self.persistent,
            "severity_changes": [c.to_dict() for c in self.severity_changes],
            "overall_trend": self.overall_trend,
            "weight_previous": self.weight_previous,
            "weight_current": self.weight_current,
            "totals": {
                "new": len(self.new),
                "resolved": len(self.resolved),
                "persistent": len(self.persistent),
                "severity_changes": len(self.severity_changes),
            },
        }


def _index_by_hash(findings: Iterable) -> dict[str, dict]:
    """Indexa findings por finding_hash (tolera dicts o modelos)."""
    out: dict[str, dict] = {}
    for f in findings:
        if isinstance(f, dict):
            h = f.get("finding_hash")
            sev = f.get("severity", "info")
            title = f.get("title", "")
        else:
            h = getattr(f, "finding_hash", None)
            sev = getattr(f, "severity", "info")
            title = getattr(f, "title", "")
        if not h:
            continue
        out[h] = {"finding_hash": h, "severity": sev, "title": title}
    return out


def _weight(findings_by_hash: dict[str, dict]) -> int:
    return sum(
        SEV_WEIGHT.get((f.get("severity") or "info").lower(), 0)
        for f in findings_by_hash.values()
    )


def compute_delta(
    previous: Iterable, current: Iterable,
) -> DeltaReport:
    """Calcula delta entre dos colecciones de findings.

    Cualquiera de las dos acepta modelos SQLAlchemy VerificationFinding
    o dicts con las claves 'finding_hash' + 'severity' + 'title'.
    """
    prev_idx = _index_by_hash(previous)
    curr_idx = _index_by_hash(current)

    new_hashes = set(curr_idx) - set(prev_idx)
    resolved_hashes = set(prev_idx) - set(curr_idx)
    persistent_hashes = set(prev_idx) & set(curr_idx)

    sev_changes: list[SeverityChange] = []
    for h in persistent_hashes:
        p_sev = (prev_idx[h]["severity"] or "info").lower()
        c_sev = (curr_idx[h]["severity"] or "info").lower()
        if p_sev != c_sev:
            sev_changes.append(SeverityChange(
                finding_hash=h,
                title=curr_idx[h]["title"],
                from_sev=p_sev,
                to_sev=c_sev,
            ))

    w_prev = _weight(prev_idx)
    w_curr = _weight(curr_idx)

    if w_prev == 0 and w_curr == 0:
        trend = "estable"
    elif w_prev == 0:
        trend = "empeorando" if w_curr > 0 else "estable"
    elif w_curr < w_prev * 0.8:
        trend = "mejorando"
    elif w_curr > w_prev * 1.2:
        trend = "empeorando"
    else:
        trend = "estable"

    return DeltaReport(
        new=[curr_idx[h] for h in sorted(new_hashes)],
        resolved=[prev_idx[h] for h in sorted(resolved_hashes)],
        persistent=[curr_idx[h] for h in sorted(persistent_hashes)],
        severity_changes=sev_changes,
        overall_trend=trend,
        weight_previous=w_prev,
        weight_current=w_curr,
    )


def persist_delta_to_run(run, delta: DeltaReport) -> None:
    """Copia los totales del delta al VerificationRun (columns delta_*)."""
    run.delta_new = len(delta.new)
    run.delta_resolved = len(delta.resolved)
    run.delta_persistent = len(delta.persistent)
