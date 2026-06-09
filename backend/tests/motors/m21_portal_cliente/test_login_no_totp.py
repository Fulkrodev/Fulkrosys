"""SAN-E.MB-1.1 · validación login cliente sin TOTP · ADR-046.

Tests confirmar BREAKING CHANGE post-migration a6d892162a67:

1. test_client_login_password_no_totp_step · login cliente con password
   responde directo autenticado · sin step TOTP · sin keys "totp_*" en
   response · sin error "TOTP requerido".

2. test_client_me_no_totp_field · GET /client-portal/me devuelve dict
   sin key "totp_enabled" (UserOut depurado · /me payload limpio).

Regresión admin TOTP: ver backend/tests/auth/test_admin_login_post_san_e.py
(separado por cross-conftest fixture access · auth_seed_user vive
en tests/auth/conftest.py).
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

# Sub-fase 4.D ADR-021: opt-out del autouse override (validamos auth real).
pytestmark = pytest.mark.real_auth


@pytest.mark.asyncio
async def test_client_login_password_no_totp_step(
    async_client: AsyncClient,
    make_client_user,
    db: AsyncSession,
):
    """Login cliente con password · respuesta directa autenticada · 0 TOTP."""
    await make_client_user(
        email="test-no-totp-1@example.com",
        password="TestP@ssw0rd123!",
    )

    response = await async_client.post(
        "/api/v1/client-auth/login",
        json={
            "email": "test-no-totp-1@example.com",
            "password": "TestP@ssw0rd123!",
        },
    )

    # Login responde directo autenticado · sin step intermedio
    assert response.status_code == 200, response.text
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    # SAN-E.MB-1.1 · response NO contiene keys TOTP
    assert "totp_enabled" not in data
    assert "needs_totp" not in data
    assert "totp_required" not in data

    # Body request totp_code ya no es campo válido del schema
    # (Pydantic ignora extras por default · pero el campo no se procesa)
    response_with_totp = await async_client.post(
        "/api/v1/client-auth/login",
        json={
            "email": "test-no-totp-1@example.com",
            "password": "TestP@ssw0rd123!",
            "totp_code": "123456",  # ignorado · sin error
        },
    )
    assert response_with_totp.status_code == 200, response_with_totp.text


@pytest.mark.asyncio
async def test_client_me_no_totp_field(
    async_client: AsyncClient,
    make_client_user,
    db: AsyncSession,
):
    """GET /client-portal/me · response sin key 'totp_enabled' · UserOut depurado."""
    await make_client_user(
        email="test-no-totp-2@example.com",
        password="TestP@ssw0rd123!",
    )

    login_res = await async_client.post(
        "/api/v1/client-auth/login",
        json={
            "email": "test-no-totp-2@example.com",
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
    # Keys esperados post-MB-1.1 + ADR-013 v3 single-user-RW
    assert data["email"] == "test-no-totp-2@example.com"
    assert data["scope"] == "rw"
    assert "must_change_password" in data
    # SAN-E.MB-1.1 · /me NO devuelve totp_enabled
    assert "totp_enabled" not in data
    # ADR-013 v3 · /me NO devuelve role/scopes legacy
    assert "role" not in data
    assert "scopes" not in data


# Test admin TOTP regresión: ver backend/tests/auth/test_admin_login_post_san_e.py
# (movido por cross-conftest fixture access · auth_seed_user vive en tests/auth/)
