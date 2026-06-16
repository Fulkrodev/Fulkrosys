"""WAVE C1 · §4.4/370 parte A — resolución robusta de la garantía comercial.

La garantía pasa a leerse de la fuente ESTRUCTURADA ``importe_desglose["garantia"]``
con fallback legacy al marcador de texto libre ``Garantia:`` en ``notas_marcos``.
"""
from backend.app.motors.m13_commercial.garantia import extract_garantia


def test_prefers_structured_desglose():
    desglose = {"garantia": "Devolución total si no se completa la implantación."}
    notas = "Notas internas\n\nGarantia: marcador-legacy-ignorado"
    assert extract_garantia(desglose, notas) == (
        "Devolución total si no se completa la implantación."
    )


def test_fallback_to_legacy_notas_marker():
    desglose = {"base": 10700.0}  # sin clave garantia (fila antigua)
    notas = "Algo\n\nGarantia: 30 días de devolución"
    assert extract_garantia(desglose, notas) == "30 días de devolución"


def test_empty_when_no_source():
    assert extract_garantia({}, "") == ""
    assert extract_garantia(None, None) == ""


def test_structured_blank_falls_back_to_legacy():
    desglose = {"garantia": "   "}  # estructurada vacía → no cuenta
    notas = "Garantia: garantía recuperada del marcador"
    assert extract_garantia(desglose, notas) == "garantía recuperada del marcador"
