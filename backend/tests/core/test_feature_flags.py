"""Tests feature flags catalog + helpers (ADR-036 SAN-D MB-17.1)."""
from __future__ import annotations

import pytest

from backend.app.core.feature_flags import (
    get_blocking_features_for_phase,
    get_features_for_project,
    is_feature_applicable,
    load_feature_flags,
    phase_int_to_enum,
)
from backend.app.core.workflow_phase import WorkflowPhase


def test_load_catalog_version():
    catalog = load_feature_flags()
    assert catalog.version == "1.0.0"


def test_load_catalog_features_present():
    catalog = load_feature_flags()
    assert "alta_pentest_cpstic" in catalog.features
    assert "art9_rgpd_data" in catalog.features
    assert "basica_autoevaluacion" in catalog.features


def test_basica_no_alta_features():
    """Cliente BASICA · features Alta NO aplican."""
    assert is_feature_applicable("alta_pentest_cpstic", "BASICA") is False
    assert is_feature_applicable("alta_productos_cpstic", "BASICA") is False
    assert is_feature_applicable("alta_red_team", "BASICA") is False
    assert is_feature_applicable("alta_criptografia_807", "BASICA") is False


def test_basica_si_autoevaluacion():
    """BASICA · autoevaluación 809 aplica."""
    assert is_feature_applicable("basica_autoevaluacion", "BASICA") is True


def test_alta_si_features_alta():
    """ALTA · todas features Alta aplican."""
    assert is_feature_applicable("alta_pentest_cpstic", "ALTA") is True
    assert is_feature_applicable("alta_productos_cpstic", "ALTA") is True
    assert is_feature_applicable("alta_criptografia_807", "ALTA") is True
    assert is_feature_applicable("refuerzos_r2_r3_r4", "ALTA") is True


def test_media_features_intermedias():
    """MEDIA · refuerzos R1 + auditor ENAC aplican · R2-4 no."""
    assert is_feature_applicable("refuerzos_r1", "MEDIA") is True
    assert is_feature_applicable("refuerzos_r2_r3_r4", "MEDIA") is False
    assert is_feature_applicable("media_auditor_enac", "MEDIA") is True


def test_archetype_sector_salud_lowercase():
    """sector_salud (lowercase enum) · art.9 RGPD aplica."""
    assert is_feature_applicable(
        "art9_rgpd_data", "MEDIA", archetype="sector_salud",
    ) is True
    assert is_feature_applicable(
        "art9_rgpd_data", "MEDIA", archetype="saas_only",
    ) is False


def test_archetype_saas_skip_mp_if():
    """saas_only · skip mp.if aplica."""
    assert is_feature_applicable(
        "skip_mp_if_instalaciones", "BASICA", archetype="saas_only",
    ) is True
    assert is_feature_applicable(
        "skip_mp_if_instalaciones", "BASICA", archetype="sector_salud",
    ) is False


def test_pce_nis2_combined_filter_applies():
    """PCE-NIS2 · MEDIA + proveedor_financiero + ≥50 empleados → aplica."""
    assert is_feature_applicable(
        "pce_nis2", "MEDIA", archetype="proveedor_financiero", employee_count=100,
    ) is True


def test_pce_nis2_blocked_by_basica():
    """PCE-NIS2 · BASICA bloquea aunque arquetipo y empleados OK."""
    assert is_feature_applicable(
        "pce_nis2", "BASICA", archetype="proveedor_financiero", employee_count=100,
    ) is False


def test_pce_nis2_blocked_by_archetype():
    """PCE-NIS2 · arquetipo no listado bloquea."""
    assert is_feature_applicable(
        "pce_nis2", "MEDIA", archetype="saas_only", employee_count=100,
    ) is False


def test_pce_nis2_blocked_by_employee_count():
    """PCE-NIS2 · employee_count < 50 bloquea."""
    assert is_feature_applicable(
        "pce_nis2", "MEDIA", archetype="proveedor_financiero", employee_count=20,
    ) is False


def test_pce_nis2_blocked_when_employee_count_missing():
    """PCE-NIS2 · employee_count None bloquea (no asume default)."""
    assert is_feature_applicable(
        "pce_nis2", "MEDIA", archetype="proveedor_financiero", employee_count=None,
    ) is False


def test_get_features_for_project_basica_saas():
    """BASICA + saas_only · subset features esperado."""
    features = get_features_for_project("BASICA", archetype="saas_only")
    assert features["basica_autoevaluacion"] is True
    assert features["alta_pentest_cpstic"] is False
    assert features["skip_mp_if_instalaciones"] is True
    assert features["art9_rgpd_data"] is False


def test_get_blocking_features_alta_conformity():
    """ALTA · features que bloquean Conformidad (fase 9)."""
    blocking = get_blocking_features_for_phase(9, "ALTA")
    assert "alta_pentest_cpstic" in blocking
    assert "alta_productos_cpstic" in blocking
    assert "alta_criptografia_807" in blocking


def test_get_blocking_features_media_conformity():
    """MEDIA · solo auditor ENAC bloquea Conformidad."""
    blocking = get_blocking_features_for_phase(9, "MEDIA")
    assert "media_auditor_enac" in blocking
    assert "alta_pentest_cpstic" not in blocking


def test_basica_no_blocking_to_conformity():
    """BASICA · sin features bloqueantes Conformidad (autoevaluación basta)."""
    blocking = get_blocking_features_for_phase(9, "BASICA")
    assert blocking == []


def test_phase_int_to_enum_mapping():
    """1-indexed mapping coincide con WorkflowPhase.ordered()."""
    assert phase_int_to_enum(1) == WorkflowPhase.PRE_VENTA
    assert phase_int_to_enum(3) == WorkflowPhase.DIAGNOSTICO
    assert phase_int_to_enum(8) == WorkflowPhase.VERIFICACION
    assert phase_int_to_enum(9) == WorkflowPhase.CONFORMIDAD
    assert phase_int_to_enum(10) == WorkflowPhase.RETAINER_CIERRE


def test_phase_int_to_enum_out_of_range():
    """Int fuera de rango raise ValueError."""
    with pytest.raises(ValueError):
        phase_int_to_enum(0)
    with pytest.raises(ValueError):
        phase_int_to_enum(11)


def test_unknown_feature_returns_false():
    """Feature key no catalogado retorna False."""
    assert is_feature_applicable("non_existent_feature", "ALTA") is False
