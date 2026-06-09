"""L-8 (FRENTE L) · justificación DdA con nota de proporcionalidad micro/autónomo.

CCN-STIC 801 sec 4.2 · additive · NO altera el determinismo de aplicabilidad
(la medida sigue siendo no aplicable por categoría · solo enriquece el texto).
"""
from __future__ import annotations

from backend.app.motors.m03_dda.templates import render_no_aplica_justification


def _args():
    return dict(
        codigo="op.acc.3",
        nombre="Segregación de funciones",
        cat_minima="MEDIA",
        system_category="BASICA",
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
