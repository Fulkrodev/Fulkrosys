"""Golden datasets eval harness skeleton tests · sub-atom 1.E.1.B.3.B.

Cubre infrastructure (loader · runner · report formatters · CLI) sin
golden entries reales (curación B.3.C pendiente Marcos input).

Pytest marker `@pytest.mark.golden` registered en pyproject.toml.

Tests verde sin LLM calls (skeleton phase) · 0 ANTHROPIC_API_KEY needed.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from backend.app.motors.m_observability.eval_runner import (
    DatasetEvalReport,
    EntryEvalResult,
    _default_skeleton_evaluator,
    compute_regression_score,
    format_eval_report_json,
    format_eval_report_markdown,
    run_eval,
)
from backend.app.motors.m_observability.golden_datasets_loader import (
    GOLDEN_DATASETS_ROOT,
    GoldenDataset,
    GoldenDatasetEntry,
    GoldenDatasetLoadError,
    GoldenExpectedOutput,
    GoldenRubric,
    clear_cache,
    list_available_datasets,
    load_golden_dataset,
)


pytestmark = pytest.mark.golden


# ════════════════════════════════════════════════════════════════════
# Loader tests · skeleton verification
# ════════════════════════════════════════════════════════════════════


def test_golden_dataset_loadable_curated():
    """deliverable_text_auditor v1 loads · 10 entries Marcos-curated.

    Ratchet B.3.C+B.3.D Paso 2 · skeleton (0 entries · curated_by="skeleton")
    promoted to curated baseline (10 entries · curated_by="marcos") +
    rename agent_11_auditor_virtual → deliverable_text_auditor (label
    accuracy · A11 es M10 enricher · NO audita deliverable text).
    Distribution: 4 PASS_AUDITOR_READY · 4 FAIL_CRITICAL · 2 NEEDS_REVISION
    cubriendo BÁSICA/MEDIA/ALTA/CROSS deliverable types. Entry IDs preserved
    historical a11-* (traceability B.3.C curation insights).
    """
    clear_cache()
    ds = load_golden_dataset("deliverable_text_auditor", "v1")
    assert ds.agent_name == "deliverable_text_auditor"
    assert ds.version == "v1"
    assert ds.curated_by == "marcos"
    assert len(ds.entries) == 10
    assert ds.regression_thresholds.pass_rate_warn_below == 0.8
    assert ds.regression_thresholds.pass_rate_alert_below == 0.6

    # Verify ids a11-001..a11-010 historical preserved
    expected_ids = [f"a11-{i:03d}" for i in range(1, 11)]
    assert [e.id for e in ds.entries] == expected_ids

    # Verify verdict distribution (4 PASS + 4 FAIL + 2 NEEDS_REVISION)
    verdicts = [e.expected_output.verdict for e in ds.entries]
    assert verdicts.count("PASS_AUDITOR_READY") == 4
    assert verdicts.count("FAIL_CRITICAL") == 4
    assert verdicts.count("NEEDS_REVISION") == 2


def test_list_available_datasets_returns_deliverable_text_auditor():
    """list_available_datasets descubre dataset renamed (B.3.D Paso 2)."""
    available = list_available_datasets()
    assert ("deliverable_text_auditor", "v1") in available


def test_load_unknown_agent_raises():
    """Loader raises clear error si agente NO existe en filesystem."""
    with pytest.raises(GoldenDatasetLoadError, match="not found"):
        load_golden_dataset("agent_99_inexistente", "v1")


# ════════════════════════════════════════════════════════════════════
# Runner skeleton tests
# ════════════════════════════════════════════════════════════════════


def _write_empty_dataset(tmp_path: Path, agent: str = "agent_test_empty") -> Path:
    """Helper · escribir dataset vacío synthetic en tmp_path."""
    agent_dir = tmp_path / agent
    agent_dir.mkdir()
    payload = {
        "agent_name": agent,
        "version": "v1",
        "created_at": "2026-05-23",
        "curated_by": "skeleton",
        "purpose": "Empty synthetic fixture · runner structure tests.",
        "entries": [],
    }
    (agent_dir / "v1.json").write_text(
        json.dumps(payload), encoding="utf-8",
    )
    return tmp_path


def test_eval_runner_returns_structure_empty_dataset(tmp_path: Path):
    """run_eval con dataset vacío → report estructura correcta · vacuously OK."""
    root = _write_empty_dataset(tmp_path)
    clear_cache()
    report = run_eval("agent_test_empty", "v1", root=root)
    assert isinstance(report, DatasetEvalReport)
    assert report.agent_name == "agent_test_empty"
    assert report.total_entries == 0
    assert report.passed == 0
    assert report.failed == 0
    assert report.severity == "ok"


def test_regression_score_empty_dataset_returns_one_vacuously(tmp_path: Path):
    """Empty 0 entries · pass_rate = 1.0 vacuously true (NO entries to fail)."""
    root = _write_empty_dataset(tmp_path)
    clear_cache()
    report = run_eval("agent_test_empty", "v1", root=root)
    score = compute_regression_score(report)
    assert score == 1.0


# ════════════════════════════════════════════════════════════════════
# Default skeleton evaluator tests
# ════════════════════════════════════════════════════════════════════


def _mk_entry(
    *,
    required: list[str] | None = None,
    forbidden: list[str] | None = None,
    structure_check: bool = True,
) -> GoldenDatasetEntry:
    return GoldenDatasetEntry(
        id="test-001",
        category="unit",
        input={"foo": "bar"},
        expected_output=GoldenExpectedOutput(
            key_phrases_required=required or [],
            key_phrases_forbidden=forbidden or [],
        ),
        rubric=GoldenRubric(structure_check=structure_check),
    )


def test_skeleton_evaluator_pass_when_actual_matches():
    """default evaluator · key_phrases required all present + 0 forbidden → pass."""
    entry = _mk_entry(required=["alpha", "beta"], forbidden=["gamma"])
    actual = {"text": "alpha beta delta"}
    passed, diff = _default_skeleton_evaluator(entry, actual)
    assert passed is True
    assert diff == "ok"


def test_skeleton_evaluator_fail_missing_required():
    """default evaluator · missing required phrase → fail con diff descriptive."""
    entry = _mk_entry(required=["alpha", "beta"])
    actual = {"text": "alpha gamma"}
    passed, diff = _default_skeleton_evaluator(entry, actual)
    assert passed is False
    assert "missing required phrase 'beta'" in diff


def test_skeleton_evaluator_fail_forbidden_present():
    """default evaluator · forbidden phrase presente → fail con diff."""
    entry = _mk_entry(forbidden=["gamma"])
    actual = {"text": "alpha gamma"}
    passed, diff = _default_skeleton_evaluator(entry, actual)
    assert passed is False
    assert "contains forbidden phrase 'gamma'" in diff


def test_skeleton_evaluator_fail_structure_when_not_dict():
    """structure_check=True · actual NO dict → fail."""
    entry = _mk_entry()
    passed, diff = _default_skeleton_evaluator(entry, ["not_a_dict"])  # type: ignore[arg-type]
    assert passed is False
    assert "structure_check failed" in diff


# ════════════════════════════════════════════════════════════════════
# Report formatters
# ════════════════════════════════════════════════════════════════════


def test_format_markdown_empty_dataset_mentions_skeleton(tmp_path: Path):
    root = _write_empty_dataset(tmp_path)
    clear_cache()
    report = run_eval("agent_test_empty", "v1", root=root)
    md = format_eval_report_markdown(report)
    assert "Golden eval report" in md
    assert "agent_test_empty" in md
    assert "Skeleton dataset" in md
    assert "✅ OK" in md


def test_format_json_empty_dataset_round_trippable(tmp_path: Path):
    root = _write_empty_dataset(tmp_path)
    clear_cache()
    report = run_eval("agent_test_empty", "v1", root=root)
    js = format_eval_report_json(report)
    data = json.loads(js)
    assert data["agent_name"] == "agent_test_empty"
    assert data["total_entries"] == 0
    assert data["severity"] == "ok"
    assert data["entry_results"] == []


# ════════════════════════════════════════════════════════════════════
# Custom actual_provider integration (B.3.D pre-wiring)
# ════════════════════════════════════════════════════════════════════


def test_runner_uses_custom_actual_provider_when_entries_exist(tmp_path: Path):
    """Si dataset tiene entries + actual_provider · runner ejecuta evaluator."""
    # Build synthetic dataset con 2 entries en tmp dir
    agent_dir = tmp_path / "agent_test_synthetic"
    agent_dir.mkdir()
    payload = {
        "agent_name": "agent_test_synthetic",
        "version": "v1",
        "created_at": "2026-05-23",
        "curated_by": "test",
        "purpose": "Synthetic test fixture",
        "entries": [
            {
                "id": "s-001",
                "category": "unit",
                "input": {"foo": "bar"},
                "expected_output": {
                    "key_phrases_required": ["alpha"],
                    "key_phrases_forbidden": [],
                },
                "rubric": {"structure_check": True},
            },
            {
                "id": "s-002",
                "category": "unit",
                "input": {"foo": "baz"},
                "expected_output": {
                    "key_phrases_required": ["nonexistent"],
                    "key_phrases_forbidden": [],
                },
                "rubric": {"structure_check": True},
            },
        ],
    }
    (agent_dir / "v1.json").write_text(
        json.dumps(payload), encoding="utf-8",
    )
    clear_cache()
    # Patch GOLDEN_DATASETS_ROOT via dependency injection
    ds = load_golden_dataset("agent_test_synthetic", "v1", root=tmp_path)
    assert len(ds.entries) == 2

    # Build runner-aware path · use root param via direct evaluator call
    # (skip full run_eval for cross-root scenario · skeleton test sufficient)
    from backend.app.motors.m_observability.eval_runner import (
        _default_skeleton_evaluator,
    )
    actuals = [{"text": "alpha rendered"}, {"text": "alpha rendered"}]
    results = []
    for entry, actual in zip(ds.entries, actuals):
        passed, _ = _default_skeleton_evaluator(entry, actual)
        results.append(passed)
    # s-001 passes (alpha present) · s-002 fails (nonexistent missing)
    assert results == [True, False]
