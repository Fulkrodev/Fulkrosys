"""Tests for M16 addendum v2.2 extensions (route gate, topology, overlay, retainer profile)."""
from backend.app.motors.m16_onboarding.addendum_v22 import (
    overlay_detection_block,
    retainer_profile_predictor,
    role_topology_designer,
    route_gate_block,
)


def test_route_gate_basica_forces_declaration():
    out = route_gate_block("BASICA")
    assert out["blocked_until_locked"] is True
    assert out["required_route_type"] == "DECLARATION"


def test_route_gate_alta_forces_certification():
    out = route_gate_block("ALTA")
    assert out["required_route_type"] == "CERTIFICATION"


def test_topology_designer_returns_known_pattern():
    out = role_topology_designer("saas_tech", 100, True, True, False, "MEDIA")
    assert out["recommended_pattern"].startswith("PATTERN_")
    assert "rationale" in out


def test_overlay_detection_returns_dict():
    out = overlay_detection_block("sanidad_privada", "MEDIA")
    assert out["overlay_code"] == "PCE-SALUD"


def test_retainer_profile_predictor_critical_for_alta():
    out = retainer_profile_predictor("ALTA", 200, True, "saas_tech")
    assert out["predicted_profile"] == "R_CRITICAL"


def test_retainer_profile_predictor_lite_for_micro():
    out = retainer_profile_predictor("BASICA", 5, False, "generico")
    assert out["predicted_profile"] == "R_LITE"
