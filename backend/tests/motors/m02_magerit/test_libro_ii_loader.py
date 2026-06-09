"""Tests Libro II loader (ADR-037 SAN-D MB-15.2)."""
from __future__ import annotations


from backend.app.motors.m02_magerit.libro_ii_loader import (
    frequency_to_probability,
    get_threats_for_asset_type,
    get_threats_for_dimension,
    load_libro_ii,
)


def test_load_libro_ii_returns_threats():
    catalog = load_libro_ii()
    assert len(catalog.threats) >= 30  # 57 amenazas oficiales esperadas


def test_load_libro_ii_groups_present():
    catalog = load_libro_ii()
    groups = {t.group_code for t in catalog.threats}
    assert {"N", "I", "E", "A"}.issubset(groups)


def test_by_code_returns_threat():
    catalog = load_libro_ii()
    fuego = catalog.by_code("N.1")
    assert fuego is not None
    assert fuego.name == "Fuego"
    assert "HW" in fuego.asset_types
    assert "D" in fuego.dimensions


def test_by_code_unknown_returns_none():
    catalog = load_libro_ii()
    assert catalog.by_code("NONEXISTENT.999") is None


def test_get_threats_for_asset_type_HW():
    threats = get_threats_for_asset_type("HW")
    codes = [t.code for t in threats]
    assert "N.1" in codes  # Fuego
    assert "I.5" in codes  # Avería físico/lógico
    assert len(threats) >= 5


def test_get_threats_for_asset_type_unknown_returns_empty():
    threats = get_threats_for_asset_type("UNKNOWN_XYZ")
    assert threats == []


def test_get_threats_for_dimension_D():
    threats = get_threats_for_dimension("D")
    assert len(threats) >= 5
    for t in threats:
        assert "D" in t.dimensions


def test_frequency_to_probability_mapping():
    assert frequency_to_probability("muy_baja") == "MB"
    assert frequency_to_probability("baja") == "B"
    assert frequency_to_probability("media") == "M"
    assert frequency_to_probability("alta") == "A"
    assert frequency_to_probability("muy_alta") == "MA"


def test_frequency_to_probability_default():
    assert frequency_to_probability(None) == "M"
    assert frequency_to_probability("desconocida") == "M"


def test_lru_cache_no_recarga():
    """load_libro_ii usa lru_cache · 2 invocaciones devuelven mismo objeto."""
    a = load_libro_ii()
    b = load_libro_ii()
    assert a is b


def test_threat_has_group_metadata():
    catalog = load_libro_ii()
    fuego_industrial = catalog.by_code("I.1")
    assert fuego_industrial is not None
    assert fuego_industrial.group_code == "I"
    assert fuego_industrial.group_name is not None
