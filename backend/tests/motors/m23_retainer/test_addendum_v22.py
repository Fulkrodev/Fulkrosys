"""Tests for M23 retainer addendum v2.2 submodules."""
from datetime import date, timedelta

from backend.app.motors.m23_retainer.addendum_v22 import (
    DRIFT_DIMENSIONS,
    DRIFT_SEVERITIES,
    PROFILE_HOURS_PER_MONTH,
    RENEWAL_STATES,
    CapacityPlanner,
    ChangeIntake,
    DriftDetector,
    EvidenceFreshnessScheduler,
    IncidentLuciaAssist,
    ProviderLifecycle,
    RenewalClock,
    RetainerExit,
    RetainerOpsQueue,
)


class TestRetainerProfiles:
    def test_4_profiles(self):
        assert set(PROFILE_HOURS_PER_MONTH.keys()) == {"R_LITE", "R_STD", "R_PLUS", "R_CRITICAL"}

    def test_profile_hours_strict_increase(self):
        assert PROFILE_HOURS_PER_MONTH["R_LITE"] < PROFILE_HOURS_PER_MONTH["R_STD"]
        assert PROFILE_HOURS_PER_MONTH["R_STD"] < PROFILE_HOURS_PER_MONTH["R_PLUS"]
        assert PROFILE_HOURS_PER_MONTH["R_PLUS"] < PROFILE_HOURS_PER_MONTH["R_CRITICAL"]


class TestRenewalClock:
    def test_states_constant_has_9(self):
        assert len(RENEWAL_STATES) == 9

    def test_renewal_clock_state(self):
        target = date.today() + timedelta(days=200)
        assert RenewalClock.state_for(target) == "T-180"


class TestDriftDetector:
    def test_dimensions_count_10(self):
        assert len(DRIFT_DIMENSIONS) == 10

    def test_severities_count_4(self):
        assert len(DRIFT_SEVERITIES) == 4

    def test_health_score_high_when_low_drift(self):
        m = {d: "LOW" for d in DRIFT_DIMENSIONS}
        assert DriftDetector.health_score(m) == 100

    def test_health_score_drops_with_critical(self):
        m = {d: "LOW" for d in DRIFT_DIMENSIONS}
        m["evidence_freshness"] = "CRITICAL"
        assert DriftDetector.health_score(m) == 70


class TestCapacityPlanner:
    def test_total_assigned(self):
        assert CapacityPlanner.total_assigned(["R_LITE", "R_STD"]) == 24

    def test_alert_when_over_90pct(self):
        u = CapacityPlanner.utilization(["R_CRITICAL", "R_CRITICAL"], 100)
        assert u["alert"] is True
        assert u["utilization"] > 0.9


class TestProviderLifecycleAndOpsQueue:
    def test_provider_next_stage(self):
        assert ProviderLifecycle.next_stage("onboarding") == "operating"
        assert ProviderLifecycle.next_stage("closed") == "closed"

    def test_ops_queue_prioritizes_critical(self):
        items = [
            {"id": "a", "severity": "LOW", "sla_hours_remaining": 100, "affects_renewal": False},
            {"id": "b", "severity": "CRITICAL", "sla_hours_remaining": 4, "affects_renewal": True},
            {"id": "c", "severity": "MEDIUM", "sla_hours_remaining": 24, "affects_renewal": True},
        ]
        ordered = RetainerOpsQueue.prioritize(items)
        assert ordered[0]["id"] == "b"


class TestChangeIntakeAndOthers:
    def test_change_intake_returns_next_step(self):
        import uuid
        out = ChangeIntake.derive(uuid.uuid4(), "Migration", "marcos")
        assert "POST" in out["next_step"]

    def test_incident_lucia_required_for_high(self):
        import uuid
        out = IncidentLuciaAssist.package(uuid.uuid4(), "HIGH", [])
        assert out["lucia_export_required"] is True

    def test_evidence_freshness_returns_due(self):
        ev = [
            {"id": "1", "last_refresh_days": 500, "freshness_policy": "annual"},
            {"id": "2", "last_refresh_days": 10, "freshness_policy": "monthly"},
        ]
        due = EvidenceFreshnessScheduler.due_evidences(ev)
        assert len(due) == 1
        assert due[0]["id"] == "1"

    def test_retainer_exit_checklist(self):
        cl = RetainerExit.handover_checklist()
        assert len(cl) >= 5
