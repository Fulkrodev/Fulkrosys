"""Audit accompaniment state machine canonical · Sesión 3B-4 Ejecutable 7.5.

Validated via web search CCN-STIC-808 BÁSICO + CCN-STIC-809 + CCN-CERT IC-01/19 +
CCN-CERT IC-02/20 jurisprudencia ENS RD 311/2022 cycle real-world.

Pattern #18 state machine canonical reuse (corrective_loop_service Ejecutable 5
reference). Branch decision per project.categoria_objetivo:
- BASICA → 7 states (autodeclaración · NO ENAC · incl. comunicación al CCN)
- MEDIA/ALTA → 11 states unified (ENAC certificación + biannual renewal)
"""
from __future__ import annotations


# ════════════════════════════════════════════════════════════════════════
# BÁSICO branch · 7 states (autodeclaración · NO ENAC · comunicación CCN/AMPARO)
# ════════════════════════════════════════════════════════════════════════

STATE_BASICO_NOT_STARTED = "not_started"
STATE_BASICO_DECLARATION_DRAFTED = "declaration_drafted"
STATE_BASICO_DECLARATION_SIGNED = "declaration_signed"
STATE_BASICO_DECLARATION_PUBLISHED = "declaration_published"
# #3 Ola 7 · comunicación de la Declaración al CCN (AMPARO) · TRAS publicar,
# ANTES de la revisión periódica. AMPARO no tiene API pública de terceros → es
# registro de constancia: Marcos comunica por el canal oficial y el sistema
# archiva el acuse + deja el rastro trazable (estado + audit_log + artefacto).
STATE_BASICO_CCN_COMMUNICATED = "ccn_communicated"
STATE_BASICO_PERIODIC_REVIEW_SCHEDULED = "periodic_review_scheduled"
STATE_BASICO_COMPLETED = "completed"

BASICO_STATES: tuple[str, ...] = (
    STATE_BASICO_NOT_STARTED,
    STATE_BASICO_DECLARATION_DRAFTED,
    STATE_BASICO_DECLARATION_SIGNED,
    STATE_BASICO_DECLARATION_PUBLISHED,
    STATE_BASICO_CCN_COMMUNICATED,
    STATE_BASICO_PERIODIC_REVIEW_SCHEDULED,
    STATE_BASICO_COMPLETED,
)

BASICO_TRANSITIONS: dict[str, set[str]] = {
    STATE_BASICO_NOT_STARTED: {STATE_BASICO_DECLARATION_DRAFTED},
    STATE_BASICO_DECLARATION_DRAFTED: {STATE_BASICO_DECLARATION_SIGNED},
    STATE_BASICO_DECLARATION_SIGNED: {STATE_BASICO_DECLARATION_PUBLISHED},
    STATE_BASICO_DECLARATION_PUBLISHED: {STATE_BASICO_CCN_COMMUNICATED},
    STATE_BASICO_CCN_COMMUNICATED: {STATE_BASICO_PERIODIC_REVIEW_SCHEDULED},
    STATE_BASICO_PERIODIC_REVIEW_SCHEDULED: {STATE_BASICO_COMPLETED},
    STATE_BASICO_COMPLETED: set(),
}


# ════════════════════════════════════════════════════════════════════════
# MEDIO/ALTO branch · 11 states unified (ENAC certificación + biannual)
# ════════════════════════════════════════════════════════════════════════

STATE_MA_NOT_STARTED = "not_started"
STATE_MA_PREPARATION = "preparation"
STATE_MA_DOCS_COLLECTED = "docs_collected"
STATE_MA_INTERNAL_AUDIT_SCHEDULED = "internal_audit_scheduled"
STATE_MA_INTERNAL_AUDIT_COMPLETED = "internal_audit_completed"
STATE_MA_ENAC_AUDIT_SCHEDULED = "enac_audit_scheduled"
STATE_MA_ENAC_AUDIT_IN_PROGRESS = "enac_audit_in_progress"
STATE_MA_ENAC_FINDINGS_RESOLUTION = "enac_findings_resolution"
STATE_MA_ENAC_AUDIT_PASSED = "enac_audit_passed"
STATE_MA_CERTIFICATE_ISSUED = "certificate_issued"
STATE_MA_BIANNUAL_RENEWAL_SCHEDULED = "biannual_renewal_scheduled"

MEDIO_ALTO_STATES: tuple[str, ...] = (
    STATE_MA_NOT_STARTED,
    STATE_MA_PREPARATION,
    STATE_MA_DOCS_COLLECTED,
    STATE_MA_INTERNAL_AUDIT_SCHEDULED,
    STATE_MA_INTERNAL_AUDIT_COMPLETED,
    STATE_MA_ENAC_AUDIT_SCHEDULED,
    STATE_MA_ENAC_AUDIT_IN_PROGRESS,
    STATE_MA_ENAC_FINDINGS_RESOLUTION,
    STATE_MA_ENAC_AUDIT_PASSED,
    STATE_MA_CERTIFICATE_ISSUED,
    STATE_MA_BIANNUAL_RENEWAL_SCHEDULED,
)

