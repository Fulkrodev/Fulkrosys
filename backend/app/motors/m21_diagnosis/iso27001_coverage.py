"""ISO 27001 → ENS coverage calculator · SAN-C.MB-10.7.

Para clientes que tienen ISO 27001 vigente, calcula el % de medidas
ENS automáticamente cubiertas vía la mapping canónica CCN-STIC 825
(``ens_iso27001_mapping``).

Estrategia: el cliente lista los controles ISO 27001 implementados
(set de strings tipo "A.5.1" · "A.8.5"). El servicio cruza con la
mapping y calcula:

* % medidas ENS cubiertas (al menos 1 control ISO mapeado implementado)
* Lista medidas cubiertas + gaps específicos ENS-only
* Effort estimado ahorrado (placeholder · refinar con M17 ratio futuro)

Refs: SAN-C.MB-10.7 · CCN-STIC 825
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Iterable

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession


# Estimación bruta de horas por medida ENS no implementada que debe
# desarrollarse desde cero (vs. ya cubierta por ISO). Se usa solo
# para reportar effort_saved aproximado (placeholder · per medida).
HOURS_PER_ENS_MEASURE = 8.0


@dataclass(slots=True)
class IsoCoverageResult:
    project_id: uuid.UUID | None
    iso_controls_implemented: list[str]
    ens_measures_total: int
    ens_measures_covered: list[str]
    ens_measures_gaps: list[str]
    coverage_percent: float
    effort_hours_saved_estimate: float
    coverage_per_family: dict[str, dict[str, int]]


async def calculate_iso27001_coverage(
    db: AsyncSession,
    iso_controls_implemented: Iterable[str],
    *,
    project_id: uuid.UUID | None = None,
) -> IsoCoverageResult:
    """Calcula cobertura ENS automática a partir de controles ISO implementados.

    ``iso_controls_implemented`` es un iterable de IDs ISO 27001:2022
    Anexo A (e.g. ``{"A.5.1", "A.8.5", "A.5.24"}``).
    """
    iso_set = {c.strip() for c in iso_controls_implemented if c}

    # Mapeo: ¿qué medidas ENS quedan cubiertas?
    if iso_set:
        rows = await db.execute(
            sa_text(
                "SELECT DISTINCT ens_measure_code "
                "FROM ens_iso27001_mapping "
                "WHERE iso27001_control = ANY(:isos)"
            ),
            {"isos": list(iso_set)},
        )
        covered_set = {r[0] for r in rows.fetchall()}
    else:
        covered_set = set()

    # Total medidas ENS canónicas + por familia
    total_row = await db.execute(
        sa_text(
            "SELECT codigo, familia FROM ens_measures "
            "WHERE deleted_at IS NULL ORDER BY codigo"
        )
    )
    all_measures: list[tuple[str, str]] = [
        (str(r[0]), str(r[1] or "")) for r in total_row.fetchall()
    ]
    all_codes = [c for c, _ in all_measures]
    total = len(all_codes)
    covered = sorted(c for c in all_codes if c in covered_set)
    gaps = sorted(c for c in all_codes if c not in covered_set)
    coverage_pct = round((len(covered) / total * 100) if total else 0.0, 2)

    # Coverage per family
    per_family: dict[str, dict[str, int]] = {}
    for code, family in all_measures:
        fam = family or "(otro)"
        bucket = per_family.setdefault(fam, {"total": 0, "covered": 0})
        bucket["total"] += 1
        if code in covered_set:
            bucket["covered"] += 1

    return IsoCoverageResult(
        project_id=project_id,
        iso_controls_implemented=sorted(iso_set),
        ens_measures_total=total,
        ens_measures_covered=covered,
        ens_measures_gaps=gaps,
        coverage_percent=coverage_pct,
        effort_hours_saved_estimate=round(
            len(covered) * HOURS_PER_ENS_MEASURE, 1
        ),
        coverage_per_family=per_family,
    )
