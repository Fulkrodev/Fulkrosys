"""Tests característicos baseline pre-Mini-Fase 3.5 — flow cliente actual.

BLOQUE 0 de Mini-Fase 3.5 (auth unificado). Captura comportamiento
ACTUAL (Bearer token + localStorage frontend) ANTES del refactor a
cookie httpOnly. Estos tests se ACTUALIZARÁN durante BLOQUES 1-5
conforme el refactor avanza, pero su PROPÓSITO permanece: red de
seguridad para detectar regresiones de comportamiento.

Tests basados en endpoints reales (signature audit pre-MF3.5):
- POST /api/v1/client-auth/login (LoginBody → LoginResponse)
- GET  /api/v1/client-portal/me (Bearer required)
- POST /api/v1/client-auth/logout

Ver ADR-018 + plan Mini-Fase 3.5 (TODO-AUTH-UNIFY-001).
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

# Sub-fase 4.D ADR-021: opt-out del autouse override (validamos auth real).
pytestmark = pytest.mark.real_auth


@pytest.mark.asyncio
async def test_client_login_valid_credentials_returns_access_token(
    async_client: AsyncClient,
    make_client_user,
    db,
):
    """POST /client-auth/login con credentials validas devuelve access_token
    + datos cliente (token_type, expires_at, must_change_password,
    full_name). ADR-013 v3 single-user-RW · sin role."""
    await make_client_user(
        email="test-baseline-1@example.com",
        password="TestP@ssw0rd123!",
    )

    response = await async_client.post(
        "/api/v1/client-auth/login",
        json={
            "email": "test-baseline-1@example.com",
            "password": "TestP@ssw0rd123!",
        },
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "expires_at" in data
    assert data["must_change_password"] is False


@pytest.mark.asyncio
async def test_client_login_invalid_password_returns_401(
    async_client: AsyncClient,
    make_client_user,
):
    """POST /client-auth/login con password incorrecto → 401."""
    await make_client_user(
        email="test-baseline-2@example.com",
        password="CorrectP@ss123456!",
    )

    response = await async_client.post(
        "/api/v1/client-auth/login",
        json={
            "email": "test-baseline-2@example.com",
            "password": "WrongP@ssword999!",
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_client_me_with_valid_bearer_returns_user_info(
    async_client: AsyncClient,
    make_client_user,
):
    """GET /client-portal/me con Bearer valido devuelve dict con id, email,
    scope, must_change_password. ADR-013 v3 single-user-RW."""
    await make_client_user(
        email="test-baseline-me@example.com",
        password="TestP@ssw0rd123!",
    )

    login_res = await async_client.post(
        "/api/v1/client-auth/login",
        json={
            "email": "test-baseline-me@example.com",
            "password": "TestP@ssw0rd123!",
        },
    )
    assert login_res.status_code == 200, login_res.text
    access_token = login_res.json()["access_token"]

    me_res = await async_client.get(
        "/api/v1/client-portal/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert me_res.status_code == 200, me_res.text
    data = me_res.json()
    assert data["email"] == "test-baseline-me@example.com"
    assert data["scope"] == "rw"
    assert data["must_change_password"] is False


@pytest.mark.asyncio
async def test_client_me_without_auth_returns_401(
    async_client: AsyncClient,
):
    """GET /client-portal/me sin Bearer → 401."""
    response = await async_client.get("/api/v1/client-portal/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_client_me_with_cookie_only_returns_user_info(
    async_client: AsyncClient,
    make_client_user,
):
    """GET /client-portal/me con cookie fulkro_session (sin Bearer) →
    200 + user info.

    Valida BLOQUE 2 Mini-Fase 3.5: get_current_client_user lee cookie
    httpOnly como auth method además de Authorization Bearer. httpx
    envía cookies automáticamente tras Set-Cookie del login.
    """
    await make_client_user(
        email="test-cookie-only@example.com",
        password="TestP@ssw0rd123!",
    )

    login_res = await async_client.post(
        "/api/v1/client-auth/login",
        json={
            "email": "test-cookie-only@example.com",
            "password": "TestP@ssw0rd123!",
        },
    )
    assert login_res.status_code == 200, login_res.text
    # Tras login, httpx ha guardado la cookie automáticamente.

    # GET /me SIN Authorization header — solo cookie
    me_res = await async_client.get("/api/v1/client-portal/me")

    assert me_res.status_code == 200, me_res.text
    data = me_res.json()
    assert data["email"] == "test-cookie-only@example.com"
    assert data["scope"] == "rw"


@pytest.mark.asyncio
async def test_client_logout_invalidates_session(
    async_client: AsyncClient,
    make_client_user,
):
    """POST /client-auth/logout → siguiente call con mismo token
    devuelve 401 (sesión revocada en client_sessions)."""
    await make_client_user(
        email="test-baseline-logout@example.com",
        password="TestP@ssw0rd123!",
    )

    login_res = await async_client.post(
        "/api/v1/client-auth/login",
        json={
            "email": "test-baseline-logout@example.com",
            "password": "TestP@ssw0rd123!",
        },
    )
    access_token = login_res.json()["access_token"]
    auth_header = {"Authorization": f"Bearer {access_token}"}

    # /me funciona con token activo (GET no requiere CSRF)
    me_pre = await async_client.get(
        "/api/v1/client-portal/me", headers=auth_header
    )
    assert me_pre.status_code == 200

    # logout (BLOQUE 4 MF3.5: POST mutating requiere X-CSRF-Token
    # con valor de cookie fulkro_csrf seteada por server en login)
    csrf_token = async_client.cookies.get("fulkro_csrf")
    assert csrf_token is not None, "Cookie fulkro_csrf debió ser seteada en login"
    logout_res = await async_client.post(
        "/api/v1/client-auth/logout",
        headers={**auth_header, "X-CSRF-Token": csrf_token},
    )
    assert logout_res.status_code == 200, logout_res.text
    assert logout_res.json() == {"logged_out": True}

    # /me con mismo token tras logout → 401
    me_post = await async_client.get(
        "/api/v1/client-portal/me", headers=auth_header
    )
    assert me_post.status_code == 401


# ════════════════════════════════════════════════════════════════════
# CSRF triple binding (BLOQUE 4 MF3.5)
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_mutation_without_csrf_header_is_rejected(
    async_client: AsyncClient,
    make_client_user,
):
    """POST mutating sin header X-CSRF-Token → 403 csrf token mismatch.

    Replica patrón admin TestCSRF::test_mutation_without_csrf_header_is_rejected
    (backend/tests/auth/test_auth_api.py).
    """
    await make_client_user(
        email="test-csrf-missing@example.com",
        password="TestP@ssw0rd123!",
    )
    await async_client.post(
        "/api/v1/client-auth/login",
        json={
            "email": "test-csrf-missing@example.com",
            "password": "TestP@ssw0rd123!",
        },
    )
    # Logout SIN X-CSRF-Token header
    logout_res = await async_client.post("/api/v1/client-auth/logout")
    assert logout_res.status_code == 403
    assert "csrf" in logout_res.json().get("detail", "").lower()


@pytest.mark.asyncio
async def test_mutation_with_wrong_csrf_header_is_rejected(
    async_client: AsyncClient,
    make_client_user,
):
    """POST mutating con X-CSRF-Token distinto de cookie → 403."""
    await make_client_user(
        email="test-csrf-wrong@example.com",
        password="TestP@ssw0rd123!",
    )
    await async_client.post(
        "/api/v1/client-auth/login",
        json={
            "email": "test-csrf-wrong@example.com",
            "password": "TestP@ssw0rd123!",
        },
    )
    logout_res = await async_client.post(
        "/api/v1/client-auth/logout",
        headers={"X-CSRF-Token": "tampered-attacker-token"},
    )
    assert logout_res.status_code == 403


@pytest.mark.asyncio
async def test_mutation_with_valid_csrf_header_succeeds(
    async_client: AsyncClient,
    make_client_user,
):
    """POST mutating con X-CSRF-Token == cookie csrf == JWT claim → 200."""
    await make_client_user(
        email="test-csrf-valid@example.com",
        password="TestP@ssw0rd123!",
    )
    await async_client.post(
        "/api/v1/client-auth/login",
        json={
            "email": "test-csrf-valid@example.com",
            "password": "TestP@ssw0rd123!",
        },
    )
    csrf_token = async_client.cookies.get("fulkro_csrf")
    assert csrf_token is not None

    logout_res = await async_client.post(
        "/api/v1/client-auth/logout",
        headers={"X-CSRF-Token": csrf_token},
    )
    assert logout_res.status_code == 200


@pytest.mark.asyncio
async def test_get_does_not_require_csrf_header(
    async_client: AsyncClient,
    make_client_user,
):
    """GET /client-portal/me NO requiere X-CSRF-Token (idempotente).

    Replica patrón admin TestCSRF::test_GET_does_not_require_csrf_header.
    """
    await make_client_user(
        email="test-csrf-get@example.com",
        password="TestP@ssw0rd123!",
    )
    await async_client.post(
        "/api/v1/client-auth/login",
        json={
            "email": "test-csrf-get@example.com",
            "password": "TestP@ssw0rd123!",
        },
    )
    # GET SIN X-CSRF-Token (debe funcionar)
    me_res = await async_client.get("/api/v1/client-portal/me")
    assert me_res.status_code == 200
