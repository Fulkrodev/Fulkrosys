"""Feature flags catalog declarativo per categoría ENS + arquetipo PYME.

ADR-036 (SAN-D MB-17). YAML único en
``categoria_archetype_features.yaml`` define qué features aplican
per ``Project.categoria_objetivo`` (BASICA|MEDIA|ALTA) y/o
``Project.archetype`` (lowercase enum ``PymeArquetipo``).

Source of truth backend + frontend (TS types lowercase matching enum
values reales). 4 helpers expuestos:

- ``load_feature_flags()`` · YAML loader con ``lru_cache`` (1 carga
  proceso).
- ``is_feature_applicable(key, categoria, archetype, employee_count)``
  · True si feature aplica a este proyecto.
- ``get_features_for_project(categoria, archetype, employee_count)``
  · dict completo ``{feature_key: bool}``.
- ``get_blocking_features_for_phase(target_phase, categoria, archetype)``
  · lista features que bloquean transición a target_phase si no
  completas.

Helper auxiliar ``phase_int_to_enum(n)`` mapea int 1-indexed a
``WorkflowPhase`` real (1=PRE_VENTA … 9=CONFORMIDAD … 10=RETAINER_CIERRE).

Decisión arquitectónica: YAML estático suficiente (no DB-driven).
Permite source-control diff de cambios feature scope · review
explícito · sin migration data necesaria. Si dynamic per-tenant
override emerge necesidad → tabla ``feature_flag_overrides``
deferred MB-19+.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional, Union

import yaml
from pydantic import BaseModel

from backend.app.core.workflow_phase import WorkflowPhase


class FeatureFlag(BaseModel):
    """Definición canónica de una feature flag."""

    description: str
    applicable_categories: Union[list[str], str]
    applicable_archetypes: Union[list[str], str]
    required_for_phase: Union[int, str, None] = None
    blocks_phase_transition_if_missing: Optional[int] = None
    ui_paths: Optional[list[str]] = None
    requires_employee_count: Optional[str] = None
    mp_sw_reforzado: bool = False


class FeatureFlagsCatalog(BaseModel):
    """Catalog completo · loaded once con ``lru_cache``."""

    version: str
    features: dict[str, FeatureFlag]
    always_required: list[str] = []


@lru_cache(maxsize=1)
def load_feature_flags() -> FeatureFlagsCatalog:
    """Carga YAML una sola vez por proceso."""
    yaml_path = Path(__file__).parent / "categoria_archetype_features.yaml"
    with open(yaml_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return FeatureFlagsCatalog(**data)


def is_feature_applicable(
    feature_key: str,
    categoria: str,
    archetype: Optional[str] = None,
    employee_count: Optional[int] = None,
) -> bool:
    """True si feature aplica al proyecto dado categoría + arquetipo + empleados."""
    catalog = load_feature_flags()

    if feature_key in catalog.always_required:
        return True

    feature = catalog.features.get(feature_key)
    if not feature:
        return False

    cats = feature.applicable_categories
    if cats != "ALL" and categoria not in cats:
        return False

    archs = feature.applicable_archetypes
    if archs != "ALL":
        if archetype is None or archetype not in archs:
            return False

    if feature.requires_employee_count and employee_count is not None:
        op = feature.requires_employee_count
        if op.startswith(">="):
            if employee_count < int(op[2:]):
                return False
        elif op.startswith(">"):
            if employee_count <= int(op[1:]):
                return False
    elif feature.requires_employee_count and employee_count is None:
        return False

    return True


def get_features_for_project(
    categoria: str,
    archetype: Optional[str] = None,
    employee_count: Optional[int] = None,
) -> dict[str, bool]:
    """Retorna dict ``{feature_key: bool}`` con todas features evaluadas."""
    catalog = load_feature_flags()
    return {
        key: is_feature_applicable(key, categoria, archetype, employee_count)
        for key in catalog.features.keys()
    }


def get_blocking_features_for_phase(
    target_phase: int,
    categoria: str,
    archetype: Optional[str] = None,
) -> list[str]:
    """Features aplicables que bloquean transición a target_phase si no completas."""
    catalog = load_feature_flags()
    blocking = []
    for key, feature in catalog.features.items():
        if not is_feature_applicable(key, categoria, archetype):
            continue
        if feature.blocks_phase_transition_if_missing == target_phase:
            blocking.append(key)
    return blocking


def phase_int_to_enum(n: int) -> WorkflowPhase:
    """Mapea int 1-indexed a ``WorkflowPhase`` enum real.

    1=PRE_VENTA · 2=ONBOARDING · 3=DIAGNOSTICO · 4=ANALISIS_RIESGOS ·
    5=ADECUACION · 6=IMPLANTACION · 7=DDA_FINAL · 8=VERIFICACION ·
    9=CONFORMIDAD · 10=RETAINER_CIERRE.

    Raises:
        ValueError: si ``n`` fuera de rango [1, 10].
    """
    ordered = WorkflowPhase.ordered()
    if n < 1 or n > len(ordered):
        raise ValueError(f"phase int {n} fuera de rango [1, {len(ordered)}]")
    return ordered[n - 1]
