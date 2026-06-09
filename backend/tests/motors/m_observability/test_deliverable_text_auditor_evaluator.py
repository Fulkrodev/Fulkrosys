"""Tests deliverable_text_auditor evaluator skeleton · 1.E.1.B.3.D Path C-light.

Cubre:
  - skip path cuando actual_provider declined (capability_pending_build)
  - deterministic checks · key_phrases_required missing
  - deterministic checks · key_phrases_forbidden present unflagged
  - forbidden phrase OK si correctly flagged como issue
  - verdict_match check
  - happy path pass
  - ComplianceAlert shell: skip if all entries skipped
  - ComplianceAlert shell: create si pass_rate < threshold

NO real LLM calls · mock provider only.
"""
from __future__ import annotations

from typing import Any

import pytest

# Import evaluators package · side-effect register_evaluator
from backend.app.motors.m_observability import evaluators  # noqa: F401
from backend.app.motors.m_observability.eval_runner import (
    DatasetEvalReport,
    EntryEvalResult,
    _AGENT_EVALUATORS,
    maybe_create_regression_alert,
)
from backend.app.motors.m_observability.evaluators.deliverable_text_auditor_evaluator import (
    deliverable_text_auditor_evaluator,
)
from backend.app.motors.m_observability.golden_datasets_loader import (
    GoldenDatasetEntry,
    GoldenExpectedOutput,
    GoldenRubric,
)


pytestmark = pytest.mark.golden


def _entry(
    *,
    verdict: str | None = "PASS_AUDITOR_READY",
    required: list[str] | None = None,
    forbidden: list[str] | None = None,
) -> GoldenDatasetEntry:
    return GoldenDatasetEntry(
        id="dta-test-001",
        category="unit_test",
        input={"deliverable_text": "sample"},
        expected_output=GoldenExpectedOutput(
            verdict=verdict,
            key_phrases_required=required or [],
            key_phrases_forbidden=forbidden or [],
        ),
        rubric=GoldenRubric(),
    )


# ════════════════════════════════════════════════════════════════════
# Registry · evaluator registrado al importar package
# ════════════════════════════════════════════════════════════════════


def test_evaluator_registered_under_deliverable_text_auditor():
    """Side-effect: importing evaluators package registers evaluator."""
    assert "deliverable_text_auditor" in _AGENT_EVALUATORS


# ════════════════════════════════════════════════════════════════════
# Skip path · actual=None (capability_pending_build)
# ════════════════════════════════════════════════════════════════════


def test_evaluator_skips_when_actual_is_none():
    """actual=None → skipped=True con reason capability_pending_build."""
    entry = _entry()
    result = deliverable_text_auditor_evaluator(entry, None)
    assert result.skipped is True
    assert result.passed is False
    assert "capability pending build" in result.skip_reason.lower()
    assert "future-1.e.1.dossier-pack-10docs" in result.skip_reason.lower()


# ════════════════════════════════════════════════════════════════════
# Deterministic checks · key_phrases required/forbidden
# ════════════════════════════════════════════════════════════════════


def test_evaluator_required_missing_fail():
    """key_phrase_required ausente en actual → passed=False."""
    entry = _entry(
        verdict=None,  # no verdict check
        required=["mandatory_phrase", "another_required"],
    )
    actual: dict[str, Any] = {"text": "only contains mandatory_phrase nothing else"}
    result = deliverable_text_auditor_evaluator(entry, actual)
    assert result.passed is False
    assert "another_required" in result.required_missing
    assert "mandatory_phrase" not in result.required_missing


def test_evaluator_forbidden_present_unflagged_fail():
    """key_phrase_forbidden present sin flagged en issues → passed=False."""
    entry = _entry(
        verdict=None,
        forbidden=["se cumplirán las medidas aplicables"],
    )
    actual: dict[str, Any] = {
        "text": "Se cumplirán las medidas aplicables del Anexo II",
        "issues_critical": [],
        "issues_moderate": [],
    }
    result = deliverable_text_auditor_evaluator(entry, actual)
    assert result.passed is False
    assert "se cumplirán las medidas aplicables" in result.forbidden_present_unflagged


def test_evaluator_forbidden_correctly_flagged_passes():
    """forbidden phrase OK si auditor lo flagged en issues_critical/moderate."""
    entry = _entry(
        verdict=None,
        forbidden=["se cumplirán las medidas aplicables"],
    )
    actual: dict[str, Any] = {
        "text": "Se cumplirán las medidas aplicables del Anexo II (frase detected)",
        "issues_critical": [
            "Frase genérica 'Se cumplirán las medidas aplicables' detectada",
        ],
        "issues_moderate": [],
    }
    result = deliverable_text_auditor_evaluator(entry, actual)
    assert result.forbidden_present_unflagged == []
    assert result.passed is True


def test_evaluator_verdict_match_pass():
    """verdict_match True cuando actual.verdict == expected.verdict."""
    entry = _entry(verdict="PASS_AUDITOR_READY")
    actual = {"verdict": "PASS_AUDITOR_READY", "text": "sample"}
    result = deliverable_text_auditor_evaluator(entry, actual)
    assert result.verdict_match is True
    assert result.passed is True


