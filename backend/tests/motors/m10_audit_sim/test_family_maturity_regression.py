"""Regresión BUG-04 (audit 2026-06-13): el nivel de madurez POR FAMILIA quedaba
siempre 'L0' (el default no se recalculaba) mientras el global daba L3.

Guarda: una familia con medidas conformes (L3) debe reportar nivel != 'L0'.
"""
from types import SimpleNamespace

from backend.app.motors.m10_audit_sim.audit_simulator import AuditSimulatorService


def _f(fam, evaluacion, nivel):
    return SimpleNamespace(measure_family=fam, evaluacion=evaluacion, nivel_madurez=nivel)


def test_family_nivel_is_computed_not_default_l0():
    findings = [
        _f("org", "conforme", "L3"),
        _f("org", "conforme", "L3"),
        _f("op.acc", "no_conforme_mayor", "L0"),
        _f("op.acc", "conforme", "L3"),
    ]
    res = AuditSimulatorService._scores_by_family(findings)
    # familia totalmente conforme -> nivel L3 (no el default L0)
    assert res["org"]["nivel"] == "L3", res["org"]
    # familia mixta L0+L3 -> media redondeada L2 (no queda en L0 por defecto)
    assert res["op.acc"]["nivel"] in ("L1", "L2"), res["op.acc"]
    # ninguna familia con medidas evaluadas debe quedar en L0 si tiene conformes
    assert res["org"]["nivel"] != "L0"


def test_family_no_temp_keys_leak():
    findings = [_f("mp.if", "conforme", "L3")]
    res = AuditSimulatorService._scores_by_family(findings)
    assert "_nivel_sum" not in res["mp.if"]
    assert "_nivel_n" not in res["mp.if"]
