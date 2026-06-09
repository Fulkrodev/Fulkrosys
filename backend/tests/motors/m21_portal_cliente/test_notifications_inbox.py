"""Tests ClientNotification infra (SAN-E v3.MB-4.bis3 · ADR-020)."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text as sa_text

from backend.app.models.client_notification import ClientNotification
from backend.app.models.client_portal import ClientUser
from backend.app.motors.m21_portal_cliente import notification_service
from backend.tests.conftest import _admin_setup, setup_test_project


pytestmark = pytest.mark.asyncio


async def _setup_client_user(db, client_id: str) -> ClientUser:
    user_id = uuid.uuid4()
    email = f"notif-{user_id.hex[:8]}@example.com"
    async with _admin_setup(db):
        await db.execute(sa_text("""
            INSERT INTO client_users (id, client_id, email, password_hash,
                must_change_password, created_at)
            VALUES (:id, :cid, :email, 'fake_hash', false, now())
        """), {"id": str(user_id), "cid": client_id, "email": email})
    return ClientUser(
        id=user_id,
        client_id=uuid.UUID(client_id),
        email=email,
        password_hash="fake_hash",
        must_change_password=False,
    )


async def test_emit_creates_notification_record(db):
    _, project_id = await setup_test_project(db)
    res = await db.execute(sa_text("SELECT get_project_owner(:pid)"), {"pid": project_id})
    client_id = str(res.scalar())
    user = await _setup_client_user(db, client_id)

    notif = await notification_service.emit_client_notification(
        db,
        project_id=uuid.UUID(project_id),
        client_user_id=user.id,
        type="evidence_request",
        title="Aportar evidencia OBL-042",
        body="Evidencia documental requerida",
        target_url="/client-portal/evidencias?obligation=abc",
        priority="high",
        emitted_by_motor="m05",
    )
    assert notif.id is not None
    assert notif.type == "evidence_request"
    assert notif.priority == "high"
    assert notif.emitted_by_motor == "m05"
    assert notif.read_at is None


async def test_emit_invalid_type_raises(db):
    _, project_id = await setup_test_project(db)
    res = await db.execute(sa_text("SELECT get_project_owner(:pid)"), {"pid": project_id})
    client_id = str(res.scalar())
    user = await _setup_client_user(db, client_id)

    with pytest.raises(ValueError, match="type inválido"):
        await notification_service.emit_client_notification(
            db,
            project_id=uuid.UUID(project_id),
            client_user_id=user.id,
            type="totally_invalid_type",
            title="x",
            body=None,
            target_url="/x",
            emitted_by_motor="m05",
        )


async def test_emit_invalid_priority_raises(db):
    _, project_id = await setup_test_project(db)
    res = await db.execute(sa_text("SELECT get_project_owner(:pid)"), {"pid": project_id})
    client_id = str(res.scalar())
    user = await _setup_client_user(db, client_id)

    with pytest.raises(ValueError, match="priority inválido"):
        await notification_service.emit_client_notification(
            db,
            project_id=uuid.UUID(project_id),
            client_user_id=user.id,
            type="evidence_request",
            title="x",
            body=None,
            target_url="/x",
            priority="extreme_emergency",
            emitted_by_motor="m05",
        )


async def test_list_inbox_returns_unread_first(db):
    _, project_id = await setup_test_project(db)
    res = await db.execute(sa_text("SELECT get_project_owner(:pid)"), {"pid": project_id})
    client_id = str(res.scalar())
    user = await _setup_client_user(db, client_id)

    for i in range(3):
        await notification_service.emit_client_notification(
            db,
            project_id=uuid.UUID(project_id),
            client_user_id=user.id,
            type="generic_alert",
            title=f"Alert {i}",
            body=None,
            target_url=f"/x{i}",
            emitted_by_motor="m05",
        )

    items = await notification_service.list_inbox(db, user.id)
    assert len(items) == 3
    # ordered DESC by created_at · más reciente primero
    assert items[0].title == "Alert 2"
    assert items[1].title == "Alert 1"
    assert items[2].title == "Alert 0"


async def test_list_inbox_filter_include_read(db):
    _, project_id = await setup_test_project(db)
    res = await db.execute(sa_text("SELECT get_project_owner(:pid)"), {"pid": project_id})
    client_id = str(res.scalar())
    user = await _setup_client_user(db, client_id)

    n1 = await notification_service.emit_client_notification(
        db, project_id=uuid.UUID(project_id), client_user_id=user.id,
        type="generic_alert", title="N1", body=None,
        target_url="/x", emitted_by_motor="m05",
    )
    await notification_service.emit_client_notification(
        db, project_id=uuid.UUID(project_id), client_user_id=user.id,
        type="generic_alert", title="N2", body=None,
        target_url="/x", emitted_by_motor="m05",
    )
    await notification_service.mark_read(db, n1.id, user.id)

    unread_only = await notification_service.list_inbox(db, user.id)
    assert len(unread_only) == 1
    assert unread_only[0].title == "N2"

    all_items = await notification_service.list_inbox(db, user.id, include_read=True)
    assert len(all_items) == 2


async def test_mark_read_updates_timestamp(db):
    _, project_id = await setup_test_project(db)
    res = await db.execute(sa_text("SELECT get_project_owner(:pid)"), {"pid": project_id})
    client_id = str(res.scalar())
    user = await _setup_client_user(db, client_id)

    notif = await notification_service.emit_client_notification(
        db, project_id=uuid.UUID(project_id), client_user_id=user.id,
        type="evidence_request", title="X", body=None,
        target_url="/x", emitted_by_motor="m05",
    )
    assert notif.read_at is None
    ok = await notification_service.mark_read(db, notif.id, user.id)
    assert ok is True
    assert notif.read_at is not None


async def test_mark_read_other_user_returns_false(db):
    _, project_id = await setup_test_project(db)
    res = await db.execute(sa_text("SELECT get_project_owner(:pid)"), {"pid": project_id})
    client_id = str(res.scalar())
    user_a = await _setup_client_user(db, client_id)
    user_b = await _setup_client_user(db, client_id)

    notif = await notification_service.emit_client_notification(
        db, project_id=uuid.UUID(project_id), client_user_id=user_a.id,
        type="evidence_request", title="X", body=None,
        target_url="/x", emitted_by_motor="m05",
    )
    # User B intenta mark_read · debe retornar False (ownership)
    ok = await notification_service.mark_read(db, notif.id, user_b.id)
    assert ok is False


async def test_dismiss_updates_timestamp(db):
    _, project_id = await setup_test_project(db)
    res = await db.execute(sa_text("SELECT get_project_owner(:pid)"), {"pid": project_id})
    client_id = str(res.scalar())
    user = await _setup_client_user(db, client_id)

    notif = await notification_service.emit_client_notification(
        db, project_id=uuid.UUID(project_id), client_user_id=user.id,
        type="generic_alert", title="X", body=None,
        target_url="/x", emitted_by_motor="m05",
    )
    ok = await notification_service.dismiss(db, notif.id, user.id)
    assert ok is True
    assert notif.dismissed_at is not None


async def test_mark_actioned_sets_both_timestamps(db):
    _, project_id = await setup_test_project(db)
    res = await db.execute(sa_text("SELECT get_project_owner(:pid)"), {"pid": project_id})
    client_id = str(res.scalar())
    user = await _setup_client_user(db, client_id)

    notif = await notification_service.emit_client_notification(
        db, project_id=uuid.UUID(project_id), client_user_id=user.id,
        type="evidence_request", title="X", body=None,
        target_url="/x", emitted_by_motor="m05",
    )
    ok = await notification_service.mark_actioned(db, notif.id, user.id)
    assert ok is True
    assert notif.actioned_at is not None
    assert notif.read_at is not None  # implicit read


async def test_count_unread_excludes_read(db):
    _, project_id = await setup_test_project(db)
    res = await db.execute(sa_text("SELECT get_project_owner(:pid)"), {"pid": project_id})
    client_id = str(res.scalar())
    user = await _setup_client_user(db, client_id)

    n1 = await notification_service.emit_client_notification(
        db, project_id=uuid.UUID(project_id), client_user_id=user.id,
        type="generic_alert", title="N1", body=None,
        target_url="/x", emitted_by_motor="m05",
    )
    await notification_service.emit_client_notification(
        db, project_id=uuid.UUID(project_id), client_user_id=user.id,
        type="generic_alert", title="N2", body=None,
        target_url="/x", emitted_by_motor="m05",
    )

    assert await notification_service.count_unread(db, user.id) == 2
    await notification_service.mark_read(db, n1.id, user.id)
    assert await notification_service.count_unread(db, user.id) == 1


async def test_emit_with_expires_excludes_post_expiration(db):
    _, project_id = await setup_test_project(db)
    res = await db.execute(sa_text("SELECT get_project_owner(:pid)"), {"pid": project_id})
    client_id = str(res.scalar())
    user = await _setup_client_user(db, client_id)

    expired = ClientNotification(
        project_id=uuid.UUID(project_id),
        client_user_id=user.id,
        type="generic_alert",
        title="Expired",
        body=None,
        target_url="/x",
        emitted_by_motor="m05",
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    db.add(expired)
    await db.flush()

    items = await notification_service.list_inbox(db, user.id)
    assert all(n.title != "Expired" for n in items)
    assert await notification_service.count_unread(db, user.id) == 0
