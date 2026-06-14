"""Tests for M27 route + submission state machines and invariants."""
import pytest

from backend.app.motors.m27_conformity import service
from backend.app.motors.m27_conformity.route_machine import (
    InvalidRouteTransitionError,
    RouteState,
    RouteType,
    can_transition,
    transition,
)
from backend.app.motors.m27_conformity.submission_machine import (
    InvalidSubmissionTransitionError,
    SubmissionState,
    can_transition as sub_can_transition,
    transition as sub_transition,
)


class TestRouteStateMachine:
    def test_initial_pending_to_locked_ok(self):
        assert can_transition(RouteState.ROUTE_PENDING, RouteState.ROUTE_LOCKED)

    def test_locked_to_declaration_only_with_declaration(self):
        assert can_transition(
            RouteState.ROUTE_LOCKED, RouteState.DECLARATION_IN_PROGRESS,
            route_type=RouteType.DECLARATION,
        )

    def test_locked_to_declaration_blocked_with_certification(self):
        assert not can_transition(
            RouteState.ROUTE_LOCKED, RouteState.DECLARATION_IN_PROGRESS,
            route_type=RouteType.CERTIFICATION,
        )

    def test_terminal_expired_has_no_outgoing(self):
        for s in RouteState:
            assert not can_transition(RouteState.EXPIRED, s)

    def test_active_can_renew_or_expire(self):
        assert can_transition(RouteState.ACTIVE, RouteState.RENEWAL_DUE)
        assert can_transition(RouteState.ACTIVE, RouteState.EXPIRED)

    def test_invalid_transition_raises(self):
        with pytest.raises(InvalidRouteTransitionError):
            transition(RouteState.ROUTE_PENDING, RouteState.ACTIVE)


class TestSubmissionStateMachine:
    def test_draft_to_generated(self):
        assert sub_can_transition(SubmissionState.DRAFT, SubmissionState.GENERATED)

    def test_submitted_to_under_review(self):
        assert sub_can_transition(SubmissionState.SUBMITTED, SubmissionState.UNDER_REVIEW)

    def test_completed_is_terminal(self):
        for s in SubmissionState:
            assert not sub_can_transition(SubmissionState.COMPLETED, s)

    def test_invalid_transition_raises(self):
        with pytest.raises(InvalidSubmissionTransitionError):
            sub_transition(SubmissionState.DRAFT, SubmissionState.COMPLETED)


class TestInvariants:
    def test_no_violations_for_empty_project(self):
        snap = {"project_phase": 0, "route": None, "overlays": [], "submissions": [], "renewals": []}
        assert service.check_invariants(snap) == []

    def test_phase1_without_route_violates(self):
        snap = {"project_phase": 1, "route": None, "overlays": [], "submissions": [], "renewals": []}
        assert "PROJECT_HAS_ROUTE_FROM_PHASE_1" in service.check_invariants(snap)

    def test_two_primary_overlays_violate(self):
        snap = {
            "project_phase": 1,
            "route": {"state": "ACTIVE"},
            "overlays": [{"is_primary": True}, {"is_primary": True}],
            "submissions": [], "renewals": [],
        }
        assert "SINGLE_ACTIVE_OVERLAY_PER_PROJECT" in service.check_invariants(snap)

    def test_submitted_without_payload_violates(self):
        snap = {
            "project_phase": 1, "route": {"state": "ACTIVE"}, "overlays": [],
            "submissions": [{"state": "SUBMITTED", "payload_present": False}],
            "renewals": [],
        }
        assert "NO_SUBMITTED_WITHOUT_PAYLOAD" in service.check_invariants(snap)

    def test_completed_without_proof_violates(self):
        snap = {
            "project_phase": 1, "route": {"state": "ACTIVE"}, "overlays": [],
            "submissions": [{"state": "COMPLETED", "payload_present": True, "proof_present": False, "justification": ""}],
            "renewals": [],
        }
        assert "NO_COMPLETED_WITHOUT_PROOF_OR_JUSTIFICATION" in service.check_invariants(snap)


class TestDeclaration:
    def test_declaration_generates_4_documents(self):
        import uuid
        decl = service.generate_declaration(uuid.uuid4(), "marcos")
        assert len(decl["documents"]) == 4
        assert decl["documents"] == ["E-041", "E-042", "E-043", "E-044"]


class TestRenewalClock:
    def test_state_t_180_when_far(self):
        from datetime import date, timedelta
        d = date.today() + timedelta(days=200)
        assert service.compute_renewal_state(d)["state"] == "T-180"

    def test_state_lapsed_in_past(self):
        from datetime import date, timedelta
        d = date.today() - timedelta(days=5)
        assert service.compute_renewal_state(d)["state"] == "LAPSED"

    def test_state_due_today(self):
        from datetime import date
        assert service.compute_renewal_state(date.today())["state"] == "DUE"

    def test_intermediate_windows_no_off_by_one(self):
        """Regresión batch2: la cascada de umbrales no debe desplazarse (antes
        delta>120 devolvía 'T-180' duplicado y corría cada ventana inferior)."""
        from datetime import date, timedelta

        def st(days: int) -> str:
            return service.compute_renewal_state(
                date.today() + timedelta(days=days)
            )["state"]

        assert st(150) == "T-120"
        assert st(100) == "T-90"
        assert st(70) == "T-60"
        assert st(45) == "T-30"
        assert st(15) == "T-30"


class TestPceOverlay:
    def test_detects_pce_pyme_for_basica_generic(self):
        out = service.detect_overlay("generico", "BASICA")
        assert out["overlay_code"] == "PCE-PYME"

    def test_detects_pce_salud(self):
        out = service.detect_overlay("sanidad_privada", "MEDIA")
        assert out["overlay_code"] == "PCE-SALUD"

    def test_overlay_validation_rejects_below_min(self):
        out = service.validate_overlay("PCE-AAPP-LOCAL", "BASICA")
        assert out["valid"] is False

    def test_overlay_validation_accepts(self):
        out = service.validate_overlay("PCE-PYME", "BASICA")
        assert out["valid"] is True
