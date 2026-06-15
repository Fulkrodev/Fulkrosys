"""PCE overlay YAML catalogs loader.

Carga 3 catalogos YAML cloud (cloud_azure_es + cloud_aws_eu + cloud_gcp_eu)
y expone helpers para detectar overlay aplicable + lectura de medidas extra.

Sub-lote 1.B.8.A AMEND-016 v2 elimino overlays AAPP-only (uceens_*) por test
aplicabilidad target empresa privada licitando AAPP (LECCION-OPS-032).
"""
from __future__ import annotations

import functools
from pathlib import Path
from typing import Any

import yaml

CATALOGS_DIR = Path(__file__).parent

OVERLAY_TYPES = (
    "cloud_azure_es",
    "cloud_aws_eu",
    "cloud_gcp_eu",
)
# NOTA §2.1 (revertido): PCE NIS2/SSG (pce_nis2.yaml/pce_ssg.yaml) están en
# KNOWN_OVERLAYS pero NO en OVERLAY_TYPES → catálogos muertos. NO es un one-liner:
# el loader construye la ruta como f"pce_{overlay_type}.yaml" (los cloud usan
# overlay_type SIN prefijo "pce_"), así que requiere alinear nombre de fichero +
# overlay_type + clave KNOWN_OVERLAYS + campo interno del YAML + códigos de
# detect_overlay coherentemente. NIS2/SSG son overlays extra (NO core ENS) →
# DEFER a rewiring dedicado. Ver FIX_TRACKER §2.1.


@functools.lru_cache(maxsize=None)
def load_overlay_catalog(overlay_type: str) -> dict[str, Any]:
    """Carga el YAML del overlay. Cacheado in-process."""
    if overlay_type not in OVERLAY_TYPES:
        raise ValueError(
            f"Unknown overlay_type {overlay_type}. "
            f"Valid: {OVERLAY_TYPES}"
        )
    yaml_path = CATALOGS_DIR / f"pce_{overlay_type}.yaml"
    if not yaml_path.is_file():
        raise FileNotFoundError(f"Overlay YAML not found: {yaml_path}")
    with yaml_path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_all_catalogs() -> dict[str, dict[str, Any]]:
    """Return dict of all overlay catalogs keyed by overlay_type."""
    return {t: load_overlay_catalog(t) for t in OVERLAY_TYPES}


def suggest_overlays_by_hints(hints: list[str]) -> list[str]:
    """Given a list of hints (keywords from client metadata / architecture
    discovery), returns overlay_types whose ``auto_detect_hints`` match.
    """
    if not hints:
        return []
    hints_lc = [h.lower() for h in hints]
    matches = []
    for ov_type, catalog in load_all_catalogs().items():
        applicability = catalog.get("applicability", {})
        detect_hints = [
            h.lower() for h in applicability.get("auto_detect_hints", [])
        ]
        if any(dh in hh for dh in detect_hints for hh in hints_lc):
            matches.append(ov_type)
    return matches


def get_extra_measures(overlay_type: str, min_category: str | None = None) -> list[dict]:
    """Filtra las medidas del overlay por categoria minima (BASICA/MEDIA/ALTA)."""
    catalog = load_overlay_catalog(overlay_type)
    measures = catalog.get("extra_measures", [])
    if min_category is None:
        return list(measures)
    levels = {"BASICA": 0, "MEDIA": 1, "ALTA": 2}
    min_level = levels.get(min_category, 0)
    return [
        m for m in measures
        if levels.get(m.get("category", "BASICA"), 0) <= min_level
    ]
