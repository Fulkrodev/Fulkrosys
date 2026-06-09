"""Tests gap engine · cobertura por categoría ENS BASICA/MEDIA/ALTA.

Verifica:
- BASICA aplica subset menor (sin op.acc.5 · sin op.exp.8 · sin op.cont.3)
- MEDIA aplica subset intermedio
- ALTA aplica todas las reglas del catalog
- categoría None/desconocida → 0 reglas
- normalización aliases (B/M/A · básica/básica con tilde)
"""
from __future__ import annotations

from backend.app.motors.m_cloud_connectors import (
    RULE_CATALOG,
    rules_for_category,
)
from backend.app.motors.m_cloud_connectors.diagnostic_gap_engine import (
    _normalize_category,
)


def test_basica_subset():
    rules = rules_for_category("BASICA")
    codes = {r.ens_measure_code for r in rules}
    # BASICA NO incluye: op.acc.5 · op.exp.8 · op.cont.3 (MEDIA/ALTA only)
    assert "op.acc.5" not in codes
    assert "op.exp.8" not in codes
    assert "op.cont.3" not in codes
    # BASICA SI incluye estos nucleares cliente-piloto
    assert "op.acc.6" in codes
    assert "mp.info.3" in codes
    assert "op.exp.1" in codes
    assert "org.1" in codes


def test_media_includes_logging_and_privilege_rules():
    rules = rules_for_category("MEDIA")
    codes = {r.ens_measure_code for r in rules}
    assert "op.acc.5" in codes
    assert "op.exp.8" in codes
    assert "op.cont.3" in codes


def test_alta_covers_all_catalog():
    rules = rules_for_category("ALTA")
    codes = {r.ens_measure_code for r in rules}
    expected = {r.ens_measure_code for r in RULE_CATALOG}
    assert codes == expected


def test_unknown_category_returns_empty():
    assert rules_for_category("UNKNOWN") == ()
    assert rules_for_category("") == ()
    assert rules_for_category(None) == ()


def test_category_alias_normalization():
    assert _normalize_category("B") == "BASICA"
    assert _normalize_category("M") == "MEDIA"
    assert _normalize_category("A") == "ALTA"
    assert _normalize_category("basica") == "BASICA"
    assert _normalize_category("BÁSICA") == "BASICA"
    assert _normalize_category("media") == "MEDIA"
    assert _normalize_category("ALTA") == "ALTA"
    assert _normalize_category("XYZ") is None


def test_alta_strictly_superset_of_media():
    media_codes = {r.ens_measure_code for r in rules_for_category("MEDIA")}
    alta_codes = {r.ens_measure_code for r in rules_for_category("ALTA")}
    assert media_codes.issubset(alta_codes)


def test_media_strictly_superset_of_basica():
    basica_codes = {r.ens_measure_code for r in rules_for_category("BASICA")}
    media_codes = {r.ens_measure_code for r in rules_for_category("MEDIA")}
    assert basica_codes.issubset(media_codes)
