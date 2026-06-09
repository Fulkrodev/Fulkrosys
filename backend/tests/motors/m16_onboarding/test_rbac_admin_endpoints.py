"""Tests RBAC m16_onboarding admin endpoints (TODO-RBAC-M16-ONBOARDING-ADMIN-001).

23 admin endpoints (sessions admin, connectors, pkg, pkg tools, lms admin,
export-categorization) ahora exigen ``Depends(require_owner)`` per-endpoint
para bloquear pool cliente y enforce role==owner desde BD.

Patrón **per-endpoint** (no router-level) preserva whitelist:
- ``/consume`` (token-based magic link)
- ``/me/*`` (cliente x-onboarding-session-* headers)

Ambos endpoints público compute-only (``/catalog``, ``/catalog/{id}``,
``/tools``, ``/lms/courses``, ``/lms/courses/{codigo}``) NO llevan
``require_owner`` (compute-only sin DB; auth bypass via global dep es la
puerta principal).

Pattern coherente con ``backend/tests/auth/test_rbac_per_endpoint.py`` +
``test_role_based_auth.py`` (require_owner unit-tested allí).
"""
from __future__ import annotations

import pytest
from fastapi.routing import APIRoute

from backend.app.auth.dependencies import require_owner
from backend.app.motors.m16_onboarding.api import router as m16_router

# Sub-fase 4.D ADR-021: opt-out del autouse override (validamos auth real).
pytestmark = pytest.mark.real_auth


def _route_deps(router, path: str, method: str):
    """Lookup ``route.dependencies`` (lista Depends explícita) por path+method."""
    for route in router.routes:
        if not isinstance(route, APIRoute):
            continue
        if route.path == path and method.upper() in route.methods:
            return [d.dependency for d in route.dependencies]
    return None


# ════════════════════════════════════════════════════════════════════
# Test 1 — Sample admin endpoints (sessions, pkg, lms) tienen require_owner
# ════════════════════════════════════════════════════════════════════


def test_admin_endpoints_have_require_owner_per_endpoint():
    """Sample 6 admin endpoints (sessions/pkg/lms/export) tienen require_owner.

    Per-endpoint check (no router-level) porque m16 mix admin + token-based.
    """
    samples = [
        # Sessions admin
        ("/onboarding/projects/{project_id}/sessions", "POST"),
        ("/onboarding/sessions/{session_id}", "GET"),
        ("/onboarding/sessions/{session_id}/cancel", "POST"),
        # PKG admin
        ("/onboarding/projects/{project_id}/pkg/summary", "GET"),
        ("/onboarding/projects/{project_id}/pkg/ingest-from-onboarding/{session_id}", "POST"),
        # LMS admin
        ("/onboarding/projects/{project_id}/lms/assign", "POST"),
        # Export categorization
        ("/onboarding/projects/{project_id}/onboarding/export-categorization", "GET"),
    ]
    for path, method in samples:
        deps = _route_deps(m16_router, path, method)
        assert deps is not None, f"Route {method} {path} no encontrada en m16 router"
        assert require_owner in deps, (
            f"{method} {path} debe tener require_owner per-endpoint "
            f"(TODO-RBAC-M16-ONBOARDING-ADMIN-001)"
        )


# ════════════════════════════════════════════════════════════════════
# Test 2 — Token-based cliente endpoints NO llevan require_owner
# ════════════════════════════════════════════════════════════════════


def test_client_token_based_endpoints_no_require_owner():
    """``/consume`` + ``/me/*`` son token-based cliente legítimos.

    Whitelist H49+H51 preservada: cliente recibe ``session_secret`` tras
    consumir magic link y autentica via ``x-onboarding-session-*`` headers
    (no cookie). Aplicar ``require_owner`` rompería el flujo legítimo.
    """
    samples = [
        ("/onboarding/consume", "POST"),
        ("/onboarding/me/next-question", "GET"),
        ("/onboarding/me/responses", "POST"),
        ("/onboarding/me/submit", "POST"),
        ("/onboarding/me/progress", "GET"),
    ]
    for path, method in samples:
        deps = _route_deps(m16_router, path, method)
        assert deps is not None, f"Route {method} {path} no encontrada"
        assert require_owner not in deps, (
            f"{method} {path} NO debe tener require_owner "
            f"(endpoint cliente legítimo via magic link)"
        )


# ════════════════════════════════════════════════════════════════════
# Test 3 — Conteo total: 23 endpoints admin con require_owner
# ════════════════════════════════════════════════════════════════════


def test_total_admin_endpoints_count_matches_audit():
    """Conteo total endpoints con require_owner == 24 (audit empírico).

    Si este conteo cambia, alguien añadió/quitó endpoint sin clasificar
    correctamente (admin vs token-based vs compute-only). REPORTAR antes
    de modificar este test — clasificación ADR-021/022.

    Batch B diagnóstico previo (2026): +1 endpoint admin con require_owner ·
    POST /onboarding/precliente/sessions (trigger del cuestionario del lead) →
    23 → 24. Los endpoints account-less del lead (/consume + /me/*) NO llevan
    require_owner (token/secret-based · ver test_client_token_based_*).
    """
    count = 0
    for route in m16_router.routes:
        if not isinstance(route, APIRoute):
            continue
        dep_funcs = [d.dependency for d in route.dependencies]
        if require_owner in dep_funcs:
            count += 1
    assert count == 24, (
        f"Esperaba 24 admin endpoints con require_owner, encontré {count}. "
        f"Clasificar nuevo endpoint en docstring de api.py antes de cambiar."
    )
