"""Tests para OAuthStateService (SAN-E v3.MB-4.2.bis · Q2-A)."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text as sa_text

from backend.app.models.onboarding import OAuthStateToken
from backend.app.motors.m16_onboarding import oauth_state_service
from backend.tests.conftest import _admin_setup, setup_test_project


pytestmark = pytest.mark.asyncio


async def _create_test_client_user(db, client_id: str) -> uuid.UUID:
    """Crea ClientUser de test para un client_id existente."""
    user_id = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(sa_text("""
            INSERT INTO client_users (id, client_id, email, password_hash, must_change_password, created_at)
            VALUES (:id, :cid, :email, 'fake_hash', false, now())
        """), {
            "id": str(user_id),
            "cid": client_id,
            "email": f"test-{user_id.hex[:8]}@example.com",
        })
    return user_id


async def test_create_state_unique_token(db):
    _, project_id = await setup_test_project(db)
    res = await db.execute(sa_text(
        "SELECT get_project_owner(:pid)"), {"pid": project_id},
    )
    client_id = str(res.scalar())
    user_id = await _create_test_client_user(db, client_id)

    state1, _challenge1 = await oauth_state_service.create_state(
        db,
        client_user_id=user_id,
        project_id=uuid.UUID(project_id),
        connector_type="github",
        redirect_uri="http://localhost/cb",
    )
    state2, _challenge2 = await oauth_state_service.create_state(
        db,
        client_user_id=user_id,
        project_id=uuid.UUID(project_id),
        connector_type="github",
        redirect_uri="http://localhost/cb",
    )
    assert state1 != state2
    assert len(state1) >= 32


async def test_create_state_with_pkce_returns_challenge(db):
    _, project_id = await setup_test_project(db)
    res = await db.execute(sa_text(
        "SELECT get_project_owner(:pid)"), {"pid": project_id},
    )
    client_id = str(res.scalar())
    user_id = await _create_test_client_user(db, client_id)

    state, challenge = await oauth_state_service.create_state(
        db,
        client_user_id=user_id,
        project_id=uuid.UUID(project_id),
        connector_type="microsoft",
        redirect_uri="http://localhost/cb",
        use_pkce=True,
    )
    assert challenge is not None
    assert len(challenge) >= 32


async def test_validate_consumes_token(db):
    _, project_id = await setup_test_project(db)
    res = await db.execute(sa_text(
        "SELECT get_project_owner(:pid)"), {"pid": project_id},
    )
    client_id = str(res.scalar())
    user_id = await _create_test_client_user(db, client_id)

    state, _ = await oauth_state_service.create_state(
        db,
        client_user_id=user_id,
        project_id=uuid.UUID(project_id),
        connector_type="github",
        redirect_uri="http://localhost/cb",
    )
    ctx = await oauth_state_service.validate_and_consume(db, state)
    assert ctx.client_user_id == user_id
    assert ctx.connector_type == "github"

    # Replay attack: segundo intento debe fallar
    with pytest.raises(oauth_state_service.OAuthStateError, match="consumed"):
        await oauth_state_service.validate_and_consume(db, state)


async def test_validate_expired_raises(db):
    _, project_id = await setup_test_project(db)
    res = await db.execute(sa_text(
        "SELECT get_project_owner(:pid)"), {"pid": project_id},
    )
    client_id = str(res.scalar())
    user_id = await _create_test_client_user(db, client_id)

    # Manualmente crear con expires_at en el pasado
    state = "expired_state_xxxx_test_only_aaaaaaaaaaaaaaaaaaaaaa"
    record = OAuthStateToken(
        state_token=state,
        client_user_id=user_id,
        project_id=uuid.UUID(project_id),
        connector_type="github",
        redirect_uri="http://localhost/cb",
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    db.add(record)
    await db.flush()

    with pytest.raises(oauth_state_service.OAuthStateError, match="expired"):
        await oauth_state_service.validate_and_consume(db, state)
