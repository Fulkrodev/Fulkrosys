"""Tests JWT role-aware claims + dependencies role-based + /auth/me capability.

Valida ADR-013 + ADR-015:
- ``service.create_session`` produce JWT con claims role/is_owner
  derivados de BD + Settings
- Dependencies ``require_owner``, ``require_client_user`` rechazan
  con 403 selectivo
- ``GET /api/v1/auth/me`` expone los claims al frontend

Las dependencies se testean unitariamente (llamada directa con un
``User`` sintético). El test de /auth/me usa el flow MFA real
(login + TOTP) porque httpx solo envía cookies que llegaron vía
``Set-Cookie`` server-side; cookies seteadas manualmente con
``async_client.cookies.set`` no se propagan al endpoint en este
fixture.
"""
from __future__ import annotations

import pyotp
import pytest
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth import crypto, service
from backend.app.auth.dependencies import (
    require_client_user,
    require_owner,
)

# Sub-fase 4.D ADR-021: opt-out del autouse override (validamos auth real).
pytestmark = pytest.mark.real_auth


async def _enroll_totp(db: AsyncSession, user_id: str) -> str:
    """Force-enroll TOTP for the given user id. Returns secret."""
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


# ──────────────────────────────────────────────────────────────────────
# Unit tests — dependencies validan ``user.role`` (BD) directamente
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_require_owner_blocks_client_user(make_user):
    client = await make_user(role="client_user")
    with pytest.raises(HTTPException) as exc_info:
        await require_owner(user=client)
    assert exc_info.value.status_code == 403
    assert "owner" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_require_client_user_blocks_owner(make_user):
    """Marcos owner (role_pool='marcos') no puede pasar require_client_user.

    Sub-fase 4.D ADR-021: require_client_user ahora lookup
    request.state.auth_subject (populado por global dep
    authenticate_request) en vez del User directo. El test mock
    Request con AuthSubject role_pool='marcos' debe rechazarse 403.
    """
    from types import SimpleNamespace

    from backend.app.auth.global_dep import AuthSubject

    owner = await make_user(role="owner", email="extra-owner@example.com")
    fake_request = SimpleNamespace(
        state=SimpleNamespace(
            auth_subject=AuthSubject(user=owner, role_pool="marcos"),
        ),
    )
    with pytest.raises(HTTPException) as exc_info:
        await require_client_user(fake_request)
    assert exc_info.value.status_code == 403


# ──────────────────────────────────────────────────────────────────────
# Integration tests — claims propagados al JWT y a /auth/me
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_jwt_session_includes_role_and_capability_claims(
    db: AsyncSession, make_user, auth_seed_user
):
    """``service.create_session`` para un owner produce JWT con
    role + is_owner correctos."""
    owner = await service.get_user(db, auth_seed_user["id"])
    assert owner is not None

    token, _csrf, _exp, _jti = await service.create_session(
        db, user=owner, ip_address="127.0.0.1", user_agent="test"
    )
    payload = crypto.decode_token(token)

    assert payload["role"] == "owner"
    assert payload["is_owner"] is True

    # Cliente sintético: role=client_user
    client = await make_user(role="client_user")
    token_c, _, _, _ = await service.create_session(
        db, user=client, ip_address="127.0.0.1", user_agent="test"
    )
    payload_c = crypto.decode_token(token_c)
    assert payload_c["role"] == "client_user"
    assert payload_c["is_owner"] is False


@pytest.mark.asyncio
async def test_auth_me_includes_role_claims_for_owner(
    async_client, db, auth_seed_user
):
    """/auth/me devuelve role + is_owner para un owner del fixture.

    Usa flow MFA real (login + TOTP) porque las cookies se propagan
    al endpoint solo cuando llegan vía ``Set-Cookie`` server-side.
    """
    # Login → mfa_ticket
    r = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": auth_seed_user["email"],
            "password": auth_seed_user["password"],
        },
    )
    assert r.status_code == 200, r.text
    ticket = r.json()["mfa_ticket"]

    # Enroll TOTP via BD + verify → cookies seteadas server-side
    secret = await _enroll_totp(db, auth_seed_user["id"])
    code = pyotp.TOTP(secret).now()
    r2 = await async_client.post(
        "/api/v1/auth/totp/verify",
        json={"mfa_ticket": ticket, "code": code},
    )
    assert r2.status_code == 200, r2.text

    # /me con cookies activas
    r3 = await async_client.get("/api/v1/auth/me")
    assert r3.status_code == 200, r3.text
    body = r3.json()
    assert body["email"] == auth_seed_user["email"]
    assert body["role"] == "owner"
    assert body["is_owner"] is True
