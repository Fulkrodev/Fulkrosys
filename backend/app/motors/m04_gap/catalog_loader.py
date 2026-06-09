"""Motor 4 -- Gap Analysis Engine -- catalog loader.

Loads the severity and quick-win rules catalog from YAML.
Pattern consistent with M19 catalog_loader.py.
"""
from pathlib import Path
from typing import Any

import yaml

from backend.app.motors.m04_gap.exceptions import (
    SeverityCatalogNotFoundError,
    SeverityCatalogParseError,
)

CATALOG_PATH = Path(__file__).resolve().parents[4] / "docs" / "catalogs" / "gap_severity_rules_v1.yaml"

REQUIRED_MEDIDA_FIELDS = [
    "codigo", "nombre", "familia", "marco", "aplica_desde",
    "severidad_base", "esfuerzo_horas_base", "quick_win",
    "guia_remediacion", "evidencia_tipica", "notas_auditor",
]

VALID_SEVERIDADES = {"critica", "alta", "media", "baja", "informativa"}
VALID_CATEGORIAS_ENS = {"basica", "media", "alta"}


def load_catalog(catalog_path: Path | None = None) -> dict[str, Any]:
    """Load and validate gap_severity_rules catalog YAML."""
    path = catalog_path or CATALOG_PATH
    if not path.exists():
        raise SeverityCatalogNotFoundError(f"Catalog not found at {path}")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise SeverityCatalogParseError(f"YAML parse error: {e}") from e

    if not isinstance(data, dict):
        raise SeverityCatalogParseError("Catalog root is not a dict")
    if "medidas" not in data:
        raise SeverityCatalogParseError("Missing 'medidas' key")
    if "medidas_criticas_nucleares" not in data:
        raise SeverityCatalogParseError("Missing 'medidas_criticas_nucleares' key")
    if "thresholds" not in data:
        raise SeverityCatalogParseError("Missing 'thresholds' key")

    medidas = data["medidas"]
    if not isinstance(medidas, list):
        raise SeverityCatalogParseError("'medidas' is not a list")

    for idx, m in enumerate(medidas):
        for field in REQUIRED_MEDIDA_FIELDS:
            if field not in m:
                raise SeverityCatalogParseError(
                    f"Medida idx={idx} codigo={m.get('codigo', '?')} missing field: {field}"
                )
        # Validate severidad_base structure
        sb = m["severidad_base"]
        if not isinstance(sb, dict) or set(sb.keys()) != VALID_CATEGORIAS_ENS:
            raise SeverityCatalogParseError(
                f"Medida {m['codigo']} has invalid severidad_base structure"
            )
        for cat, sev in sb.items():
            if sev not in VALID_SEVERIDADES:
                raise SeverityCatalogParseError(
                    f"Medida {m['codigo']} has invalid severidad '{sev}' for categoria '{cat}'"
                )

    return data


def get_medida_rule(catalog: dict[str, Any], codigo: str) -> dict[str, Any] | None:
    """Get a single medida rule by its codigo."""
    for m in catalog["medidas"]:
        if m["codigo"] == codigo:
            return m
    return None


def is_nuclear(catalog: dict[str, Any], codigo: str) -> bool:
    """Check if a measure is in the critical-nuclear list."""
    return codigo in catalog.get("medidas_criticas_nucleares", [])


def get_severidad_for_categoria(
    catalog: dict[str, Any],
    codigo: str,
    categoria: str,
) -> str | None:
    """Return severidad base for a medida in a given system category."""
    m = get_medida_rule(catalog, codigo)
    if m is None:
        return None
    cat = categoria.lower()
    return m["severidad_base"].get(cat)


def get_esfuerzo_for_categoria(
    catalog: dict[str, Any],
    codigo: str,
    categoria: str,
) -> int | None:
    """Return esfuerzo_horas for a medida in a given system category."""
    m = get_medida_rule(catalog, codigo)
    if m is None:
        return None
    cat = categoria.lower()
    return m["esfuerzo_horas_base"].get(cat)


def is_quick_win_for_categoria(
    catalog: dict[str, Any],
    codigo: str,
    categoria: str,
) -> bool:
    """Quick win if base quick_win flag AND severidad>=alta AND esfuerzo<=threshold."""
    m = get_medida_rule(catalog, codigo)
    if m is None or not m.get("quick_win"):
        return False
    sev = get_severidad_for_categoria(catalog, codigo, categoria)
    esf = get_esfuerzo_for_categoria(catalog, codigo, categoria)
    thresh_horas = catalog["thresholds"]["quick_win_max_horas"]
    if sev not in {"alta", "critica"}:
        return False
    return (esf or 999) <= thresh_horas


def get_catalog_version(catalog: dict[str, Any]) -> str:
    """Extract the version string from a loaded catalog."""
    return str(catalog.get("version", "unknown"))


def get_total_medidas(catalog: dict[str, Any]) -> int:
    """Get the total number of medidas in the catalog."""
    return len(catalog.get("medidas", []))
