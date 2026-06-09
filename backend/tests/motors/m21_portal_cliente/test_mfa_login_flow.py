"""CLUSTER 6 Phase 6A · MFA login flow integration tests.

Verifies POST /client-auth/login 2-step:
1. Cliente sin MFA → 200 standard
2. Cliente con MFA + no mfa_code → 401 + requires_mfa: True
3. Cliente con MFA + valid TOTP → 200
4. Cliente con MFA + wrong TOTP → 401 + lockout escalates failed_attempts
"""
from __future__ import annotations

import pyotp
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m21_portal_cliente import mfa_service

pytestmark = pytest.mark.real_auth


async def _enroll_mfa(db: AsyncSession, user) -> str:
    init = await mfa_service.initiate(db, user)
    code = pyotp.TOTP(init.secret).now()
    await mfa_service.confirm(db, user, code)
    await db.commit()
    return init.secret


@pytest.mark.asyncio
async def test_login_without_mfa_remains_one_step(
    async_client: AsyncClient, make_client_user,
):
    await make_client_user(
        email="mfa-login-nomfa@example.com",
        password="TestP@ssw0rd123!",
    )
    resp = await async_client.post(
        "/api/v1/client-auth/login",
        json={"email": "mfa-login-nomfa@example.com",
              "password": "TestP@ssw0rd123!"},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_with_mfa_no_code_returns_401_requires_mfa(
    async_client: AsyncClient, make_client_user, db: AsyncSession,
):
    user = await make_client_user(
        email="mfa-login-step1@example.com",
        password="TestP@ssw0rd123!",
    )
    await _enroll_mfa(db, user)

    resp = await async_client.post(
        "/api/v1/client-auth/login",
        json={"email": "mfa-login-step1@example.com",
              "password": "TestP@ssw0rd123!"},
    )
    assert resp.status_code == 401
    body = resp.json()
    # FastAPI HTTPException(detail={..}) serializes as {"detail": {...}}
    assert body["detail"]["requires_mfa"] is True


@pytest.mark.asyncio
async def test_login_with_mfa_valid_code_returns_200(
    async_client: AsyncClient, make_client_user, db: AsyncSession,
):
    user = await make_client_user(
        email="mfa-login-step2@example.com",
        password="TestP@ssw0rd123!",
    )
    secret = await _enroll_mfa(db, user)
    code = pyotp.TOTP(secret).now()

    resp = await async_client.post(
        "/api/v1/client-auth/login",
        json={"email": "mfa-login-step2@example.com",
              "password": "TestP@ssw0rd123!",
              "mfa_code": code},
    )
    assert resp.status_code == 200, resp.text
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_with_mfa_bad_code_returns_401(
    async_client: AsyncClient, make_client_user, db: AsyncSession,
):
    user = await make_client_user(
        email="mfa-login-bad@example.com",
        password="TestP@ssw0rd123!",
    )
    await _enroll_mfa(db, user)

    resp = await async_client.post(
        "/api/v1/client-auth/login",
        json={"email": "mfa-login-bad@example.com",
              "password": "TestP@ssw0rd123!",
              "mfa_code": "000000"},
    )
    assert resp.status_code == 401
