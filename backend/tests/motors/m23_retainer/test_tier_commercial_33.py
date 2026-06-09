"""#33 Ola8 · mapeo de los 5 tiers técnicos a los 3 comerciales (presentación).

Los 5 técnicos (R_MICRO/R_LITE/R_STD/R_PLUS/R_CRITICAL · cadencia/SLA/horas reales)
se mantienen como fuente de verdad; tier_to_commercial los proyecta a los 3 que
Marcos usa de cara al cliente (R_BÁSICO/R_MEDIO/R_ALTO).
"""
from __future__ import annotations

from backend.app.motors.m23_retainer.paso2_extensions import suggest_tier
from backend.app.motors.m23_retainer.retainer_service import (
    CADENCES_BY_PROFILE,
    tier_to_commercial,
)


def test_tier_to_commercial_mapping():
    assert tier_to_commercial("R_MICRO") == "R_BÁSICO"
    assert tier_to_commercial("R_LITE") == "R_BÁSICO"
    assert tier_to_commercial("R_STD") == "R_MEDIO"
    assert tier_to_commercial("R_PLUS") == "R_ALTO"
    assert tier_to_commercial("R_CRITICAL") == "R_ALTO"


def test_tier_to_commercial_unknown_degrades():
    assert tier_to_commercial("R_UNKNOWN") == "R_UNKNOWN"


def test_all_technical_tiers_have_commercial_label():
    # los 5 técnicos siguen existiendo y todos mapean a uno de los 3 comerciales
    for tier in CADENCES_BY_PROFILE:
        assert tier_to_commercial(tier) in {"R_BÁSICO", "R_MEDIO", "R_ALTO"}


def test_suggest_tier_includes_commercial_label():
    assert suggest_tier("MEDIA", empleados=50)["tier_comercial"] == "R_MEDIO"
    assert suggest_tier("BASICA", empleados=5)["tier_comercial"] == "R_BÁSICO"
    assert suggest_tier("ALTA", empleados=300)["tier_comercial"] == "R_ALTO"
