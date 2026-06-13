"""Tests Diagnostic Gap Engine · R1 INVIOLABLE deterministic decisions.

Verifica:
- Detectors son pure functions sobre CloudResource list
- Detección NO usa LLM (decisión binaria)
- Decisión idéntica con input idéntico
- LLM enrichment SOLO renderiza explanation_es desde template
"""
from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any


from backend.app.motors.m_cloud_connectors import (
    RULE_CATALOG,
    GapFinding,
    list_supported_measures,
)
from backend.app.motors.m_cloud_connectors.diagnostic_gap_engine import (
    DiagnosticGapEngine,
)
from backend.app.motors.m_cloud_connectors.gap_rules import (
    detect_excess_privileged_users,
    detect_inventory_coverage,
    detect_logging_disabled,
    detect_log_retention_insufficient,
    detect_ntp_not_synced,
    detect_no_backup_strategy,
    detect_public_buckets,
    detect_unencrypted_storage,
    detect_users_without_mfa,
)


def _r(
    *,
    resource_type: str,
    external_id: str | None = None,
    name: str | None = None,
    **attrs: Any,
) -> SimpleNamespace:
    """Factory de CloudResource-like (SimpleNamespace para pure tests)."""
    return SimpleNamespace(
        resource_type=resource_type,
        resource_external_id=external_id or str(uuid.uuid4()),
        resource_name=name or external_id or "unnamed",
        attributes=attrs,
    )


# ============================================================
# R1 verify: detectors son PURE functions
# ============================================================


def test_detector_mfa_pure_function_no_side_effects():
    """detect_users_without_mfa NO toca DB · NO llama LLM · 100% pura."""
    resources = [
        _r(resource_type="identity.user", mfa_enabled=True, name="ok"),
        _r(resource_type="identity.user", mfa_enabled=False, name="bad1"),
        _r(resource_type="identity.user", mfa_enabled=False, name="bad2"),
    ]
    f1 = detect_users_without_mfa(resources)
    f2 = detect_users_without_mfa(resources)

    assert len(f1) == 1
    assert f1[0].ens_measure_code == "op.acc.6"
    assert f1[0].severity == "critical"
    assert f1[0].raw_evidence["users_no_mfa_count"] == 2

    # Determinismo · misma input misma output
    assert f1[0].title == f2[0].title
    assert f1[0].raw_evidence == f2[0].raw_evidence


def test_detector_mfa_empty_when_all_have_mfa():
    resources = [
        _r(resource_type="identity.user", mfa_enabled=True, name="a"),
        _r(resource_type="identity.user", mfa_enabled=True, name="b"),
    ]
    assert detect_users_without_mfa(resources) == []


# ============================================================
# #1 op.exp.8 · retención ≥12m + sincronización NTP (detector real)
# ============================================================


def test_op_exp_8_retention_gap_when_logging_on_but_short():
    resources = [
        _r(resource_type="asset.storage", logging_enabled=True, log_retention_days=90),
    ]
    findings = detect_log_retention_insufficient(resources)
    assert len(findings) == 1
    assert findings[0].ens_measure_code == "op.exp.8"
    assert findings[0].severity == "high"
    assert findings[0].raw_evidence["max_retention_days_detected"] == 90


def test_op_exp_8_retention_ok_when_12m_plus():
    resources = [
        _r(resource_type="asset.storage", logging_enabled=True, log_retention_days=400),
    ]
    assert detect_log_retention_insufficient(resources) == []


def test_op_exp_8_retention_no_double_flag_when_logging_off():
    # Sin logging activo lo cubre detect_logging_disabled · NO se duplica aquí
    resources = [_r(resource_type="asset.storage", logging_enabled=False)]
    assert detect_log_retention_insufficient(resources) == []


def test_op_exp_8_retention_gap_when_unset():
    # logging on pero retención no reportada → no verificada → gap (max=0)
    resources = [_r(resource_type="asset.storage", logging_enabled=True)]
    findings = detect_log_retention_insufficient(resources)
    assert len(findings) == 1
    assert findings[0].raw_evidence["max_retention_days_detected"] == 0


def test_op_exp_8_ntp_gap_when_no_sync():
    resources = [_r(resource_type="asset.host", name="srv1")]
    findings = detect_ntp_not_synced(resources)
    assert len(findings) == 1
    assert findings[0].ens_measure_code == "op.exp.8"
    assert findings[0].severity == "medium"


def test_op_exp_8_ntp_ok_when_synced():
    resources = [_r(resource_type="asset.host", ntp_enabled=True)]
    assert detect_ntp_not_synced(resources) == []


def test_op_exp_8_ntp_no_finding_when_no_cloud_assets():
    assert detect_ntp_not_synced([]) == []
    assert detect_ntp_not_synced([_r(resource_type="identity.user")]) == []


def test_detector_excess_privileged_under_threshold_no_finding():
    """6 users · 1 privileged = 16% · bajo threshold 20% · sin finding."""
    resources = [
        _r(resource_type="identity.user", is_privileged=False) for _ in range(5)
    ] + [_r(resource_type="identity.user", is_privileged=True)]
    findings = detect_excess_privileged_users(resources)
    assert findings == []  # 1/6 = 16% < 20% threshold


