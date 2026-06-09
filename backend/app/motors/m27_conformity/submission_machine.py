"""Motor 27 — Submission State Machine (addendum v2.2 §7.7)."""
from __future__ import annotations

from enum import Enum


class SubmissionState(str, Enum):
    DRAFT = "DRAFT"
    GENERATED = "GENERATED"
    READY_FOR_SIGNATURE = "READY_FOR_SIGNATURE"
    READY_FOR_SUBMISSION = "READY_FOR_SUBMISSION"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    OBSERVED = "OBSERVED"
    CORRECTION_REQUIRED = "CORRECTION_REQUIRED"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"


_TRANSITIONS: dict[SubmissionState, set[SubmissionState]] = {
    SubmissionState.DRAFT: {SubmissionState.GENERATED, SubmissionState.WITHDRAWN},
    SubmissionState.GENERATED: {SubmissionState.READY_FOR_SIGNATURE, SubmissionState.WITHDRAWN},
    SubmissionState.READY_FOR_SIGNATURE: {SubmissionState.READY_FOR_SUBMISSION, SubmissionState.WITHDRAWN},
    SubmissionState.READY_FOR_SUBMISSION: {SubmissionState.SUBMITTED, SubmissionState.WITHDRAWN},
    SubmissionState.SUBMITTED: {SubmissionState.UNDER_REVIEW},
    SubmissionState.UNDER_REVIEW: {
        SubmissionState.OBSERVED, SubmissionState.CORRECTION_REQUIRED,
        SubmissionState.COMPLETED, SubmissionState.REJECTED,
    },
    SubmissionState.OBSERVED: {SubmissionState.CORRECTION_REQUIRED, SubmissionState.COMPLETED},
    SubmissionState.CORRECTION_REQUIRED: {SubmissionState.SUBMITTED, SubmissionState.WITHDRAWN},
}


TERMINAL_STATES = {SubmissionState.COMPLETED, SubmissionState.REJECTED, SubmissionState.WITHDRAWN}


class InvalidSubmissionTransitionError(Exception):
    """Transition not allowed by the submission state machine."""


def can_transition(from_state: SubmissionState, to_state: SubmissionState) -> bool:
    return to_state in _TRANSITIONS.get(from_state, set())


def transition(from_state: SubmissionState, to_state: SubmissionState) -> SubmissionState:
    if not can_transition(from_state, to_state):
        raise InvalidSubmissionTransitionError(
            f"Cannot transition submission from {from_state.value} to {to_state.value}"
        )
    return to_state


def allowed_next(from_state: SubmissionState) -> set[SubmissionState]:
    return set(_TRANSITIONS.get(from_state, set()))
