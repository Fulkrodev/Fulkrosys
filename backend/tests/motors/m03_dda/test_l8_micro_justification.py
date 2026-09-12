"""L-8 (FRENTE L) · justificación DdA con nota de proporcionalidad micro/autónomo.

CCN-STIC 801 sec 4.2 · additive · NO altera el determinismo de aplicabilidad
(la medida sigue siendo no aplicable por categoría · solo enriquece el texto).
"""
from __future__ import annotations

from backend.app.motors.m01_categorization.aplicabilidad import (
    medidas_no_aplicables,
)
from backend.app.motors.m03_dda.templates import render_no_aplica_justification

# Q1 · la firma cambió: el motivo ya no se deduce de `categoria_minima`, se toma
# de la misma tabla que decide la exclusión. op.acc.3 es de eje dimensión, así
# que se pide su motivo REAL para un sistema BASICA con las dimensiones en BAJO.
_NIVELES_BASICA = {"D": "BAJO", "I": "BAJO", "C": "BAJO", "A": "BAJO", "T": "BAJO"}


def _args():
    motivo = medidas_no_aplicables("BASICA", _NIVELES_BASICA)["op.acc.3"]
    return dict(
        codigo="op.acc.3",
        nombre="Segregación de funciones",
        system_category="BASICA",
        motivo=motivo,
    )


def test_l8_micro_adds_proportionality_note():
    out = render_no_aplica_justification(**_args(), empresa_size="micro")
    assert "proporcionalidad" in out
    assert "CCN-STIC 801 sec 4.2" in out


def test_l8_autonomo_alias_adds_note():
    out = render_no_aplica_justification(**_args(), empresa_size="autonomo")
    assert "CCN-STIC 801 sec 4.2" in out


def test_l8_non_micro_unchanged_backward_compat():
    # sin empresa_size o no-micro → salida idéntica al template base (sin nota)
    base = render_no_aplica_justification(**_args())
    big = render_no_aplica_justification(**_args(), empresa_size="grande")
    assert base == big
    assert "proporcionalidad" not in base
    # el determinismo de aplicabilidad no cambia: el texto base sigue presente
    assert "op.acc.3" in base and "no resulta de aplicación" in base
