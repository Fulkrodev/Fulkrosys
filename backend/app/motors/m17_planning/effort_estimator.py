"""Estimador determinista de esfuerzo (Motor 17 — Apendice N).

Calibrado sobre 11 proyectos ENS 2024-2026. Las formulas viven en un
fichero JSON unico (``docs/catalogs/effort_formulas_v1.json``) para que
puedan revisarse y versionarse al margen del codigo.

Formula principal:

    horas_consultor = horas_base[categoria]
                    × factor_sector[sector]
                    × factor_madurez[madurez]
                    × factor_size[client_size]
                    × factor_complexity[complexity]

Funciones expuestas:

* ``load_formulas()``           — carga el JSON (idempotente con cache).
* ``estimate_effort(...)``      — version legacy (acepta base_hours del
  caller). Mantenida para retrocompatibilidad de Motor 17 v1.
* ``estimate_full(...)``        — calculo completo con horas_base
  intrinsecas a la categoria + breakdown auditable.
* ``estimate_duration_weeks(...)`` — duracion segun categoria.
* ``classify_size_by_employees(n)`` — bucket size automatico.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Catalog loader
# ---------------------------------------------------------------------------

CATALOG_PATH = (
    Path(__file__).resolve().parents[4]
    / "docs" / "catalogs" / "effort_formulas_v1.json"
)


class EffortFormulasError(Exception):
    """Raised when the formulas catalog is missing or malformed."""


@lru_cache(maxsize=1)
def load_formulas(path: Path | None = None) -> dict[str, Any]:
    """Load and cache effort formulas catalog.

    Pass ``path`` only in tests. Returns the parsed JSON dict.
    """
    p = path or CATALOG_PATH
    if not p.exists():
        raise EffortFormulasError(f"Effort formulas catalog not found at {p}")
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    for key in (
        "horas_base_por_categoria",
        "factor_sector",
        "factor_madurez",
        "factor_size_empleados",
        "factor_complejidad_tecnica",
        "duracion_semanas_por_categoria",
    ):
        if key not in data:
            raise EffortFormulasError(
                f"Missing required key '{key}' in effort formulas catalog"
            )
    return data


def reset_formulas_cache() -> None:
    """Clear the load_formulas cache (use only in tests)."""
    load_formulas.cache_clear()


# ---------------------------------------------------------------------------
# Legacy API (mantained for backwards compatibility — tests v1)
# ---------------------------------------------------------------------------

# Tablas legacy expuestas para tests que importan el factor directamente.
# Se rellenan al cargar el catalogo por primera vez.

CATEGORIA_FACTOR: dict[str, float] = {"BASICA": 0.6, "MEDIA": 1.0, "ALTA": 1.5}
SIZE_FACTOR: dict[str, float] = {
    "micro": 0.7,
    "pequena": 0.85,
    "mediana": 1.0,
    "grande": 1.3,
    "muy_grande": 1.6,
}
COMPLEXITY_FACTOR: dict[str, float] = {
    "baja": 0.8,
    "media": 1.0,
    "alta": 1.3,
    "muy_alta": 1.6,
}

VALID_SIZES = set(SIZE_FACTOR.keys())
VALID_COMPLEXITY = set(COMPLEXITY_FACTOR.keys())
VALID_CATEGORIAS = set(CATEGORIA_FACTOR.keys())


def estimate_effort(
    base_hours: float,
    categoria: str,
    client_size: str = "mediana",
    complexity: str = "media",
) -> float:
    """Legacy: caller provides base_hours, we apply 3 multiplicative factors.

    Mantenido para los tests v1 de Motor 17 que pasan base_hours
    explicitamente. Para nuevos consumidores, usar ``estimate_full``.
    """
    cat = (categoria or "").upper()
    size = (client_size or "").lower()
    comp = (complexity or "").lower()
    factor = (
        CATEGORIA_FACTOR.get(cat, 1.0)
        * SIZE_FACTOR.get(size, 1.0)
        * COMPLEXITY_FACTOR.get(comp, 1.0)
    )
    return round((base_hours or 0.0) * factor, 1)


def estimate_duration_weeks(categoria: str) -> int:
    """Duracion en semanas calendario por categoria (no cambia con factores)."""
    try:
        formulas = load_formulas()
        return int(
            formulas["duracion_semanas_por_categoria"].get(
                (categoria or "").upper(), 36,
            )
        )
    except EffortFormulasError:
        return {"BASICA": 18, "MEDIA": 36, "ALTA": 60}.get(
            (categoria or "").upper(), 36,
        )


# ---------------------------------------------------------------------------
# Full estimator (Apendice N — calibrado)
# ---------------------------------------------------------------------------

def classify_size_by_employees(n_empleados: int | None) -> str:
    """Mapea numero de empleados a bucket size.

    Devuelve siempre un bucket valido. None o 0 -> 'micro'.
    """
    if n_empleados is None or n_empleados <= 0:
        return "micro"
    formulas = load_formulas()
    buckets = formulas["factor_size_empleados"]
    # Orden por max_empleados ascendente; el ultimo (None) es 'muy_grande'
    for bucket_name in ("micro", "pequena", "mediana", "grande"):
        info = buckets.get(bucket_name, {})
        max_emp = info.get("max_empleados")
        if max_emp is not None and n_empleados <= max_emp:
            return bucket_name
    return "muy_grande"


def estimate_full(
    categoria: str,
    sector: str = "generico",
    madurez: str = "L3",
    client_size: str | None = "mediana",
    complexity: str = "media",
    n_empleados: int | None = None,
    tarifa_hora_eur: float | None = None,
) -> dict[str, Any]:
    """Calculo completo de esfuerzo del consultor.

    Args:
        categoria: BASICA | MEDIA | ALTA (categorizacion ENS Anexo I).
        sector: clave de ``factor_sector`` (salud, financiero, ...).
        madurez: L1 | L2 | L3 | L4 | L5.
        client_size: micro | pequena | mediana | grande | muy_grande.
            Si es None y se pasa ``n_empleados``, se infiere automaticamente.
        complexity: baja | media | alta | muy_alta.
        n_empleados: opcional, para auto-clasificacion del size.
        tarifa_hora_eur: opcional. Si se omite, usa el default del catalogo.

    Returns:
        dict con breakdown auditable: horas_base, factores aplicados,
        factor_combinado, horas_consultor, presupuesto_eur, duracion_semanas,
        avisos (warnings sobre limites).
    """
    formulas = load_formulas()

    cat = (categoria or "").upper()
    sec = (sector or "generico").lower()
    mad = (madurez or "L3").upper()
    comp = (complexity or "media").lower()

    if cat not in formulas["horas_base_por_categoria"]:
        raise EffortFormulasError(
            f"Categoria '{cat}' no valida. "
            f"Validas: {sorted(formulas['horas_base_por_categoria'].keys())}"
        )

    # Auto-clasificacion size si no se especifica
    size = (client_size or "").lower() if client_size else None
    if not size:
        size = classify_size_by_employees(n_empleados)

    # Resolver factores (con fallback neutro 1.0 si la clave no existe)
    sec_entry = formulas["factor_sector"].get(sec)
    mad_entry = formulas["factor_madurez"].get(mad)
    size_entry = formulas["factor_size_empleados"].get(size)
    comp_entry = formulas["factor_complejidad_tecnica"].get(comp)

    avisos: list[str] = []

    if sec_entry is None:
        sec_entry = {"factor": 1.0, "label": f"sector desconocido '{sec}' (factor neutro 1.0)"}
        avisos.append(f"Sector '{sec}' no esta en el catalogo; aplicado factor neutro 1.0")
    if mad_entry is None:
        mad_entry = {"factor": 1.0, "label": f"madurez desconocida '{mad}' (factor neutro 1.0)"}
        avisos.append(f"Madurez '{mad}' no esta en el catalogo; aplicado factor neutro 1.0")
    if size_entry is None:
        size_entry = {"factor": 1.0, "label": f"size desconocido '{size}' (factor neutro 1.0)"}
        avisos.append(f"Tamano '{size}' no esta en el catalogo; aplicado factor neutro 1.0")
    if comp_entry is None:
        comp_entry = {"factor": 1.0, "label": f"complejidad desconocida '{comp}' (factor neutro 1.0)"}
        avisos.append(f"Complejidad '{comp}' no esta en el catalogo; aplicado factor neutro 1.0")

    horas_base = float(formulas["horas_base_por_categoria"][cat])
    f_sec = float(sec_entry["factor"])
    f_mad = float(mad_entry["factor"])
    f_size = float(size_entry["factor"])
    f_comp = float(comp_entry["factor"])

    factor_combinado = round(f_sec * f_mad * f_size * f_comp, 4)

    limites = formulas.get("limites", {})
    cap = float(limites.get("factor_combinado_max", 3.5))
    floor = float(limites.get("factor_combinado_min", 0.40))
    if factor_combinado > cap:
        avisos.append(
            f"Factor combinado {factor_combinado} > {cap}. "
            f"Replantear modalidad del proyecto."
        )
    if factor_combinado < floor:
        avisos.append(
            f"Factor combinado {factor_combinado} < {floor}. "
            f"Verificar alcance: puede no ser un proyecto real."
        )

    horas_consultor = round(horas_base * factor_combinado, 1)
    duracion_semanas = int(
        formulas["duracion_semanas_por_categoria"].get(cat, 36)
    )

    tarifa = (
        float(tarifa_hora_eur)
        if tarifa_hora_eur is not None
        else float(formulas.get("tarifa_hora_eur_default", 95))
    )
    presupuesto_eur = round(horas_consultor * tarifa, 2)

    return {
        "version_formulas": formulas.get("version", "unknown"),
        "categoria": cat,
        "sector": sec,
        "madurez": mad,
        "client_size": size,
        "size_inferido_de_empleados": (
            n_empleados if not client_size else None
        ),
        "complexity": comp,
        "horas_base": horas_base,
        "factor_sector":      {"valor": f_sec,  "label": sec_entry.get("label", "")},
        "factor_madurez":     {"valor": f_mad,  "label": mad_entry.get("label", "")},
        "factor_size":        {"valor": f_size, "label": size_entry.get("label", "")},
        "factor_complexity":  {"valor": f_comp, "label": comp_entry.get("label", "")},
        "factor_combinado": factor_combinado,
        "horas_consultor": horas_consultor,
        "tarifa_hora_eur": tarifa,
        "presupuesto_eur": presupuesto_eur,
        "duracion_semanas": duracion_semanas,
        "avisos": avisos,
    }