def test_evaluator_verdict_mismatch_fails():
    """verdict_match False cuando actual.verdict != expected.verdict."""
    entry = _entry(verdict="PASS_AUDITOR_READY")
    actual = {"verdict": "FAIL_CRITICAL", "text": "sample"}
    result = deliverable_text_auditor_evaluator(entry, actual)
    assert result.verdict_match is False
    assert result.passed is False
    assert "verdict mismatch" in result.diff_summary.lower()


def test_evaluator_happy_path_full_pass():
    """All checks pass · verdict match + required present + no forbidden."""
    entry = _entry(
        verdict="PASS_AUDITOR_READY",
        required=["anexo ii", "responsable de seguridad"],
        forbidden=["se cumplirán"],
    )
    actual = {
        "verdict": "PASS_AUDITOR_READY",
        "text": (
            "Documento conforme al Anexo II RD 311/2022. "
            "Responsable de Seguridad asignado. Aplicabilidad documentada."
        ),
        "issues_critical": [],
        "issues_moderate": [],
    }
    result = deliverable_text_auditor_evaluator(entry, actual)
    assert result.passed is True
    assert result.verdict_match is True
    assert result.required_missing == []
    assert result.forbidden_present_unflagged == []
    assert result.diff_summary == "ok"
    assert result.actual_summary == {
        "verdict": "PASS_AUDITOR_READY",
        "issues_critical_count": 0,
    }


# ════════════════════════════════════════════════════════════════════
# ComplianceAlert integration shell
# ════════════════════════════════════════════════════════════════════


def test_alert_skipped_no_alert_created():
    """Si all entries skipped · NO alert (capability pending build)."""
    report = DatasetEvalReport(
        agent_name="deliverable_text_auditor",
        version="v1",
        total_entries=0,
        passed=0,
        failed=0,
        pass_rate=1.0,
        severity="ok",
        entries_in_dataset=10,
        entry_results=[
            EntryEvalResult(
                entry_id=f"dta-{i:03d}",
                category="ens_doa",
                passed=False,
                diff_summary="skipped · capability pending build",
                skipped=True,
                skip_reason="capability_pending_build",
            )
            for i in range(1, 11)
        ],
    )
    descriptor = maybe_create_regression_alert(report)
    assert descriptor is None


def test_alert_created_below_warn_threshold_medium_severity():
    """pass_rate 0.7 < 0.8 warn threshold · MEDIUM severity descriptor."""
    report = DatasetEvalReport(
        agent_name="deliverable_text_auditor",
        version="v1",
        total_entries=10,
        passed=7,
        failed=3,
        pass_rate=0.7,
        severity="warn",
        entries_in_dataset=10,
        entry_results=[
            EntryEvalResult(
                entry_id=f"dta-{i:03d}",
                category="ens_doa",
                passed=(i <= 7),
                diff_summary="ok" if i <= 7 else "fail",
            )
            for i in range(1, 11)
        ],
    )
    descriptor = maybe_create_regression_alert(report)
    assert descriptor is not None
    assert descriptor["severity"] == "MEDIUM"
    assert descriptor["norma"] == "INTERNAL_GOLDEN_EVAL"
    assert descriptor["metadata"]["pass_rate"] == 0.7
    assert len(descriptor["metadata"]["failed_entry_ids"]) == 3


def test_alert_created_below_alert_threshold_high_severity():
    """pass_rate 0.5 < 0.6 alert threshold · HIGH severity descriptor."""
    report = DatasetEvalReport(
        agent_name="deliverable_text_auditor",
        version="v1",
        total_entries=10,
        passed=5,
        failed=5,
        pass_rate=0.5,
        severity="alert",
        entries_in_dataset=10,
        entry_results=[
            EntryEvalResult(
                entry_id=f"dta-{i:03d}",
                category="ens_doa",
                passed=(i <= 5),
                diff_summary="ok" if i <= 5 else "fail",
            )
            for i in range(1, 11)
        ],
    )
    descriptor = maybe_create_regression_alert(report)
    assert descriptor is not None
    assert descriptor["severity"] == "HIGH"


def test_alert_factory_called_when_provided():
    """alert_factory dependency-injected callable invocada con descriptor."""
    captured: dict[str, Any] = {}

    def fake_factory(**kwargs: Any) -> None:
        captured.update(kwargs)

    report = DatasetEvalReport(
        agent_name="deliverable_text_auditor",
        version="v1",
        total_entries=2,
        passed=0,
        failed=2,
        pass_rate=0.0,
        severity="alert",
        entries_in_dataset=2,
        entry_results=[
            EntryEvalResult(
                entry_id="dta-001", category="x",
                passed=False, diff_summary="fail",
            ),
            EntryEvalResult(
                entry_id="dta-002", category="y",
                passed=False, diff_summary="fail",
            ),
        ],
    )
    descriptor = maybe_create_regression_alert(
        report, alert_factory=fake_factory,
    )
    assert descriptor is not None
    assert captured["severity"] == "HIGH"
    assert captured["norma"] == "INTERNAL_GOLDEN_EVAL"
    assert "dta-001" in captured["metadata"]["failed_entry_ids"]
    assert "dta-002" in captured["metadata"]["failed_entry_ids"]
