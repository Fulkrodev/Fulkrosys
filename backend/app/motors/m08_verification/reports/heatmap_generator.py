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

from backend.app.motors.m03_dda.anexo2_rd311_2022 import ANEXO_II_RD311


CELL_STATUS = {"compliant", "partial", "non_compliant", "not_verified"}


# Derivado de la FUENTE ÚNICA RD 311/2022 (Anexo II) para que el heatmap NUNCA
# vuelva a derivar al RD 3/2010. La lista hardcodeada anterior tenía códigos
# fantasma (op.exp.11, op.nub.2) y omitía medidas reales (mp.s.3, mp.s.4).
ENS_73_MEASURES: list[str] = list(ANEXO_II_RD311.keys())


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
