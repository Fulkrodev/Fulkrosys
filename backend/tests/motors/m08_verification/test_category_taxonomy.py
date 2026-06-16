"""WAVE C3 (tracker §2.2 line 229) — canonical ENS category taxonomy bridge.

Two taxonomies coexist by design in m08_verification: internal autopilot keys
(masculine BASICO/MEDIO/ALTO) vs ENS project field categoria_objetivo (feminine
BASICA/MEDIA/ALTA). These tests pin the single shared normalizer that bridges
both and verify the orchestrator's _normalize_category re-uses it.
"""
from __future__ import annotations

import pytest

from backend.app.motors.m08_verification.category_taxonomy import (
    ALTO,
    BASICO,
    MEDIO,
    is_alta,
    normalize_category,
    to_ens_category,
)


@pytest.mark.parametrize(
    "value,expected",
    [
        ("BASICA", BASICO), ("BASICO", BASICO),
        ("basica", BASICO), ("Basico", BASICO),
        ("MEDIA", MEDIO), ("MEDIO", MEDIO), ("media", MEDIO),
        ("ALTA", ALTO), ("ALTO", ALTO), ("alta", ALTO), (" Alto ", ALTO),
    ],
)
def test_normalize_category_collapses_both_genders(value, expected):
    assert normalize_category(value) == expected


@pytest.mark.parametrize("value", [None, "", "   ", "EXTREMA"])
def test_normalize_category_unknown_defaults_to_basico(value):
    # Fail-safe: unknown/empty -> least-privileged scan plan.
    assert normalize_category(value) == BASICO


def test_normalize_category_custom_default():
    assert normalize_category(None, default=MEDIO) == MEDIO


def test_to_ens_category_feminine_form():
    assert to_ens_category("ALTO") == "ALTA"
    assert to_ens_category("ALTA") == "ALTA"
    assert to_ens_category("medio") == "MEDIA"
    assert to_ens_category("BASICO") == "BASICA"
    assert to_ens_category(None) is None
    assert to_ens_category("garbage") is None


def test_is_alta_robust_to_both_spellings():
    assert is_alta("ALTA") is True
    assert is_alta("ALTO") is True
    assert is_alta("alta") is True
    assert is_alta("MEDIA") is False
    assert is_alta("BASICA") is False
    assert is_alta(None) is False
    assert is_alta("") is False


def test_orchestrator_normalize_category_uses_shared_source():
    # The orchestrator's private alias must delegate to the canonical bridge.
    from backend.app.motors.m08_verification.autopilot.orchestrator import (
        _normalize_category,
    )

    assert _normalize_category("ALTA") == ALTO
    assert _normalize_category("media") == MEDIO
    assert _normalize_category(None) == BASICO


def test_category_plan_keys_match_internal_taxonomy():
    from backend.app.motors.m08_verification.autopilot.orchestrator import (
        CATEGORY_PLAN,
    )

    assert set(CATEGORY_PLAN.keys()) == {BASICO, MEDIO, ALTO}
