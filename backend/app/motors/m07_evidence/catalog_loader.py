"""Cached loader and query helpers for the evidence types catalog."""
from __future__ import annotations

import json
from pathlib import Path
from functools import lru_cache

from backend.app.motors.m07_evidence.types import (
    EvidenceTypesCatalog,
    EvidenceTypeTemplate,
)

_CATALOG_PATH = Path(__file__).parent / "catalog" / "evidence_types.json"


@lru_cache(maxsize=1)
def load_catalog(catalog_path: Path | None = None) -> EvidenceTypesCatalog:
    """Load and validate the evidence types catalog from JSON.

    Cached after first call. Pass catalog_path to override (for tests).
    """
    path = catalog_path or _CATALOG_PATH
    if not path.exists():
        raise FileNotFoundError(f"Evidence catalog not found: {path}")

    raw = json.loads(path.read_text(encoding="utf-8"))
    return EvidenceTypesCatalog.model_validate(raw)


def get_type_by_id(type_id: str) -> EvidenceTypeTemplate | None:
    """Return a single evidence type by ID, or None."""
    catalog = load_catalog()
    for t in catalog.types:
        if t.id == type_id:
            return t
    return None


def get_types_by_categoria(categoria: str) -> list[EvidenceTypeTemplate]:
    """Return all evidence types with a given categoria."""
    catalog = load_catalog()
    return [t for t in catalog.types if t.categoria == categoria]


def get_types_for_measure(measure_code: str) -> list[EvidenceTypeTemplate]:
    """Return all evidence types associated with a given ENS measure code."""
    catalog = load_catalog()
    return [t for t in catalog.types if measure_code in t.medidas_asociadas]


def get_all_categorias() -> set[str]:
    """Return the set of all categorias in the catalog."""
    catalog = load_catalog()
    return {t.categoria for t in catalog.types}


def reset_cache() -> None:
    """Clear the LRU cache (for test isolation)."""
    load_catalog.cache_clear()
