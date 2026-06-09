"""Tests modelos NotificationEvent + NotificationPreference (MB-16.1).

Cubre invariantes schema migraciones ``sand_notif_events_001`` +
``sand_notif_prefs_001`` (ADR-039):
- Insert básico con defaults aplicados.
- CHECK constraints status / digest_mode / dnd format / dnd pair.
- UNIQUE client_user_id en preferences.
- FK behavior (CASCADE / SET NULL) ante delete.
- RLS isolation (project_id NULL admin events vs project-scoped).
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from backend.app.auth.crypto import hash_password
from backend.app.models.client_portal import ClientUser
from backend.app.models.notifications import (
    NotificationEvent,
    NotificationPreference,
)
from backend.tests.conftest import _admin_setup


async def _make_client_user(db) -> ClientUser:
    client_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO clients (id, nombre, cif, created_at) "
                "VALUES (:id, 'T-NotifTests', :cif, now())"
            ),
            {"id": str(client_id), "cif": cif},
        )
        user = ClientUser(
            client_id=client_id,
            email=f"notif-{uuid.uuid4().hex[:8]}@example.com",
            password_hash=hash_password("TestP@ssw0rd123!"),
            must_change_password=False,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
    await db.execute(
        text("SELECT set_config('app.current_client_id', :cid, true)"),
        {"cid": str(client_id)},
    )
    return user


async def _make_project(db) -> uuid.UUID:
    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO clients (id, nombre, cif, created_at) "
                "VALUES (:id, 'T-NotifProj', :cif, now())"
            ),
            {"id": str(client_id), "cif": cif},
        )
        await db.execute(
            text(
                "INSERT INTO projects (id, client_id, nombre, created_at) "
                "VALUES (:id, :cid, 'Notif-P', now())"
            ),
            {"id": str(project_id), "cid": str(client_id)},
        )
    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": str(project_id)},
    )
    return project_id


@pytest.mark.asyncio
async def test_notification_event_insert_with_defaults(db):
    project_id = await _make_project(db)
    event = NotificationEvent(
        event_type="task_assigned",
        recipient_email="cliente@example.com",
        project_id=project_id,
    )
    db.add(event)
    await db.flush()
    await db.refresh(event)

    assert event.id is not None
    assert event.status == "queued"
    assert event.retry_count == 0
    assert event.channels_attempted == []
    assert event.channels_succeeded == []
    assert event.channels_failed == []
    assert event.payload_jsonb == {}
    assert event.dispatched_at is None
    assert event.delivered_at is None
    assert event.created_at is not None


@pytest.mark.asyncio
async def test_notification_event_status_check_constraint(db):
    project_id = await _make_project(db)
    with pytest.raises(IntegrityError):
        await db.execute(
            text(
                "INSERT INTO notification_events "
                "(event_type, recipient_email, project_id, status) "
                "VALUES ('x', 'a@b.com', :pid, 'invalid_status')"
            ),
            {"pid": str(project_id)},
        )
        await db.flush()


@pytest.mark.asyncio
async def test_notification_event_admin_event_no_project_id(db):
    """Admin events (project_id NULL) deben pasar RLS isolation."""
    event = NotificationEvent(
        event_type="client_inactivity_admin",
        recipient_email="marcos@fulkro.es",
        project_id=None,
        payload_jsonb={"client_user_id": str(uuid.uuid4())},
    )
    db.add(event)
    await db.flush()
    await db.refresh(event)
    assert event.project_id is None
    assert event.status == "queued"


@pytest.mark.asyncio
async def test_notification_preference_insert_with_defaults(db):
    user = await _make_client_user(db)
    await db.execute(
        text(
            "SELECT set_config('app.current_client_user_id', :uid, true)"
        ),
        {"uid": str(user.id)},
    )
    pref = NotificationPreference(client_user_id=user.id)
    db.add(pref)
    await db.flush()
    await db.refresh(pref)

    assert pref.email_enabled is True
    assert pref.portal_sse_enabled is True
    assert pref.dnd_start_local is None
    assert pref.dnd_end_local is None
    assert pref.timezone == "Europe/Madrid"
    assert pref.digest_mode == "immediate"


@pytest.mark.asyncio
async def test_notification_preference_unique_client_user(db):
    user = await _make_client_user(db)
    await db.execute(
        text(
            "SELECT set_config('app.current_client_user_id', :uid, true)"
        ),
        {"uid": str(user.id)},
    )
    db.add(NotificationPreference(client_user_id=user.id))
    await db.flush()

    db.add(NotificationPreference(client_user_id=user.id))
    with pytest.raises(IntegrityError):
        await db.flush()


@pytest.mark.asyncio
async def test_notification_preference_digest_mode_check(db):
    user = await _make_client_user(db)
    await db.execute(
        text(
            "SELECT set_config('app.current_client_user_id', :uid, true)"
        ),
        {"uid": str(user.id)},
    )
    with pytest.raises(IntegrityError):
        await db.execute(
            text(
                "INSERT INTO notification_preferences "
                "(client_user_id, digest_mode) "
                "VALUES (:uid, 'weekly_invalid')"
            ),
            {"uid": str(user.id)},
        )
        await db.flush()


@pytest.mark.asyncio
async def test_notification_preference_dnd_pair_constraint_only_start(db):
    user = await _make_client_user(db)
    await db.execute(
        text(
            "SELECT set_config('app.current_client_user_id', :uid, true)"
        ),
        {"uid": str(user.id)},
    )
    with pytest.raises(IntegrityError):
        await db.execute(
            text(
                "INSERT INTO notification_preferences "
                "(client_user_id, dnd_start_local) "
                "VALUES (:uid, '22:00')"
            ),
            {"uid": str(user.id)},
        )
        await db.flush()


@pytest.mark.asyncio
async def test_notification_preference_dnd_pair_valid(db):
    user = await _make_client_user(db)
    await db.execute(
        text(
            "SELECT set_config('app.current_client_user_id', :uid, true)"
        ),
        {"uid": str(user.id)},
    )
    pref = NotificationPreference(
        client_user_id=user.id,
        dnd_start_local="22:00",
        dnd_end_local="08:00",
        timezone="America/Mexico_City",
    )
    db.add(pref)
    await db.flush()
    await db.refresh(pref)
    assert pref.dnd_start_local == "22:00"
    assert pref.dnd_end_local == "08:00"
    assert pref.timezone == "America/Mexico_City"


@pytest.mark.asyncio
async def test_notification_event_recipient_set_null_on_user_delete(db):
    """FK ondelete=SET NULL: borrar ClientUser deja recipient_user_id NULL."""
    user = await _make_client_user(db)
    project_id = await _make_project(db)

    event = NotificationEvent(
        event_type="task_assigned",
        recipient_user_id=user.id,
        recipient_email=user.email,
        project_id=project_id,
    )
    db.add(event)
    await db.flush()
    event_id = event.id

    async with _admin_setup(db):
        await db.execute(
            text("DELETE FROM client_users WHERE id = :uid"),
            {"uid": str(user.id)},
        )

    row = (
        await db.execute(
            text(
                "SELECT recipient_user_id, recipient_email "
                "FROM notification_events WHERE id = :eid"
            ),
            {"eid": str(event_id)},
        )
    ).first()
    assert row is not None
    assert row[0] is None
    assert row[1] == user.email


@pytest.mark.asyncio
async def test_notification_preference_cascade_on_user_delete(db):
    """FK ondelete=CASCADE: borrar ClientUser borra sus preferences."""
    user = await _make_client_user(db)
    await db.execute(
        text(
            "SELECT set_config('app.current_client_user_id', :uid, true)"
        ),
        {"uid": str(user.id)},
    )
    pref = NotificationPreference(client_user_id=user.id)
    db.add(pref)
    await db.flush()
    pref_id = pref.id

    async with _admin_setup(db):
        await db.execute(
            text("DELETE FROM client_users WHERE id = :uid"),
            {"uid": str(user.id)},
        )

    result = await db.execute(
        select(NotificationPreference).where(
            NotificationPreference.id == pref_id
        )
    )
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_notification_event_jsonb_channels_persistence(db):
    project_id = await _make_project(db)
    event = NotificationEvent(
        event_type="chat_admin_reply",
        recipient_email="cliente@example.com",
        project_id=project_id,
        channels_attempted=["email", "portal_sse"],
        channels_succeeded=["portal_sse"],
        channels_failed=["email"],
        error="postmark 5xx · retry exhausted",
        retry_count=3,
        template_used="chat_admin_reply",
        status="failed",
    )
    db.add(event)
    await db.flush()
    await db.refresh(event)

    assert event.channels_attempted == ["email", "portal_sse"]
    assert event.channels_succeeded == ["portal_sse"]
    assert event.channels_failed == ["email"]
    assert event.error == "postmark 5xx · retry exhausted"
    assert event.retry_count == 3
    assert event.status == "failed"
