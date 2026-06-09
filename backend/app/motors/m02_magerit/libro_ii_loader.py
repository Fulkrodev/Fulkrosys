"""Magerit Libro II catalog loader (ADR-037 SAN-D MB-15.2).

Reusa yaml existing en ``docs/magerit_catalog/threats.yaml`` (57+
amenazas oficiales NIPO 630-12-171-8 con fields code/name/description/
asset_types/dimensions/typical_frequency).

Single source of truth · NO crear duplicados (DEC-MAGERIT-THIRD-YAML
ADR-037 Deferrables).

Helpers:
- ``load_libro_ii()`` · catálogo flat (lista threats con grupo).
- ``get_threats_for_asset_type(asset_type, categoria)`` · amenazas
  aplicables a un tipo de activo (con filtro categoría B/M/A si
  necesario).
- ``get_threats_for_dimension(dim)`` · amenazas afectando dimensión
  CIDAT.
- ``frequency_to_probability(typical_frequency)`` · mapping
  ``muy_baja|baja|media|alta|muy_alta`` →
  ``MB|B|M|A|MA`` (escala MAGERIT MageritThreatAssessment).
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel


class ThreatLibroII(BaseModel):
    """Amenaza Libro II catálogo (single source yaml)."""

    code: str
    name: str
    description: str | None = None
    asset_types: list[str] = []  # HW · SW · S · D · COM · SI · AUX · L · P
    dimensions: list[str] = []  # D · I · C · A · T
    typical_frequency: str | None = None  # muy_baja · baja · media · alta · muy_alta
    group_code: str  # N · I · E · A
    group_name: str | None = None


class LibroIICatalog(BaseModel):
    """Catálogo Libro II completo."""

    threats: list[ThreatLibroII] = []

    def by_code(self, code: str) -> Optional[ThreatLibroII]:
        return next((t for t in self.threats if t.code == code), None)


_FREQUENCY_TO_PROBABILITY: dict[str, str] = {
    "muy_baja": "MB",
    "baja": "B",
    "media": "M",
    "alta": "A",
    "muy_alta": "MA",
}


def _repo_root() -> Path:
    """Resolver repo_root: ``loader.py`` está 5 niveles bajo root."""
    # backend/app/motors/m02_magerit/libro_ii_loader.py
    return Path(__file__).resolve().parent.parent.parent.parent.parent


def _yaml_path() -> Path:
    return _repo_root() / "docs" / "magerit_catalog" / "threats.yaml"


@lru_cache(maxsize=1)
def load_libro_ii() -> LibroIICatalog:
    """Carga yaml + parsea threat_groups → flat list ThreatLibroII."""
    with open(_yaml_path(), encoding="utf-8") as f:
        data = yaml.safe_load(f)

    threats: list[ThreatLibroII] = []
    for group in data.get("threat_groups", []):
        group_code = group.get("group", "")
        group_name = group.get("name")
        for t in group.get("threats", []):
            threats.append(
                ThreatLibroII(
                    code=t["code"],
                    name=t["name"],
                    description=t.get("description"),
                    asset_types=list(t.get("asset_types", [])),
                    dimensions=list(t.get("dimensions", [])),
                    typical_frequency=t.get("typical_frequency"),
                    group_code=group_code,
                    group_name=group_name,
                )
            )

    return LibroIICatalog(threats=threats)


def get_threats_for_asset_type(asset_type: str) -> list[ThreatLibroII]:
    """Amenazas aplicables a un tipo de activo (matching ``asset_types``)."""
    catalog = load_libro_ii()
    return [t for t in catalog.threats if asset_type in t.asset_types]


def get_threats_for_dimension(dimension: str) -> list[ThreatLibroII]:
    """Amenazas afectando una dimensión CIDAT."""
    catalog = load_libro_ii()
    return [t for t in catalog.threats if dimension in t.dimensions]


def frequency_to_probability(typical_frequency: str | None) -> str:
    """Mapping ``typical_frequency`` yaml → probability MAGERIT (MB/B/M/A/MA)."""
    if not typical_frequency:
        return "M"  # default media
    return _FREQUENCY_TO_PROBABILITY.get(typical_frequency, "M")
