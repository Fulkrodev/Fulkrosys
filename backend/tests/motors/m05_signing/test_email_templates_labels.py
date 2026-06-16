"""m05_signing email step-up labels · audit-roundup-W3 §4.1/341.

Verifica que get_signable_label cubre TODOS los SignableType canónicos:
los 4 tipos que faltaban en SIGNABLE_LABELS_ES (declaracion_conformidad_basica,
retainer_quarterly_signoff, acta_decision_direccion, contrato_comercial) ya NO
devuelven el genérico "Documento" sino la etiqueta canónica.
"""
from __future__ import annotations

from backend.app.motors.m05_signing.email_templates import (
    SIGNABLE_LABELS_ES,
    get_signable_label,
)
from backend.app.motors.m05_signing.signable_types import (
    SIGNABLE_TYPE_LABELS,
    SIGNABLE_TYPES,
)


# Los 4 tipos firmables que faltaban en el mapa email-friendly y caían a "Documento".
_PREVIOUSLY_MISSING = (
    "declaracion_conformidad_basica",
    "retainer_quarterly_signoff",
    "acta_decision_direccion",
    "contrato_comercial",
)


def test_previously_missing_labels_now_resolve_canonical():
    for st in _PREVIOUSLY_MISSING:
        label = get_signable_label(st)
        assert label != "Documento", f"{st} todavía cae al genérico"
        assert label == SIGNABLE_TYPE_LABELS[st]


def test_all_signable_types_have_non_generic_label():
    """Ningún SignableType (excepto document_generic) cae al genérico 'Documento'."""
    for st in SIGNABLE_TYPES:
        label = get_signable_label(st)
        if st == "document_generic":
            assert label == "Documento"
        else:
            assert label != "Documento", f"{st} sin etiqueta propia"


def test_email_friendly_variant_wins_where_defined():
    """Donde SIGNABLE_LABELS_ES define variante propia, esa gana (no la canónica)."""
    # 'dda' tiene variante email-friendly distinta de la canónica.
    assert get_signable_label("dda") == SIGNABLE_LABELS_ES["dda"]
    assert get_signable_label("dda") != SIGNABLE_TYPE_LABELS["dda"]


def test_unknown_type_falls_back_to_generic():
    assert get_signable_label("nonexistent_type_xyz") == "Documento"
