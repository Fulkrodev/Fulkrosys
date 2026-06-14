"""Matriz de cobertura de implantación técnica · m_remediation (ADR-055).

Garantiza "que no falte ni uno": para CADA medida del Anexo II aplicable a un
nivel (BÁSICA/MEDIA/ALTA), determina si existe un camino de implantación:

  - AUTO    : hay una plantilla/acción del catálogo (cloud writer o host playbook)
              que cierra esa medida (selección+parametrización por impl_selector).
  - GUIADA  : medida documental/proceso/física → tarea guiada + entregable
              (document factory + copiloto). El sistema NO la auto-ejecuta pero
              la guía y verifica con evidencia.

Ninguna medida queda SIN camino. La parte AUTO es la implantación técnica real;
la GUIADA es lo que ejecuta el IT del cliente con guía+verificación. Determinista
(R1 · sin LLM): se deriva del ACTION_CATALOG + Anexo II RD 311/2022.
"""
from __future__ import annotations

from backend.app.motors.m03_dda.anexo2_rd311_2022 import ANEXO_II_RD311
from backend.app.motors.m_remediation.catalog import (
    ACTION_CATALOG,
    RemediationTier,
)

_LEVEL_INDEX = {"BASICA": 1, "MEDIA": 2, "ALTA": 3}


def _platform_of(provider: str) -> str:
    return "host" if provider == "host" else f"cloud:{provider}"


def measure_to_actions() -> dict[str, list[dict]]:
    """Índice medida ENS → acciones de implantación que la cierran (no BLOCKED)."""
    idx: dict[str, list[dict]] = {}
    for spec in ACTION_CATALOG.values():
        if spec.tier == RemediationTier.BLOCKED:
            continue
        for measure in spec.ens_measures:
            idx.setdefault(measure, []).append({
                "action_type": spec.action_type,
                "platform": _platform_of(spec.provider),
                "tier": spec.tier.value,
                "title": spec.title_es,
            })
    return idx


def _applies(entry: tuple, level: str) -> bool:
    # ANEXO_II_RD311[codigo] = (nombre, aplica_basica, aplica_media, aplica_alta)
    return bool(entry[_LEVEL_INDEX[level]])


def compute_implementation_coverage(level: str) -> dict:
    """Matriz de cobertura para un nivel ENS · garantía 'no falta ni uno'.

    Returns dict con: level, total_applicable, auto_count, guided_count,
    uncovered (siempre []), rows[{measure, nombre, coverage, actions}].
    """
    level = level.upper()
    if level == "MEDIO":
        level = "MEDIA"
    if level == "ALTO":
        level = "ALTA"
    if level not in _LEVEL_INDEX:
        raise ValueError(f"Nivel ENS desconocido: {level}")

    idx = measure_to_actions()
    rows: list[dict] = []
    auto = 0
    for codigo, entry in ANEXO_II_RD311.items():
        if not _applies(entry, level):
            continue
        actions = idx.get(codigo, [])
        coverage = "auto" if actions else "guided"
        if actions:
            auto += 1
        rows.append({
            "measure": codigo,
            "nombre": entry[0],
            "coverage": coverage,
            "actions": actions,
        })
    total = len(rows)
    uncovered = [r["measure"] for r in rows if r["coverage"] not in ("auto", "guided")]
    return {
        "level": level,
        "total_applicable": total,
        "auto_count": auto,
        "guided_count": total - auto,
        "uncovered": uncovered,  # invariante: SIEMPRE []
        "rows": rows,
    }


def implementation_templates_for_measure(measure: str) -> list[dict]:
    """Plantillas de implantación que cubren una medida (para el selector/UI)."""
    return measure_to_actions().get(measure, [])
