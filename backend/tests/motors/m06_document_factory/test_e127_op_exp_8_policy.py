"""#1 Ola 7 · artefacto de política op.exp.8 (E-127).

Verifica que la política de registro de actividad (retención >=12m + NTP) está
registrada en el catálogo m06 y que su cuerpo cubre los requisitos op.exp.8.
"""
from __future__ import annotations

import pathlib

import backend.app.motors.m06_document_factory as m06
from backend.app.motors.m06_document_factory.template_registry import (
    TEMPLATE_REGISTRY,
)


def test_e127_registered_as_policy():
    assert "E-127" in TEMPLATE_REGISTRY
    entry = TEMPLATE_REGISTRY["E-127"]
    assert entry["type"] == "policies"
    assert entry["body_path"].endswith(
        "E127_politica_de_registro_de_actividad_retencion_y_ntp.md"
    )


def test_e127_body_covers_op_exp_8_requirements():
    base = pathlib.Path(m06.__file__).parent / "templates"
    body_path = base / TEMPLATE_REGISTRY["E-127"]["body_path"]
    assert body_path.exists(), f"falta el cuerpo .md en {body_path}"
    body = body_path.read_text(encoding="utf-8")
    # Requisitos op.exp.8 cubiertos en el artefacto
    assert "op.exp.8" in body
    assert "12 meses" in body
    assert "NTP" in body
    assert "RD 311/2022" in body or "Real Decreto 311/2022" in body


def test_e127_module_loads_body():
    from backend.app.motors.m06_document_factory.templates.policies import (
        E127_politica_de_registro_de_actividad_retencion_y_ntp as e127,
    )

    assert e127.TEMPLATE_ID == "E-127"
    assert "op.exp.8" in e127.TEMPLATE_BODY
