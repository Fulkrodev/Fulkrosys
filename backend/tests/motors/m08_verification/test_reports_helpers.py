"""Tests para delta + heatmap + score (Checkpoint 3)."""
from __future__ import annotations

import pytest

from backend.app.motors.m08_verification.reports.delta_report import (
    compute_delta,
)
from backend.app.motors.m08_verification.reports.heatmap_generator import (
    ENS_73_MEASURES,
    generate_heatmap,
    heatmap_summary,
)
from backend.app.motors.m08_verification.reports.score_calculator import (
    calculate_score,
)


# ═══════════════════════════════════════════════════════════════════
# Delta report
# ═══════════════════════════════════════════════════════════════════

class TestDeltaReport:
    def _f(self, h, sev="medium", title="t"):
        return {"finding_hash": h, "severity": sev, "title": title}

    def test_empty_previous_all_new(self):
        d = compute_delta([], [self._f("h1"), self._f("h2")])
        assert len(d.new) == 2
        assert len(d.resolved) == 0
        assert len(d.persistent) == 0

    def test_empty_current_all_resolved(self):
        d = compute_delta([self._f("h1"), self._f("h2")], [])
        assert len(d.new) == 0
        assert len(d.resolved) == 2

    def test_persistent_findings_tracked(self):
        d = compute_delta(
            [self._f("h1", "high"), self._f("h2", "medium")],
            [self._f("h1", "high"), self._f("h2", "medium")],
        )
        assert len(d.persistent) == 2
        assert len(d.new) == 0
        assert len(d.resolved) == 0

    def test_severity_change_detected(self):
        d = compute_delta(
            [self._f("h1", "medium")],
            [self._f("h1", "critical")],
        )
        assert len(d.severity_changes) == 1
        assert d.severity_changes[0].from_sev == "medium"
        assert d.severity_changes[0].to_sev == "critical"

    def test_trend_mejorando_when_weight_drops_20pct(self):
        # prev: 3 crit = 12; curr: 1 crit = 4 (< 80% of 12)
        prev = [self._f(f"h{i}", "critical") for i in range(3)]
        curr = [self._f("h0", "critical")]
        d = compute_delta(prev, curr)
        assert d.overall_trend == "mejorando"

    def test_trend_empeorando_when_weight_rises_20pct(self):
        prev = [self._f("h1", "low")]
        curr = [self._f("h1", "low"), self._f("h2", "critical")]
        d = compute_delta(prev, curr)
        assert d.overall_trend == "empeorando"

    def test_trend_estable_when_same(self):
        prev = [self._f("h1", "medium")]
        curr = [self._f("h1", "medium")]
        d = compute_delta(prev, curr)
        assert d.overall_trend == "estable"


# ═══════════════════════════════════════════════════════════════════
# Heatmap generator
# ═══════════════════════════════════════════════════════════════════

class TestHeatmap:
    def test_ens_has_73_measures(self):
        assert len(ENS_73_MEASURES) == 73

    def test_all_cells_compliant_when_no_findings(self):
        cells = generate_heatmap([])
        statuses = {c.status for c in cells}
        assert statuses == {"compliant"}
        assert len(cells) == 73

    def test_high_finding_makes_cell_non_compliant(self):
        findings = [{
            "finding_hash": "h1",
            "severity": "high",
            "status": "open",
            "ens_primary_measure": "op.acc.6",
            "ens_measures": [],
        }]
        cells = generate_heatmap(findings)
        cell = next(c for c in cells if c.measure == "op.acc.6")
        assert cell.status == "non_compliant"
        assert cell.color == "rojo"

    def test_low_finding_makes_cell_partial(self):
        findings = [{
            "finding_hash": "h1", "severity": "low", "status": "open",
            "ens_primary_measure": "mp.info.1", "ens_measures": [],
        }]
        cells = generate_heatmap(findings)
        cell = next(c for c in cells if c.measure == "mp.info.1")
        assert cell.status == "partial"
        assert cell.color == "amarillo"

    def test_remediated_finding_does_not_affect_cell(self):
        findings = [{
            "finding_hash": "h1", "severity": "critical", "status": "remediated",
            "ens_primary_measure": "op.exp.5", "ens_measures": [],
        }]
        cells = generate_heatmap(findings)
        cell = next(c for c in cells if c.measure == "op.exp.5")
        assert cell.status == "compliant"

    def test_summary_totals_73(self):
        cells = generate_heatmap([])
        s = heatmap_summary(cells)
        assert s["total"] == 73
        assert s["compliant"] == 73


# ═══════════════════════════════════════════════════════════════════
# Score calculator
# ═══════════════════════════════════════════════════════════════════

class TestScoreCalculator:
    def test_clean_system_100(self):
        s = calculate_score([])
        assert s.score == 100
        assert s.level == "excelente"

    def test_one_critical_minus_15(self):
        f = {
            "severity": "critical", "status": "open",
            "zfp_gate5_classification": "confirmed",
        }
        s = calculate_score([f])
        assert s.score == 85

    def test_one_high_minus_8(self):
        f = {
            "severity": "high", "status": "open",
            "zfp_gate5_classification": "confirmed",
        }
        s = calculate_score([f])
        assert s.score == 92

    def test_all_severities_sum(self):
        findings = [
            {"severity": "critical", "status": "open", "zfp_gate5_classification": "confirmed"},
            {"severity": "high", "status": "open", "zfp_gate5_classification": "confirmed"},
            {"severity": "medium", "status": "open", "zfp_gate5_classification": "confirmed"},
            {"severity": "low", "status": "open", "zfp_gate5_classification": "confirmed"},
        ]
        s = calculate_score(findings)
        # 100 - 15 - 8 - 3 - 1 = 73
        assert s.score == 73

    def test_remediated_findings_ignored(self):
        findings = [
            {"severity": "critical", "status": "remediated", "zfp_gate5_classification": "confirmed"},
        ]
        s = calculate_score(findings)
        assert s.score == 100

    def test_needs_review_excluded(self):
        findings = [
            {"severity": "critical", "status": "open", "zfp_gate5_classification": "needs_review"},
        ]
        s = calculate_score(findings)
        assert s.score == 100

    def test_score_floor_zero(self):
        findings = [
            {"severity": "critical", "status": "open", "zfp_gate5_classification": "confirmed"}
            for _ in range(10)
        ]
        s = calculate_score(findings)
        assert s.score == 0

    def test_score_levels(self):
        assert calculate_score([{"severity": "low", "status": "open", "zfp_gate5_classification": "confirmed"}]).level == "excelente"
        high = [{"severity": "high", "status": "open", "zfp_gate5_classification": "confirmed"}] * 3
        assert calculate_score(high).level in ("aceptable", "mejorable")
