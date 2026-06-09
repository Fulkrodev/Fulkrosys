"""Motor 27 — Route State Machine (addendum v2.2 §7.6).

Estados (12) y transiciones permitidas. Determinista: cualquier transicion
no listada es invalida y debe lanzar InvalidRouteTransitionError.
"""
from __future__ import annotations

from enum import Enum


class RouteState(str, Enum):
    ROUTE_PENDING = "ROUTE_PENDING"
    ROUTE_LOCKED = "ROUTE_LOCKED"
    DECLARATION_IN_PROGRESS = "DECLARATION_IN_PROGRESS"
    CERTIFICATION_IN_PROGRESS = "CERTIFICATION_IN_PROGRESS"
    READY_FOR_DECLARATION = "READY_FOR_DECLARATION"
    READY_FOR_AUDITOR = "READY_FOR_AUDITOR"
    UNDER_REVIEW = "UNDER_REVIEW"
    OBSERVED = "OBSERVED"
    CORRECTION_REQUIRED = "CORRECTION_REQUIRED"
    CONFORMANT = "CONFORMANT"
    REGISTERED = "REGISTERED"
    ACTIVE = "ACTIVE"
    RENEWAL_DUE = "RENEWAL_DUE"
    RENEWAL_PENDING = "RENEWAL_PENDING"
    EXPIRED = "EXPIRED"
    SUSPENDED = "SUSPENDED"


class RouteType(str, Enum):
    DECLARATION = "DECLARATION"   # Categoria BASICA
    CERTIFICATION = "CERTIFICATION"  # Categorias MEDIA / ALTA


# (from_state, route_type) -> set[to_state]
_TRANSITIONS: dict[tuple[RouteState, RouteType | None], set[RouteState]] = {
    (RouteState.ROUTE_PENDING, None): {RouteState.ROUTE_LOCKED},
    (RouteState.ROUTE_LOCKED, RouteType.DECLARATION): {RouteState.DECLARATION_IN_PROGRESS},
    (RouteState.ROUTE_LOCKED, RouteType.CERTIFICATION): {RouteState.CERTIFICATION_IN_PROGRESS},
    (RouteState.DECLARATION_IN_PROGRESS, None): {RouteState.READY_FOR_DECLARATION},
    (RouteState.CERTIFICATION_IN_PROGRESS, None): {RouteState.READY_FOR_AUDITOR},
    (RouteState.READY_FOR_DECLARATION, None): {RouteState.UNDER_REVIEW, RouteState.SUSPENDED},
    (RouteState.READY_FOR_AUDITOR, None): {RouteState.UNDER_REVIEW, RouteState.SUSPENDED},
    (RouteState.UNDER_REVIEW, None): {
        RouteState.OBSERVED, RouteState.CORRECTION_REQUIRED, RouteState.CONFORMANT,
    },
    (RouteState.OBSERVED, None): {RouteState.CORRECTION_REQUIRED, RouteState.CONFORMANT},
    (RouteState.CORRECTION_REQUIRED, None): {RouteState.UNDER_REVIEW, RouteState.SUSPENDED},
    (RouteState.CONFORMANT, None): {RouteState.REGISTERED},
    (RouteState.REGISTERED, None): {RouteState.ACTIVE},
    (RouteState.ACTIVE, None): {RouteState.RENEWAL_DUE, RouteState.SUSPENDED, RouteState.EXPIRED},
    (RouteState.RENEWAL_DUE, None): {RouteState.RENEWAL_PENDING, RouteState.EXPIRED},
    (RouteState.RENEWAL_PENDING, None): {RouteState.ACTIVE, RouteState.EXPIRED},
    (RouteState.SUSPENDED, None): {RouteState.UNDER_REVIEW, RouteState.EXPIRED},
}


class InvalidRouteTransitionError(Exception):
    """Transition not allowed by the route state machine."""


def can_transition(
    from_state: RouteState,
    to_state: RouteState,
    route_type: RouteType | None = None,
) -> bool:
    """Check if transition is allowed."""
    allowed = _TRANSITIONS.get((from_state, route_type))
    if allowed is None:
        allowed = _TRANSITIONS.get((from_state, None), set())
    return to_state in allowed


def transition(
    from_state: RouteState,
    to_state: RouteState,
    route_type: RouteType | None = None,
) -> RouteState:
    """Apply a transition or raise InvalidRouteTransitionError."""
    if not can_transition(from_state, to_state, route_type):
        raise InvalidRouteTransitionError(
            f"Cannot transition route from {from_state.value} to {to_state.value}"
            + (f" (route_type={route_type.value})" if route_type else "")
        )
    return to_state


def allowed_next(from_state: RouteState, route_type: RouteType | None = None) -> set[RouteState]:
    """Return the set of states reachable from ``from_state``."""
    return set(_TRANSITIONS.get((from_state, route_type), set())) | set(
        _TRANSITIONS.get((from_state, None), set())
    )


TERMINAL_STATES = {RouteState.EXPIRED}
ACTIVE_STATES = {RouteState.ACTIVE, RouteState.RENEWAL_DUE, RouteState.RENEWAL_PENDING}
