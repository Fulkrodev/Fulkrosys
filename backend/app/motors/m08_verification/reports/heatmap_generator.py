"""M8 v5.1 - Heatmap de cobertura ENS Anexo II (spec §7.2).

73 celdas (marco organizativo + operacional + proteccion) coloreadas
segun el peor resultado de los findings que mapean a esa medida:

- ``compliant``     (verde):  ningun finding abierto
- ``partial``       (amarillo): findings de severity <= medium, sin critical/high
- ``non_compliant`` (rojo):   algun finding critical o high abierto
- ``not_verified``  (gris):   medida no cubierta por el run (ni compliant ni con finding)

El orden de las medidas se toma del registry ENS (Anexo II, RD 311/2022)
— 73 medidas cuando se expande con los refuerzos basicos. Para mantener
independencia del registry, pasamos la lista explicita.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


CELL_STATUS = {"compliant", "partial", "non_compliant", "not_verified"}


ENS_73_MEASURES: list[str] = [
    # Marco organizativo (4)
    "org.1", "org.2", "org.3", "org.4",
    # op.pl (5)
    "op.pl.1", "op.pl.2", "op.pl.3", "op.pl.4", "op.pl.5",
    # op.acc (6)
    "op.acc.1", "op.acc.2", "op.acc.3", "op.acc.4", "op.acc.5", "op.acc.6",
    # op.exp (11)
    "op.exp.1", "op.exp.2", "op.exp.3", "op.exp.4", "op.exp.5",
    "op.exp.6", "op.exp.7", "op.exp.8", "op.exp.9", "op.exp.10", "op.exp.11",
    # op.ext (4)
    "op.ext.1", "op.ext.2", "op.ext.3", "op.ext.4",
    # op.nub (2)
    "op.nub.1", "op.nub.2",
    # op.cont (4)
    "op.cont.1", "op.cont.2", "op.cont.3", "op.cont.4",
    # op.mon (3)
    "op.mon.1", "op.mon.2", "op.mon.3",
    # mp.if (7)
    "mp.if.1", "mp.if.2", "mp.if.3", "mp.if.4", "mp.if.5", "mp.if.6", "mp.if.7",
    # mp.per (4)
    "mp.per.1", "mp.per.2", "mp.per.3", "mp.per.4",
    # mp.eq (4)
    "mp.eq.1", "mp.eq.2", "mp.eq.3", "mp.eq.4",
    # mp.com (4)
    "mp.com.1", "mp.com.2", "mp.com.3", "mp.com.4",
    # mp.si (5)
    "mp.si.1", "mp.si.2", "mp.si.3", "mp.si.4", "mp.si.5",
    # mp.sw (2)
    "mp.sw.1", "mp.sw.2",
    # mp.info (6)
    "mp.info.1", "mp.info.2", "mp.info.3", "mp.info.4", "mp.info.5", "mp.info.6",
    # mp.s (2)
    "mp.s.1", "mp.s.2",
]  # Total: 4+5+6+11+4+2+4+3+7+4+4+4+5+2+6+2 = 73


@dataclass(frozen=True)
class HeatmapCell:
    measure: str
    status: str               # compliant | partial | non_compliant | not_verified
    color: str                # verde | amarillo | rojo | gris
    findings_count: int
    worst_severity: str | None
    findings_hashes: list[str]

    def to_dict(self) -> dict:
        return {
            "measure": self.measure,
            "status": self.status,
            "color": self.color,
            "findings_count": self.findings_count,
            "worst_severity": self.worst_severity,
            "findings_hashes": list(self.findings_hashes),
        }


COLOR_BY_STATUS = {
    "compliant":     "verde",
    "partial":       "amarillo",
    "non_compliant": "rojo",
    "not_verified":  "gris",
}


def _iter_findings(findings: Iterable):
    for f in findings:
        if isinstance(f, dict):
            yield f
        else:
            yield {
                "finding_hash": getattr(f, "finding_hash", None),
                "severity": getattr(f, "severity", "info"),
                "status": getattr(f, "status", "open"),
                "ens_measures": getattr(f, "ens_measures", []) or [],
                "ens_primary_measure": getattr(f, "ens_primary_measure", None),
            }


def _measures_of(f: dict) -> set[str]:
    measures = set()
    for m in f.get("ens_measures") or []:
        if isinstance(m, dict) and m.get("measure"):
            measures.add(m["measure"])
        elif isinstance(m, str):
            measures.add(m)
    if f.get("ens_primary_measure"):
        measures.add(f["ens_primary_measure"])
    return measures


def generate_heatmap(
    findings: Iterable,
    *,
    measures: list[str] | None = None,
    applicable_measures: set[str] | None = None,
) -> list[HeatmapCell]:
    """Produce las celdas del heatmap.

    ``applicable_measures`` (opcional) es el set de medidas aplicables
    al sistema segun la categoria ENS. Las medidas fuera de ese set
    quedan como ``not_verified`` aunque no tengan findings — pero se
    siguen listando en el heatmap. Si no se pasa, se asume que todas
    son aplicables.
    """
    all_measures = measures or ENS_73_MEASURES
    applicable = applicable_measures or set(all_measures)

    by_measure: dict[str, list[dict]] = {}
    for f in _iter_findings(findings):
        if (f.get("status") or "open") not in ("open", "needs_review"):
            # remediated / accepted_risk / false_positive no afectan heatmap
            continue
        for m in _measures_of(f):
            by_measure.setdefault(m, []).append(f)

    sev_rank = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
    cells: list[HeatmapCell] = []
    for m in all_measures:
        lst = by_measure.get(m, [])
        if not lst:
            status = "compliant" if m in applicable else "not_verified"
            cells.append(HeatmapCell(
                measure=m, status=status,
                color=COLOR_BY_STATUS[status],
                findings_count=0, worst_severity=None, findings_hashes=[],
            ))
            continue
        worst = max(
            lst, key=lambda f: sev_rank.get((f.get("severity") or "info").lower(), 0),
        )
        worst_sev = (worst.get("severity") or "info").lower()
        if worst_sev in ("critical", "high"):
            status = "non_compliant"
        else:
            status = "partial"
        cells.append(HeatmapCell(
            measure=m, status=status,
            color=COLOR_BY_STATUS[status],
            findings_count=len(lst),
            worst_severity=worst_sev,
            findings_hashes=[f.get("finding_hash") for f in lst if f.get("finding_hash")],
        ))

    return cells


def heatmap_summary(cells: list[HeatmapCell]) -> dict:
    """Resumen agregado (conteos por status)."""
    summary = {"compliant": 0, "partial": 0, "non_compliant": 0, "not_verified": 0}
    for c in cells:
        summary[c.status] = summary.get(c.status, 0) + 1
    summary["total"] = len(cells)
    return summary
