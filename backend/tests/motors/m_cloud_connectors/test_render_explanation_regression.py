"""Regresión BUG-05 (audit 2026-06-13): el Diagnostic Gap Engine CRASHEABA
(`TypeError: got multiple values for keyword argument 'n_privileged'`) al renderizar
la explicación del hallazgo op.acc.2 (exceso de privilegiados), porque su raw_evidence
ya contiene n_privileged/n_total/pct_privileged y el código los pasaba TAMBIÉN como
kwargs explícitos a str.format(); el except no capturaba TypeError → caía todo el
pipeline de /cloud-diagnosis/run.

Guarda: render de op.acc.2 (y mp.si.2/mp.s.2) NO crashea y rinde valores.
"""
from types import SimpleNamespace

from backend.app.motors.m_cloud_connectors.diagnostic_gap_engine import DiagnosticGapEngine
from backend.app.motors.m_cloud_connectors.gap_rules import (
    detect_excess_privileged_users,
    detect_unencrypted_storage,
    detect_public_buckets,
)


def _res(rt, attrs, i=0):
    return SimpleNamespace(resource_type=rt, attributes=attrs,
                           resource_name=f"r{i}", resource_external_id=f"ext{i}")


def test_render_op_acc_2_no_crash():
    # 5 identidades, 2 privilegiadas (40% > 20%) -> emite op.acc.2
    resources = [_res("identity.user", {"is_privileged": i < 2}, i) for i in range(5)]
    findings = detect_excess_privileged_users(resources)
    assert findings, "debe emitir op.acc.2"
    eng = DiagnosticGapEngine(None)
    out = eng._render_explanation(findings[0])  # antes: TypeError
    assert isinstance(out, str) and out
    assert "2" in out  # n_privileged renderizado
    assert "5" in out  # n_total renderizado
    assert "{" not in out  # sin placeholders sin sustituir


def test_render_unencrypted_and_public_no_crash():
    eng = DiagnosticGapEngine(None)
    f1 = detect_unencrypted_storage([_res("asset.bucket", {"encrypted_at_rest": False})])
    f2 = detect_public_buckets([_res("asset.bucket", {"public_access": True})])
    for f in (f1[0], f2[0]):
        out = eng._render_explanation(f)
        assert isinstance(out, str) and out and "{" not in out
