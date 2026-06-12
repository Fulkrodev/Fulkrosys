"""#37 OlaIV · E-235 Procedimiento de Sellado de Tiempo (mp.info.4).

La medida mp.info.4 (Sellos de tiempo) es refuerzo solo-ALTA. Decisión #37:
incorporar el procedimiento DOCUMENTADO ahora y diferir la TSA cualificada eIDAS/
RFC 3161 al primer proyecto ALTA. Estos tests blindan que la plantilla está
registrada, es cargable, cubre la medida + el marco eIDAS/RFC 3161 y es honesta
sobre la brecha de cualificación (mecanismo interno vs sello cualificado).
"""
from __future__ import annotations

from backend.app.motors.m06_document_factory.template_registry import (
    TEMPLATE_REGISTRY,
    load_template_module,
)


def test_e235_registered_as_procedure():
    assert "E-235" in TEMPLATE_REGISTRY
    assert TEMPLATE_REGISTRY["E-235"]["type"] == "procedures"


def test_e235_loadable_and_consistent():
    mod = load_template_module("E-235")
    assert mod is not None
    assert mod.TEMPLATE_ID == "E-235"
    assert mod.TEMPLATE_TYPE == "procedures"
    assert len(mod.TEMPLATE_BODY) >= 500
    assert "{{" in mod.TEMPLATE_BODY  # Jinja2


def test_e235_covers_measure_and_eidas_framework():
    body = load_template_module("E-235").TEMPLATE_BODY
    assert "mp.info.4" in body  # medida canónica del sistema (audit_sim)
    assert "311/2022" in body
    assert "RFC 3161" in body
    assert "910/2014" in body or "eIDAS" in body  # sello cualificado


def test_e235_alta_only_and_honest_gap():
    body = load_template_module("E-235").TEMPLATE_BODY
    # refuerzo solo-ALTA explícito
    assert "ALTA" in body
    assert "BÁSICA" in body and "MEDIA" in body  # declara no-aplicabilidad
    # honestidad: distingue mecanismo interno de sello cualificado + defer TSA.
    # R10: el placeholder 'PENDIENTE REVISIÓN CONSULTOR' se resolvió (ya no debe
    # aparecer en una plantilla emitible); la honestidad sobre la brecha permanece.
    assert "PENDIENTE REVISIÓN CONSULTOR" not in body
    assert "brecha" in body.lower()  # distingue mecanismo interno vs sello cualificado
    assert "audit_log" in body  # mecanismo interno actual (cadena hash R6)
