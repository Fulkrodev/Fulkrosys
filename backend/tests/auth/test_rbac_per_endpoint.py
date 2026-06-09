"""Tests integración RBAC per-endpoint (TODO-RBAC-PER-ENDPOINT-001).

Pattern unit + integration cobertura representativa:
- Verifica router-level dependencies aplicadas correctamente a motors
  Cat A (require_owner), Cat C (require_marcos_or_client).
- Helper `require_marcos_or_client` unit test (rechaza pool desconocido).
- Whitelist H49 + H51 paths en global dep.

Sin tests por motor individual (~26): el pattern uniforme `dependencies=[
Depends(require_X)]` aplicado router-level garantiza propagación a TODOS
los endpoints del router. Verificamos el pattern + helper, no
endpoint-by-endpoint.

ADR-021 (motors auth landing) + ADR-022 (panel admin clientes).
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from backend.app.auth.dependencies import (
    require_marcos_or_client,
    require_owner,
)
from backend.app.auth.global_dep import (
    AuthSubject,
    WHITELIST_EXACT,
    WHITELIST_PREFIX,
    _is_whitelisted,
)


# ════════════════════════════════════════════════════════════════════
# Test 1: Router-level Cat A motors aplicado
# ════════════════════════════════════════════════════════════════════


def test_cat_a_routers_have_require_owner_dependency():
    """Sample 3 motors Cat A tienen require_owner router-level."""
    from backend.app.motors.m01_categorization.api import router as m01
    from backend.app.motors.m02_magerit.api import router as m02
    from backend.app.motors.m13_commercial.api import router as m13

    for router, name in [(m01, "m01"), (m02, "m02"), (m13, "m13")]:
        dep_funcs = [d.dependency for d in router.dependencies]
        assert require_owner in dep_funcs, (
            f"Router {name} debe tener require_owner en dependencies"
        )


# ════════════════════════════════════════════════════════════════════
# Test 2: Router-level Cat C motors aplicado
# ════════════════════════════════════════════════════════════════════


def test_cat_c_routers_have_require_marcos_or_client_dependency():
    """3 motors Cat C tienen require_marcos_or_client router-level."""
    from backend.app.motors.m07_evidence.api import router as m07
    from backend.app.motors.m20_workspace.api import router as m20
    from backend.app.motors.m24_idms.api import router as m24

    for router, name in [(m07, "m07"), (m20, "m20"), (m24, "m24")]:
        dep_funcs = [d.dependency for d in router.dependencies]
        assert require_marcos_or_client in dep_funcs, (
            f"Router {name} debe tener require_marcos_or_client en dependencies"
        )


# ════════════════════════════════════════════════════════════════════
# Test 4: Helper require_marcos_or_client unit
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_require_marcos_or_client_passes_marcos():
    """Subject role_pool='marcos' → pasa OK."""

    class FakeUser:
        email = "marcos@example.com"

    request = SimpleNamespace(
        state=SimpleNamespace(
            auth_subject=AuthSubject(user=FakeUser(), role_pool="marcos"),
        ),
    )
    result = await require_marcos_or_client(request)
    assert result.email == "marcos@example.com"


@pytest.mark.asyncio
async def test_require_marcos_or_client_passes_cliente():
    """Subject role_pool='cliente' → pasa OK."""

    class FakeClientUser:
        email = "cliente@example.com"

    request = SimpleNamespace(
        state=SimpleNamespace(
            auth_subject=AuthSubject(user=FakeClientUser(), role_pool="cliente"),
        ),
    )
    result = await require_marcos_or_client(request)
    assert result.email == "cliente@example.com"


@pytest.mark.asyncio
async def test_require_marcos_or_client_blocks_unknown_pool():
    """Subject role_pool desconocido (e.g. 'auditor' futuro) → 403."""

    class FakeUser:
        email = "x@example.com"

    request = SimpleNamespace(
        state=SimpleNamespace(
            auth_subject=AuthSubject(user=FakeUser(), role_pool="auditor"),
        ),
    )
    with pytest.raises(HTTPException) as exc_info:
        await require_marcos_or_client(request)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_require_marcos_or_client_blocks_no_subject():
    """Sin auth_subject (global dep no se ejecutó) → 401.

    El helper interno ``_get_auth_subject`` retorna 401 (no 403) cuando
    no hay subject — semántica "authentication required" coherente con
    ``get_current_user`` original. Si el path está whitelisted, el
    global dep retorna None y nunca llega aquí.
    """
    request = SimpleNamespace(state=SimpleNamespace())
    with pytest.raises(HTTPException) as exc_info:
        await require_marcos_or_client(request)
    assert exc_info.value.status_code == 401


# ════════════════════════════════════════════════════════════════════
# Test 5: Whitelist H49 + H51 paths
# ════════════════════════════════════════════════════════════════════


def test_h49_magic_link_consume_whitelisted_exact():
    """H49 fix: /api/v1/magic-links/consume está en WHITELIST_EXACT."""
    assert "/api/v1/magic-links/consume" in WHITELIST_EXACT
    # Y NO está en prefix con slash trailing legacy
    assert "/api/v1/magic-links/consume/" not in WHITELIST_PREFIX


def test_h51_onboarding_consume_whitelisted_exact():
    """H51 fix: /api/v1/onboarding/consume está en WHITELIST_EXACT."""
    assert "/api/v1/onboarding/consume" in WHITELIST_EXACT


def test_h51_onboarding_me_whitelisted_prefix():
    """H51 fix: /api/v1/onboarding/me/* está en WHITELIST_PREFIX."""
    assert "/api/v1/onboarding/me/" in WHITELIST_PREFIX
    # Smoke matching real
    assert _is_whitelisted("/api/v1/onboarding/me/next-question") is True
    assert _is_whitelisted("/api/v1/onboarding/me/responses") is True
    # Y NO matchea otros paths admin
    assert _is_whitelisted("/api/v1/onboarding/sessions") is False
