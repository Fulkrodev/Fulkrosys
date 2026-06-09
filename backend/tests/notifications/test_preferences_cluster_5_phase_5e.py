"""CLUSTER 5 Phase 5E delta · notification preferences extension tests.

Cubre:
- whatsapp_enabled column persisted default FALSE
- event_opt_outs JSONB column persisted default {}
- GET /portal/notifications/preferences returns new fields
- PUT /portal/notifications/preferences updates new fields
- Field validation taxonomy (whatsapp_enabled bool · event_opt_outs dict)
"""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.notifications import NotificationPreference
from backend.tests.conftest import _admin_setup


@pytest.fixture
async def authed_client_user_fixture(
    async_client: AsyncClient, db: AsyncSession,
):
    """Cliente auth override · returns (client, user_id)."""
    from backend.app.auth.dependencies import require_client_user
    from backend.app.main import app
    from backend.app.models.client_portal import ClientUser

    client_id = uuid.uuid4()
    user_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO clients (id, nombre, cif, created_at) "
                "VALUES (:id, 'T', :cif, now())"
            ),
            {"id": str(client_id), "cif": cif},
        )
        await db.execute(
            text(
                "INSERT INTO client_users (id, client_id, email, "
                "password_hash, full_name, must_change_password, created_at) "
                "VALUES (:uid, :cid, :email, 'x', 'Test', false, now())"
            ),
            {
                "uid": str(user_id),
                "cid": str(client_id),
                "email": f"u-{user_id.hex[:8]}@test.invalid",
            },
        )

    stub_user = ClientUser(
        id=user_id,
        client_id=client_id,
        email=f"u-{user_id.hex[:8]}@test.invalid",
        password_hash="x",
        full_name="Test",
        must_change_password=False,
    )

    async def _override():
        return stub_user

    app.dependency_overrides[require_client_user] = _override
    yield async_client, user_id
    app.dependency_overrides.pop(require_client_user, None)


@pytest.mark.asyncio
async def test_preference_columns_default_values_phase_5e(db: AsyncSession):
    """Empirical default values: whatsapp_enabled=FALSE + event_opt_outs={}."""
    user_id = uuid.uuid4()
    client_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO clients (id, nombre, cif, created_at) "
                "VALUES (:id, 'T', :cif, now())"
            ),
            {"id": str(client_id), "cif": cif},
        )
        await db.execute(
            text(
                "INSERT INTO client_users (id, client_id, email, "
                "password_hash, full_name, must_change_password, created_at) "
                "VALUES (:uid, :cid, :email, 'x', 'Test', false, now())"
            ),
            {
                "uid": str(user_id),
                "cid": str(client_id),
                "email": f"u-{user_id.hex[:8]}@test.invalid",
            },
        )
        pref = NotificationPreference(client_user_id=user_id)
        db.add(pref)
        await db.flush()
        await db.refresh(pref)

    assert pref.whatsapp_enabled is False
    assert pref.event_opt_outs == {}


@pytest.mark.asyncio
async def test_get_preferences_returns_phase_5e_fields(
    authed_client_user_fixture,
) -> None:
    client, _ = authed_client_user_fixture
    resp = await client.get("/api/v1/portal/notifications/preferences")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "whatsapp_enabled" in body
    assert "event_opt_outs" in body
    assert body["whatsapp_enabled"] is False
    assert body["event_opt_outs"] == {}


@pytest.mark.asyncio
async def test_put_preferences_updates_whatsapp_enabled(
    authed_client_user_fixture,
) -> None:
    client, _ = authed_client_user_fixture
    resp = await client.put(
        "/api/v1/portal/notifications/preferences",
        json={"whatsapp_enabled": True},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["whatsapp_enabled"] is True


@pytest.mark.asyncio
async def test_put_preferences_updates_event_opt_outs_granular(
    authed_client_user_fixture,
) -> None:
    client, _ = authed_client_user_fixture
    payload = {
        "event_opt_outs": {
            "chat_admin_reply": False,
            "phase_changed": True,
            "evidence_expiring": False,
        },
    }
    resp = await client.put(
        "/api/v1/portal/notifications/preferences",
        json=payload,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["event_opt_outs"] == payload["event_opt_outs"]


@pytest.mark.asyncio
async def test_put_preferences_preserves_unset_fields(
    authed_client_user_fixture,
) -> None:
    """Partial update solo whatsapp_enabled · event_opt_outs preserved."""
    client, _ = authed_client_user_fixture
    await client.put(
        "/api/v1/portal/notifications/preferences",
        json={"event_opt_outs": {"chat_admin_reply": True}},
    )
    resp = await client.put(
        "/api/v1/portal/notifications/preferences",
        json={"whatsapp_enabled": True},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["whatsapp_enabled"] is True
    assert body["event_opt_outs"] == {"chat_admin_reply": True}
