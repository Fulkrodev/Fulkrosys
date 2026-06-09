"""HTTP integration tests for the auth router.

Covers the 6 public endpoints plus TOTP setup helpers. WebAuthn verify/register
are tested via mocking of ``webauthn_svc`` since there is no real authenticator
in CI.

Tests use the ``auth_seed_user`` fixture (conftest.py) which creates a
dedicated test owner with predictable email/password, no MFA enrolled.
The production seed user is never touched by these tests — fixture state
rollbacks at end of test transaction (SAN-A.A2.bis).
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import jwt as pyjwt
import pyotp
import pytest
from sqlalchemy import text

from backend.app.auth import crypto, totp_svc, webauthn_svc
from backend.app.auth.crypto import JWT_ALGORITHM, _PRIVATE_PEM

# Sub-fase 4.D ADR-021: opt-out del autouse override (validamos auth real).
pytestmark = pytest.mark.real_auth


async def _enroll_totp_for_user(db, user_id: str) -> str:
    """Force-enrol TOTP for the given user id. Returns the secret."""
    secret = pyotp.random_base32()
    await db.execute(
        text("DELETE FROM auth_totp_secrets WHERE user_id = :uid"),
        {"uid": user_id},
    )
    await db.execute(
        text(
            "INSERT INTO auth_totp_secrets (user_id, secret, verified) "
            "VALUES (:uid, :s, true)"
        ),
        {"uid": user_id, "s": secret},
    )
    await db.flush()
    return secret


async def _login_and_get_ticket(async_client, user: dict) -> str:
    """Login con auth_seed_user fixture · devuelve el mfa_ticket."""
    r = await async_client.post(
        "/api/v1/auth/login",
        json={"email": user["email"], "password": user["password"]},
    )
    assert r.status_code == 200, r.text
    return r.json()["mfa_ticket"]


async def _login_verify_totp_get_csrf(
    async_client, db, user: dict
) -> str:
    """Helper: full login → enrol TOTP → verify → return csrf token + cookies set."""
    ticket = await _login_and_get_ticket(async_client, user)
    secret = await _enroll_totp_for_user(db, user["id"])
    code = pyotp.TOTP(secret).now()
    r = await async_client.post(
        "/api/v1/auth/totp/verify",
        json={"mfa_ticket": ticket, "code": code},
    )
    assert r.status_code == 200, r.text
    return r.json()["csrf_token"]


class TestLogin:
    @pytest.mark.asyncio
    async def test_login_correct_password_returns_mfa_ticket(
        self, async_client, db, auth_seed_user
    ):
        r = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": auth_seed_user["email"],
                "password": auth_seed_user["password"],
            },
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["mfa_ticket"]
        assert body["webauthn_available"] is False
        assert body["totp_available"] is False

    @pytest.mark.asyncio
    async def test_login_unknown_email_returns_401(self, async_client, db):
        r = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "ghost@example.com", "password": "whatever"},
        )
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_login_wrong_password_returns_401(
        self, async_client, db, auth_seed_user
    ):
        r = await async_client.post(
            "/api/v1/auth/login",
            json={"email": auth_seed_user["email"], "password": "wrong"},
        )
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_login_mfa_ticket_decodes_as_mfa_ticket_type(
        self, async_client, db, auth_seed_user
    ):
        r = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": auth_seed_user["email"],
                "password": auth_seed_user["password"],
            },
        )
        ticket = r.json()["mfa_ticket"]
        payload = crypto.decode_token(ticket)
        assert payload["typ"] == "mfa_ticket"
        assert payload["sub"]
        assert "exp" in payload

    @pytest.mark.asyncio
    async def test_login_ip_rate_limit_blocks_after_5_failures(
        self, async_client, db, auth_seed_user
    ):
        # first 5 failures return 401
        for _ in range(5):
            r = await async_client.post(
                "/api/v1/auth/login",
                json={"email": auth_seed_user["email"], "password": "wrong"},
            )
            assert r.status_code in (401, 429, 423)

        r6 = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": auth_seed_user["email"],
                "password": auth_seed_user["password"],
            },
        )
        assert r6.status_code == 429

    @pytest.mark.asyncio
    async def test_login_inactive_user_returns_401(
        self, async_client, db, auth_seed_user
    ):
        await db.execute(
            text("UPDATE auth_users SET is_active = false WHERE id = :id"),
            {"id": auth_seed_user["id"]},
        )
        await db.flush()
        # Expire the cached User instance so the login endpoint reloads
        # the row (and sees is_active=false). Without expire, SQLAlchemy's
        # identity map returns the cached User with is_active=true.
        db.expire(auth_seed_user["user"])
        r = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": auth_seed_user["email"],
                "password": auth_seed_user["password"],
            },
        )
        assert r.status_code == 401


class TestTOTP:
    @pytest.mark.asyncio
    async def test_totp_verify_with_unknown_ticket_returns_401(
        self, async_client, db
    ):
        r = await async_client.post(
            "/api/v1/auth/totp/verify",
            json={"mfa_ticket": "nonsense", "code": "123456"},
        )
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_totp_verify_without_enrollment_returns_400(
        self, async_client, db, auth_seed_user
    ):
        ticket = await _login_and_get_ticket(async_client, auth_seed_user)
        r = await async_client.post(
            "/api/v1/auth/totp/verify",
            json={"mfa_ticket": ticket, "code": "123456"},
        )
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_totp_verify_wrong_code_returns_401(
        self, async_client, db, auth_seed_user
    ):
        ticket = await _login_and_get_ticket(async_client, auth_seed_user)
        await _enroll_totp_for_user(db, auth_seed_user["id"])
        r = await async_client.post(
            "/api/v1/auth/totp/verify",
            json={"mfa_ticket": ticket, "code": "000000"},
        )
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_totp_verify_correct_code_sets_cookies(
        self, async_client, db, auth_seed_user
    ):
        ticket = await _login_and_get_ticket(async_client, auth_seed_user)
        secret = await _enroll_totp_for_user(db, auth_seed_user["id"])
        code = pyotp.TOTP(secret).now()
        r = await async_client.post(
            "/api/v1/auth/totp/verify",
            json={"mfa_ticket": ticket, "code": code},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["csrf_token"]
        assert "fulkro_session" in r.cookies
        assert "fulkro_csrf" in r.cookies

    @pytest.mark.asyncio
    async def test_totp_code_format_validation(
        self, async_client, db, auth_seed_user
    ):
        ticket = await _login_and_get_ticket(async_client, auth_seed_user)
        await _enroll_totp_for_user(db, auth_seed_user["id"])
        r = await async_client.post(
            "/api/v1/auth/totp/verify",
            json={"mfa_ticket": ticket, "code": "12"},  # too short
        )
        assert r.status_code == 422


class TestMe:
    @pytest.mark.asyncio
    async def test_me_without_cookie_returns_401(self, async_client, db):
        r = await async_client.get("/api/v1/auth/me")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_me_with_session_returns_profile(
        self, async_client, db, auth_seed_user
    ):
        await _login_verify_totp_get_csrf(async_client, db, auth_seed_user)
        r = await async_client.get("/api/v1/auth/me")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["email"] == auth_seed_user["email"]
        assert body["display_name"] == auth_seed_user["display_name"]
        assert body["totp_enabled"] is True

    @pytest.mark.asyncio
    async def test_me_with_malformed_cookie_returns_401(self, async_client, db):
        async_client.cookies.set("fulkro_session", "not-a-jwt", domain="test")
        r = await async_client.get("/api/v1/auth/me")
        assert r.status_code == 401


class TestLogout:
    @pytest.mark.asyncio
    async def test_logout_without_session_returns_401(self, async_client, db):
        r = await async_client.post("/api/v1/auth/logout")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_logout_revokes_session(
        self, async_client, db, auth_seed_user
    ):
        csrf = await _login_verify_totp_get_csrf(async_client, db, auth_seed_user)

        r2 = await async_client.post(
            "/api/v1/auth/logout", headers={"X-CSRF-Token": csrf}
        )
        assert r2.status_code == 200, r2.text
        assert r2.json()["revoked"] is True

        # follow-up requests are unauthorized
        r3 = await async_client.get("/api/v1/auth/me")
        assert r3.status_code == 401


class TestCSRF:
    @pytest.mark.asyncio
    async def test_mutation_without_csrf_header_is_rejected(
        self, async_client, db, auth_seed_user
    ):
        await _login_verify_totp_get_csrf(async_client, db, auth_seed_user)
        r = await async_client.post("/api/v1/auth/logout")
        assert r.status_code == 403

    @pytest.mark.asyncio
    async def test_mutation_with_wrong_csrf_header_is_rejected(
        self, async_client, db, auth_seed_user
    ):
        await _login_verify_totp_get_csrf(async_client, db, auth_seed_user)
        r = await async_client.post(
            "/api/v1/auth/logout", headers={"X-CSRF-Token": "tampered"}
        )
        assert r.status_code == 403

    @pytest.mark.asyncio
    async def test_GET_does_not_require_csrf_header(
        self, async_client, db, auth_seed_user
    ):
        await _login_verify_totp_get_csrf(async_client, db, auth_seed_user)
        r = await async_client.get("/api/v1/auth/me")
        assert r.status_code == 200


class TestJWTValidation:
    @pytest.mark.asyncio
    async def test_expired_session_returns_401(
        self, async_client, db, auth_seed_user
    ):
        now = datetime.now(timezone.utc)
        payload = {
            "sub": auth_seed_user["id"],
            "jti": uuid.uuid4().hex,
            "typ": "session",
            "iat": int((now - timedelta(hours=9)).timestamp()),
            "exp": int((now - timedelta(minutes=1)).timestamp()),
            "csrf": "x",
        }
        token = pyjwt.encode(payload, _PRIVATE_PEM, algorithm=JWT_ALGORITHM)
        async_client.cookies.set("fulkro_session", token, domain="test")
        r = await async_client.get("/api/v1/auth/me")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_wrong_token_type_rejected(
        self, async_client, db, auth_seed_user
    ):
        token, _, _ = crypto.issue_token(
            user_id=auth_seed_user["id"], typ="mfa_ticket"
        )
        async_client.cookies.set("fulkro_session", token, domain="test")
        r = await async_client.get("/api/v1/auth/me")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_session_for_unknown_jti_rejected(
        self, async_client, db, auth_seed_user
    ):
        """A signature-valid session JWT whose JTI has no DB row is rejected."""
        token, _, _ = crypto.issue_token(
            user_id=auth_seed_user["id"], typ="session", csrf_token="abc"
        )
        async_client.cookies.set("fulkro_session", token, domain="test")
        async_client.cookies.set("fulkro_csrf", "abc", domain="test")
        r = await async_client.get("/api/v1/auth/me")
        assert r.status_code == 401


class TestWebAuthnMocked:
    """WebAuthn happy/sad paths using mocked ``webauthn_svc`` verification."""

    @pytest.mark.asyncio
    async def test_webauthn_register_begin_requires_auth(self, async_client, db):
        r = await async_client.post("/api/v1/auth/webauthn/register/begin", json={})
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_webauthn_register_begin_returns_options_and_ticket(
        self, async_client, db, auth_seed_user
    ):
        csrf = await _login_verify_totp_get_csrf(async_client, db, auth_seed_user)

        r2 = await async_client.post(
            "/api/v1/auth/webauthn/register/begin",
            json={"device_name": "test-yubikey"},
            headers={"X-CSRF-Token": csrf},
        )
        assert r2.status_code == 200, r2.text
        body = r2.json()
        assert body["registration_ticket"]
        assert body["options"]
        assert "publicKey" in body["options"] or body["options"].get("public_key")

    @pytest.mark.asyncio
    async def test_webauthn_register_complete_stores_credential(
        self, async_client, db, auth_seed_user
    ):
        csrf = await _login_verify_totp_get_csrf(async_client, db, auth_seed_user)

        # Begin
        rb = await async_client.post(
            "/api/v1/auth/webauthn/register/begin",
            json={"device_name": "test-yubikey"},
            headers={"X-CSRF-Token": csrf},
        )
        registration_ticket = rb.json()["registration_ticket"]

        # Mock the fido2 completion so we can test persistence without a real authenticator
        fake_cred_id = uuid.uuid4().bytes * 2
        fake_pub_key = b"\xa5\x01\x02" + b"\x00" * 60

        class _Fake:
            credential_id = fake_cred_id
            public_key = fake_pub_key

        with patch.object(
            webauthn_svc,
            "complete_registration",
            return_value=_Fake(),
        ):
            rc = await async_client.post(
                "/api/v1/auth/webauthn/register/complete",
                json={
                    "registration_ticket": registration_ticket,
                    "client_data_json": webauthn_svc.b64url_encode(b"{}"),
                    "attestation_object": webauthn_svc.b64url_encode(b"\x00"),
                    "device_name": "test-yubikey",
                },
                headers={"X-CSRF-Token": csrf},
            )
        assert rc.status_code == 200, rc.text
        assert rc.json()["device_name"] == "test-yubikey"

        # /auth/me should reflect the new credential
        rm = await async_client.get("/api/v1/auth/me")
        assert rm.json()["webauthn_credentials"] == 1

    @pytest.mark.asyncio
    async def test_webauthn_verify_happy_path(
        self, async_client, db, auth_seed_user
    ):
        # Seed a credential directly via SQL. fido2 will refuse to parse the
        # fake public key, so ``begin_authentication`` is mocked as well.
        fake_cred_id = os.urandom(32)
        fake_pub_key = os.urandom(64)
        await db.execute(
            text(
                "INSERT INTO auth_webauthn_credentials "
                "(user_id, credential_id, public_key) VALUES (:uid, :cid, :pk)"
            ),
            {"uid": auth_seed_user["id"], "cid": fake_cred_id, "pk": fake_pub_key},
        )
        await db.flush()

        fake_state = {"challenge": "Y2hhbGxlbmdl", "user_verification": "preferred"}
        fake_options = {"publicKey": {"challenge": "Y2hhbGxlbmdl"}}

        with patch.object(
            webauthn_svc,
            "begin_authentication",
            return_value=(fake_options, fake_state),
        ):
            r = await async_client.post(
                "/api/v1/auth/login",
                json={
                    "email": auth_seed_user["email"],
                    "password": auth_seed_user["password"],
                },
            )
        body = r.json()
        assert body["webauthn_available"] is True
        ticket = body["mfa_ticket"]

        class _FakeStored:
            credential_id = fake_cred_id
            public_key = fake_pub_key
            sign_count = 7

        with patch.object(
            webauthn_svc, "complete_authentication", return_value=_FakeStored()
        ):
            r2 = await async_client.post(
                "/api/v1/auth/webauthn/verify",
                json={
                    "mfa_ticket": ticket,
                    "credential_id": webauthn_svc.b64url_encode(fake_cred_id),
                    "client_data_json": webauthn_svc.b64url_encode(b"{}"),
                    "authenticator_data": webauthn_svc.b64url_encode(b"\x00"),
                    "signature": webauthn_svc.b64url_encode(b"\x00"),
                },
            )
        assert r2.status_code == 200, r2.text
        assert r2.json()["csrf_token"]


class TestTOTPSetup:
    @pytest.mark.asyncio
    async def test_totp_setup_requires_auth(self, async_client, db):
        r = await async_client.post("/api/v1/auth/totp/setup")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_totp_setup_confirm_flow(
        self, async_client, db, auth_seed_user
    ):
        # auth_seed_user starts without TOTP enrolled by default; we still
        # need a session, so enrol via DB just to login + verify.
        csrf = await _login_verify_totp_get_csrf(async_client, db, auth_seed_user)

        # Now reset and go through the setup/confirm flow
        await db.execute(
            text("UPDATE auth_totp_secrets SET verified = false, secret = 'PLACEHOLDER' "
                 "WHERE user_id = :uid"),
            {"uid": auth_seed_user["id"]},
        )
        await db.flush()

        r_setup = await async_client.post(
            "/api/v1/auth/totp/setup", headers={"X-CSRF-Token": csrf}
        )
        assert r_setup.status_code == 200, r_setup.text
        setup_body = r_setup.json()
        assert setup_body["secret"]
        assert setup_body["provisioning_uri"].startswith("otpauth://")

        confirm_code = pyotp.TOTP(setup_body["secret"]).now()
        r_confirm = await async_client.post(
            "/api/v1/auth/totp/confirm",
            json={"code": confirm_code},
            headers={"X-CSRF-Token": csrf},
        )
        assert r_confirm.status_code == 200, r_confirm.text
        assert r_confirm.json()["totp_enabled"] is True


class TestCryptoPrimitives:
    def test_hash_password_verify_roundtrip(self):
        h = crypto.hash_password("abc123")
        assert crypto.verify_password("abc123", h)
        assert not crypto.verify_password("other", h)

    def test_issue_decode_roundtrip(self):
        token, jti, exp = crypto.issue_token(
            user_id="u1", typ="session", csrf_token="c"
        )
        payload = crypto.decode_token(token)
        assert payload["sub"] == "u1"
        assert payload["jti"] == jti
        assert payload["typ"] == "session"
        assert payload["csrf"] == "c"

    def test_constant_time_eq(self):
        assert crypto.constant_time_eq("abc", "abc")
        assert not crypto.constant_time_eq("abc", "abd")
        assert not crypto.constant_time_eq("abc", "ab")

    def test_totp_verify(self):
        secret = pyotp.random_base32()
        code = pyotp.TOTP(secret).now()
        assert totp_svc.verify_code(secret, code)
        assert not totp_svc.verify_code(secret, "000000")
        assert not totp_svc.verify_code(secret, "abc123")
        assert not totp_svc.verify_code(secret, "123")
