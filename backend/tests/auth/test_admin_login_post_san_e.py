"""SAN-E v3.MB-1.1.D · regresión admin TOTP post client TOTP off · ADR-046 v3.

Confirma admin auth flow intacto post-eliminación TOTP cliente:
- Admin login con email+password · response totp_available=True (admin SÍ pide step 2)
- Admin TOTP verify con código correcto · response 200 + csrf_token + cookies sesión

Test ubicado en backend/tests/auth/ porque fixture auth_seed_user vive en
backend/tests/auth/conftest.py (cross-conftest fixture access not supported
by pytest collection from sibling test directories).
"""
from __future__ import annotations

import pyotp
import pytest
from sqlalchemy import text

# Sub-fase 4.D ADR-021: opt-out del autouse override (validamos auth real).
pytestmark = pytest.mark.real_auth


@pytest.mark.asyncio
async def test_admin_login_with_totp_still_works(
    async_client,
    db,
    auth_seed_user,
):
    """Admin login flow con TOTP · regresión check · admin 2FA intacto post SAN-E v3.MB-1.

    Mirror del patrón test_auth_api.py::TestTOTP::test_totp_verify_correct_code_sets_cookies
    pero con afirmación explícita totp_available=True (admin retiene MFA · cliente NO).
    """
    # Setup · enrol TOTP en auth_totp_secrets para auth_seed_user
    secret = pyotp.random_base32()
    await db.execute(
        text("DELETE FROM auth_totp_secrets WHERE user_id = :uid"),
        {"uid": auth_seed_user["id"]},
    )
    await db.execute(
        text(
            "INSERT INTO auth_totp_secrets (user_id, secret, verified) "
            "VALUES (:uid, :s, true)"
        ),
        {"uid": auth_seed_user["id"], "s": secret},
    )
    await db.flush()

    # Step 1 · login admin · espera mfa_ticket + totp_available=True
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": auth_seed_user["email"],
            "password": auth_seed_user["password"],
        },
    )
    assert login_res.status_code == 200, login_res.text
    body = login_res.json()
    assert body["mfa_ticket"], "admin login MUST return mfa_ticket"
    assert body["totp_available"] is True, (
        "admin con TOTP enrolled MUST report totp_available=true · "
        "regresión SAN-E v3.MB-1.1: solo cliente perdió TOTP, admin retiene"
    )
    mfa_ticket = body["mfa_ticket"]

    # Step 2 · verify TOTP code admin · response 200 + csrf_token + cookies
    code = pyotp.TOTP(secret).now()
    verify_res = await async_client.post(
        "/api/v1/auth/totp/verify",
        json={"mfa_ticket": mfa_ticket, "code": code},
    )
    assert verify_res.status_code == 200, verify_res.text
    verify_body = verify_res.json()
    assert verify_body["csrf_token"], "admin TOTP verify MUST return csrf_token"
    assert "fulkro_session" in verify_res.cookies, (
        "admin TOTP verify MUST set fulkro_session cookie"
    )
    assert "fulkro_csrf" in verify_res.cookies, (
        "admin TOTP verify MUST set fulkro_csrf cookie"
    )