def test_detector_excess_privileged_above_threshold_emits():
    """5 users · 2 privileged = 40% · emite finding."""
    resources = [
        _r(resource_type="identity.user", is_privileged=False) for _ in range(3)
    ] + [
        _r(resource_type="identity.user", is_privileged=True) for _ in range(2)
    ]
    findings = detect_excess_privileged_users(resources)
    assert len(findings) == 1
    assert findings[0].ens_measure_code == "op.acc.2"
    assert findings[0].severity == "high"


def test_detector_excess_privileged_too_few_users_no_finding():
    """<5 usuarios totales · no se evalúa privilegio (signal débil)."""
    resources = [
        _r(resource_type="identity.user", is_privileged=True),
        _r(resource_type="identity.user", is_privileged=True),
    ]
    assert detect_excess_privileged_users(resources) == []


def test_detector_inventory_empty_emits_documental_gap():
    findings = detect_inventory_coverage([])
    assert len(findings) == 1
    assert findings[0].ens_measure_code == "op.exp.1"
    assert findings[0].gap_type == "documental"


def test_detector_inventory_with_assets_no_gap():
    resources = [_r(resource_type="asset.repo", name="my-repo")]
    assert detect_inventory_coverage(resources) == []


def test_detector_unencrypted_storage_emits_critical():
    resources = [
        _r(resource_type="asset.bucket", encrypted_at_rest=True, name="ok"),
        _r(resource_type="asset.bucket", encrypted_at_rest=False, name="bad"),
    ]
    findings = detect_unencrypted_storage(resources)
    assert len(findings) == 1
    assert findings[0].severity == "critical"
    assert findings[0].ens_measure_code == "mp.si.2"


def test_detector_public_buckets_emits_critical():
    resources = [
        _r(resource_type="asset.bucket", public_access=True, name="public-1"),
    ]
    findings = detect_public_buckets(resources)
    assert len(findings) == 1
    assert findings[0].severity == "critical"
    assert findings[0].ens_measure_code == "mp.s.2"


def test_detector_logging_disabled_when_no_log_enabled():
    resources = [
        _r(resource_type="asset.bucket", logging_enabled=False),
    ]
    findings = detect_logging_disabled(resources)
    assert len(findings) == 1
    assert findings[0].ens_measure_code == "op.exp.8"


def test_detector_logging_no_gap_when_at_least_one_enabled():
    resources = [
        _r(resource_type="asset.bucket", logging_enabled=False),
        _r(resource_type="asset.storage", logging_enabled=True),
    ]
    assert detect_logging_disabled(resources) == []


def test_detector_no_backup_when_no_storage_at_all_no_finding():
    """Sin storage en el inventario · no se evalúa mp.info.6 desde cloud."""
    resources = [_r(resource_type="identity.user", mfa_enabled=True)]
    assert detect_no_backup_strategy(resources) == []


def test_detector_no_backup_strategy_when_storage_without_backup():
    resources = [
        _r(resource_type="asset.bucket", backup_enabled=False),
    ]
    findings = detect_no_backup_strategy(resources)
    assert len(findings) == 1
    assert findings[0].ens_measure_code == "mp.info.6"


# ============================================================
# R1 LLM enrichment SOLO explanation_es
# ============================================================


def test_engine_render_explanation_no_llm_pure_template():
    """Engine._render_explanation usa Python format · NO LLM."""
    engine = DiagnosticGapEngine(db=None)  # type: ignore[arg-type]
    finding = GapFinding(
        ens_measure_code="op.acc.6",
        severity="critical",
        gap_type="structural",
        title="3 users no MFA",
        suggested_action="Activar MFA",
        explanation_es_template="Hay {n_users_no_mfa} sin MFA.",
        raw_evidence={"users_no_mfa_count": 3},
    )
    rendered = engine._render_explanation(finding)
    assert "3" in rendered
    assert "MFA" in rendered


def test_engine_render_explanation_fallback_on_missing_placeholder():
    """Si template tiene placeholder no presente en raw_evidence · fallback OK."""
    engine = DiagnosticGapEngine(db=None)  # type: ignore[arg-type]
    finding = GapFinding(
        ens_measure_code="custom",
        severity="low",
        gap_type="documental",
        title="X",
        suggested_action="Y",
        explanation_es_template="Algo con {placeholder_inexistente}.",
        raw_evidence={},
    )
    rendered = engine._render_explanation(finding)
    # Fallback: NO formatea · devuelve template tal cual SIN romper pipeline
    assert "placeholder_inexistente" in rendered


# ============================================================
# Catalog meta tests
# ============================================================


def test_supported_measures_includes_nucleares():
    measures = list_supported_measures()
    assert "op.acc.6" in measures
    assert "mp.si.2" in measures
    assert "op.exp.1" in measures
    assert "op.exp.8" in measures
    assert "org.1" in measures


def test_rule_catalog_all_rules_have_unique_id():
    ids = [r.rule_id for r in RULE_CATALOG]
    assert len(ids) == len(set(ids))


def test_rule_catalog_all_rules_have_canonical_ens_measure_code():
    """ENS measure codes son del Anexo II · formato sólido (motor.cap.num)."""
    import re
    pattern = re.compile(r"^[a-z]+\.[a-z]+(\.[0-9]+)?$|^[a-z]+\.[0-9]+$")
    for rule in RULE_CATALOG:
        assert pattern.match(rule.ens_measure_code), (
            f"rule {rule.rule_id} ens_measure_code "
            f"{rule.ens_measure_code!r} no canónico"
        )
