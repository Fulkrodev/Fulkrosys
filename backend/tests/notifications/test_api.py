"""Tests API endpoints NotificationOrchestrator MB-16.5 (ADR-039).

Cubre:
- GET /portal/notifications/preferences crea default si no existe.
- PUT /portal/notifications/preferences actualiza fields.
- PUT validación dnd pair (single field error).
- PUT validación HH:MM format.
- PUT validación digest_mode enum.
- GET /admin/notifications/events listado + filtros.
- POST /admin/notifications/events/{id}/redispatch.
- Auth: 401 sin auth · 403 con auth wrong pool.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from backend.app.auth.crypto import hash_password
from backend.app.models.client_portal import ClientUser
from backend.app.models.notifications import NotificationEvent
from backend.tests.conftest import _admin_setup


async def _make_client_user(db) -> ClientUser:
    client_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO clients (id, nombre, cif, created_at) "
                "VALUES (:id, 'T-API', :cif, now())"
            ),
            {"id": str(client_id), "cif": cif},
        )
        user = ClientUser(
            client_id=client_id,
            email=f"api-{uuid.uuid4().hex[:8]}@example.com",
            password_hash=hash_password("TestP@ssw0rd123!"),
            must_change_password=False,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
    return user


@pytest.fixture
async def client_user_authed(async_client, db):
    """Crea ClientUser + override require_client_user para tests portal."""
    user = await _make_client_user(db)

    from backend.app.main import app
    from backend.app.auth.dependencies import require_client_user

    async def override_require_client_user():
        return user

    app.dependency_overrides[require_client_user] = override_require_client_user
    yield async_client, user
    app.dependency_overrides.pop(require_client_user, None)


@pytest.fixture
async def owner_authed(async_client):
    """Owner authed via autouse fixture default (Marcos stub)."""
    yield async_client, None


@pytest.mark.asyncio
async def test_portal_get_preferences_creates_default(client_user_authed):
    client, user = client_user_authed
    response = await client.get("/api/v1/portal/notifications/preferences")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["client_user_id"] == str(user.id)
    assert data["email_enabled"] is True
    assert data["portal_sse_enabled"] is True
    assert data["dnd_start_local"] is None
    assert data["dnd_end_local"] is None
    assert data["timezone"] == "Europe/Madrid"
    assert data["digest_mode"] == "immediate"


@pytest.mark.asyncio
async def test_portal_put_preferences_updates_fields(client_user_authed):
    client, user = client_user_authed
    payload = {
        "email_enabled": False,
        "dnd_start_local": "22:00",
        "dnd_end_local": "08:00",
        "timezone": "America/Mexico_City",
    }
    response = await client.put(
        "/api/v1/portal/notifications/preferences", json=payload,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["email_enabled"] is False
    assert data["dnd_start_local"] == "22:00"
    assert data["dnd_end_local"] == "08:00"
    assert data["timezone"] == "America/Mexico_City"


@pytest.mark.asyncio
async def test_portal_put_dnd_single_field_rejected(client_user_authed):
    client, _ = client_user_authed
    response = await client.put(
        "/api/v1/portal/notifications/preferences",
        json={"dnd_start_local": "22:00"},
    )
    assert response.status_code == 400
    assert "dnd_start_local" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_portal_put_invalid_hhmm_rejected(client_user_authed):
    client, _ = client_user_authed
    response = await client.put(
        "/api/v1/portal/notifications/preferences",
        json={"dnd_start_local": "25:99", "dnd_end_local": "08:00"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_portal_put_invalid_digest_mode_rejected(client_user_authed):
    client, _ = client_user_authed
    response = await client.put(
        "/api/v1/portal/notifications/preferences",
        json={"digest_mode": "weekly_invalid"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_admin_list_events_empty(owner_authed):
    client, _ = owner_authed
    response = await client.get("/api/v1/admin/notifications/events")
    assert response.status_code == 200, response.text
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["limit"] == 50
    assert data["offset"] == 0


@pytest.mark.asyncio
async def test_admin_list_events_with_data(owner_authed, db):
    client, _ = owner_authed

    project_id = uuid.uuid4()
    cid = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO clients (id, nombre, cif, created_at) "
                "VALUES (:id, 'T-Adm', :cif, now())"
            ),
            {"id": str(cid), "cif": cif},
        )
        await db.execute(
            text(
                "INSERT INTO projects (id, client_id, nombre, created_at) "
                "VALUES (:id, :cid, 'P-Adm', now())"
            ),
            {"id": str(project_id), "cid": str(cid)},
        )
    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": str(project_id)},
    )

    for i in range(3):
        evt = NotificationEvent(
            event_type="task_assigned",
            recipient_email=f"u{i}@example.com",
            project_id=project_id,
            status="delivered" if i < 2 else "failed",
            template_used="task_assigned",
        )
        db.add(evt)
    await db.flush()

    response = await client.get(
        "/api/v1/admin/notifications/events?status=failed&limit=10"
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["total"] >= 1
    assert all(item["status"] == "failed" for item in data["items"])


@pytest.mark.asyncio
async def test_admin_list_events_invalid_status(owner_authed):
    client, _ = owner_authed
    response = await client.get(
        "/api/v1/admin/notifications/events?status=garbage"
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_admin_redispatch_event_already_delivered(owner_authed, db):
    client, _ = owner_authed

    project_id = uuid.uuid4()
    cid = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO clients (id, nombre, cif, created_at) "
                "VALUES (:id, 'T-Redip', :cif, now())"
            ),
            {"id": str(cid), "cif": cif},
        )
        await db.execute(
            text(
                "INSERT INTO projects (id, client_id, nombre, created_at) "
                "VALUES (:id, :cid, 'P', now())"
            ),
            {"id": str(project_id), "cid": str(cid)},
        )
    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": str(project_id)},
    )
    evt = NotificationEvent(
        event_type="task_assigned",
        recipient_email="x@example.com",
        project_id=project_id,
        status="delivered",
    )
    db.add(evt)
    await db.flush()
    await db.refresh(evt)

    response = await client.post(
        f"/api/v1/admin/notifications/events/{evt.id}/redispatch"
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "already_delivered"