MEDIO_ALTO_TRANSITIONS: dict[str, set[str]] = {
    STATE_MA_NOT_STARTED: {STATE_MA_PREPARATION},
    STATE_MA_PREPARATION: {STATE_MA_DOCS_COLLECTED},
    STATE_MA_DOCS_COLLECTED: {STATE_MA_INTERNAL_AUDIT_SCHEDULED},
    STATE_MA_INTERNAL_AUDIT_SCHEDULED: {STATE_MA_INTERNAL_AUDIT_COMPLETED},
    STATE_MA_INTERNAL_AUDIT_COMPLETED: {STATE_MA_ENAC_AUDIT_SCHEDULED},
    STATE_MA_ENAC_AUDIT_SCHEDULED: {STATE_MA_ENAC_AUDIT_IN_PROGRESS},
    STATE_MA_ENAC_AUDIT_IN_PROGRESS: {STATE_MA_ENAC_FINDINGS_RESOLUTION, STATE_MA_ENAC_AUDIT_PASSED},
    STATE_MA_ENAC_FINDINGS_RESOLUTION: {STATE_MA_ENAC_AUDIT_PASSED},
    STATE_MA_ENAC_AUDIT_PASSED: {STATE_MA_CERTIFICATE_ISSUED},
    STATE_MA_CERTIFICATE_ISSUED: {STATE_MA_BIANNUAL_RENEWAL_SCHEDULED},
    STATE_MA_BIANNUAL_RENEWAL_SCHEDULED: {STATE_MA_PREPARATION},
}


# ════════════════════════════════════════════════════════════════════════
# Branch selector + helpers
# ════════════════════════════════════════════════════════════════════════

CATEGORY_BRANCH_BASICO = "BASICO"
CATEGORY_BRANCH_MEDIO_ALTO = "MEDIO_ALTO"


def resolve_category_branch(categoria_objetivo: str | None) -> str:
    """Map project.categoria_objetivo → state machine branch.

    BASICA → BASICO branch (7 states)
    MEDIA · ALTA → MEDIO_ALTO branch (11 states unified)
    None / unknown → BASICO default (conservative · single autodeclaración)
    """
    if not categoria_objetivo:
        return CATEGORY_BRANCH_BASICO
    cat = categoria_objetivo.upper()
    if cat in {"MEDIA", "ALTA"}:
        return CATEGORY_BRANCH_MEDIO_ALTO
    return CATEGORY_BRANCH_BASICO


def get_transitions_for_branch(branch: str) -> dict[str, set[str]]:
    """Return VALID_TRANSITIONS dict for branch."""
    if branch == CATEGORY_BRANCH_MEDIO_ALTO:
        return MEDIO_ALTO_TRANSITIONS
    return BASICO_TRANSITIONS


def get_states_for_branch(branch: str) -> tuple[str, ...]:
    """Return ordered state tuple for branch."""
    if branch == CATEGORY_BRANCH_MEDIO_ALTO:
        return MEDIO_ALTO_STATES
    return BASICO_STATES


def get_initial_state(branch: str) -> str:
    """Return canonical initial state per branch (always not_started)."""
    return STATE_BASICO_NOT_STARTED


def is_terminal_state(branch: str, state: str) -> bool:
    """Check if state has NO outgoing transitions (cycle complete)."""
    transitions = get_transitions_for_branch(branch)
    return len(transitions.get(state, set())) == 0


# ════════════════════════════════════════════════════════════════════════
# audit_log canonical events
# ════════════════════════════════════════════════════════════════════════

ACCOMPANIMENT_STATE_ADVANCED = "accompaniment.state.advanced"
ACCOMPANIMENT_ARTIFACT_UPLOADED = "accompaniment.artifact.uploaded"
ACCOMPANIMENT_INVALID_TRANSITION = "accompaniment.state.invalid_transition"
ACCOMPANIMENT_TIMELINE_VIEWED = "accompaniment.timeline.viewed"
ACCOMPANIMENT_CYCLE_COMPLETED = "accompaniment.cycle.completed"

ACCOMPANIMENT_EVENT_TYPES: tuple[str, ...] = (
    ACCOMPANIMENT_STATE_ADVANCED,
    ACCOMPANIMENT_ARTIFACT_UPLOADED,
    ACCOMPANIMENT_INVALID_TRANSITION,
    ACCOMPANIMENT_TIMELINE_VIEWED,
    ACCOMPANIMENT_CYCLE_COMPLETED,
)


class InvalidAccompanimentTransition(ValueError):
    """Raised when attempting invalid state transition (canonical NO skip · NO back)."""
