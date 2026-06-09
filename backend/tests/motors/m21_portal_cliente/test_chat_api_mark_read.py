"""CLUSTER 5 Phase 5B delta · mark-read endpoints + audit_log emit.

Cover dual cliente/admin mark-read endpoints (bulk mark counterparty messages
as read) + audit_log integrity per Sub-atom 5.A 3-way OR pattern.

Pattern mirrors test_cluster_2_phase_2b_notification_wires authed_admin_client
fixture · cliente auth via dependency override get_current_client_user.
"""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m21_portal_cliente.chat_service import ChatService
from backend.tests.conftest import _admin_setup, setup_test_project


@pytest.fixture
async def authed_admin_client(async_client: AsyncClient, db: AsyncSession):
    from backend.app.auth.dependencies import require_owner
    from backend.app.main import app

    class _StubOwner:
        id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        email = "marcos@fulkro.test"
        is_owner = True

    async def _override():
        return _StubOwner()

    app.dependency_overrides[require_owner] = _override
    yield async_client
    app.dependency_overrides.pop(require_owner, None)


@pytest.fixture
async def authed_client_user(async_client: AsyncClient, db: AsyncSession):
    """Cliente auth override + active ClientUser row · returns (client, user_id)."""
    from backend.app.models.client_portal import ClientUser
    from backend.app.motors.m21_portal_cliente.api import (
        get_current_client_user,
    )
    from backend.app.main import app

    client_id_str, project_id_str = await setup_test_project(db)
    user_id = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO client_users (id, client_id, email, "
                "password_hash, full_name, must_change_password, created_at) "
                "VALUES (:uid, :cid, :email, 'x', 'Test', false, now())"
            ),
            {
                "uid": str(user_id),
                "cid": client_id_str,
                "email": f"cliente-{user_id.hex[:8]}@test.invalid",
            },
        )

    stub_user = ClientUser(
        id=user_id,
        client_id=uuid.UUID(client_id_str),
        email=f"cliente-{user_id.hex[:8]}@test.invalid",
        password_hash="x",
        full_name="Test",
        must_change_password=False,
    )

    async def _override():
        return stub_user

    app.dependency_overrides[get_current_client_user] = _override
    yield async_client, user_id, uuid.UUID(client_id_str), uuid.UUID(project_id_str)
    app.dependency_overrides.pop(get_current_client_user, None)


# ════════════════════════════════════════════════════════════════════
# Phase 5B.1 · admin mark-read endpoint
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_admin_mark_read_bulk_marks_client_messages(
    authed_admin_client: AsyncClient, db: AsyncSession,
) -> None:
    """POST /admin/projects/{id}/chat/threads/{tid}/mark-read marks client msgs."""
    _, project_id_str = await setup_test_project(db)
    project_id = uuid.UUID(project_id_str)
    async with _admin_setup(db):
        await db.execute(
            text("SELECT set_config('app.current_project_id', :pid, true)"),
            {"pid": project_id_str},
        )
        service = ChatService(db)
        thread = await service.get_or_create_thread(project_id=project_id)
        await service.post_message(thread.id, "client", "msg1")
        await service.post_message(thread.id, "client", "msg2")
        await db.commit()

    resp = await authed_admin_client.post(
        f"/api/v1/admin/projects/{project_id_str}/chat/threads/"
        f"{thread.id}/mark-read",
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["marked_count"] == 2

    audit_row = (await db.execute(
        text(
            "SELECT accion, payload_new::text FROM audit_log "
            "WHERE tabla = 'chat_messages' "
            "AND accion = 'chat.message.read' "
            "AND registro_id = :tid "
            "ORDER BY timestamp DESC LIMIT 1"
        ),
        {"tid": str(thread.id)},
    )).first()
    assert audit_row is not None
    assert audit_row[0] == "chat.message.read"
    assert '"reader_role": "admin"' in audit_row[1]
    assert '"marked_count": 2' in audit_row[1]


@pytest.mark.asyncio
async def test_admin_mark_read_thread_not_found_returns_404(
    authed_admin_client: AsyncClient, db: AsyncSession,
) -> None:
    """Missing thread returns 404 (NOT 500)."""
    _, project_id_str = await setup_test_project(db)
    bogus_thread = uuid.uuid4()
    resp = await authed_admin_client.post(
        f"/api/v1/admin/projects/{project_id_str}/chat/threads/"
        f"{bogus_thread}/mark-read",
    )
    assert resp.status_code == 404


# ════════════════════════════════════════════════════════════════════
# Phase 5B.2 · cliente mark-read endpoint
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_client_mark_read_bulk_marks_admin_messages(
    authed_client_user, db: AsyncSession,
) -> None:
    """POST /client-portal/chat/threads/{id}/mark-read marks admin msgs."""
    client, user_id, client_id, project_id = authed_client_user

    async with _admin_setup(db):
        await db.execute(
            text("SELECT set_config('app.current_project_id', :pid, true)"),
            {"pid": str(project_id)},
        )
        service = ChatService(db)
        thread = await service.get_or_create_thread(
            project_id=project_id, client_user_id=user_id,
        )
        await service.post_message(thread.id, "admin", "respuesta marcos 1")
        await service.post_message(thread.id, "admin", "respuesta marcos 2")
        await service.post_message(thread.id, "client", "client own msg")
        await db.commit()

    resp = await client.post(
        f"/api/v1/client-portal/chat/threads/{thread.id}/mark-read",
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["marked_count"] == 2

    async with _admin_setup(db):
        rows = (await db.execute(
            text(
                "SELECT sender_type, read_at FROM chat_messages "
                "WHERE thread_id = :tid "
                "ORDER BY created_at ASC"
            ),
            {"tid": str(thread.id)},
        )).all()
    admin_rows = [r for r in rows if r[0] == "admin"]
    client_rows = [r for r in rows if r[0] == "client"]
    assert len(admin_rows) == 2
    assert all(r[1] is not None for r in admin_rows)
    assert len(client_rows) == 1
    assert client_rows[0][1] is None


# ════════════════════════════════════════════════════════════════════
# Phase 5B.3 · idempotency verification
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_admin_mark_read_idempotent_second_call_returns_zero(
    authed_admin_client: AsyncClient, db: AsyncSession,
) -> None:
    """Second mark-read call returns marked_count=0 · NO duplicate audit emit."""
    _, project_id_str = await setup_test_project(db)
    project_id = uuid.UUID(project_id_str)
    async with _admin_setup(db):
        await db.execute(
            text("SELECT set_config('app.current_project_id', :pid, true)"),
            {"pid": project_id_str},
        )
        service = ChatService(db)
        thread = await service.get_or_create_thread(project_id=project_id)
        await service.post_message(thread.id, "client", "msg1")
        await db.commit()

    first = await authed_admin_client.post(
        f"/api/v1/admin/projects/{project_id_str}/chat/threads/"
        f"{thread.id}/mark-read",
    )
    second = await authed_admin_client.post(
        f"/api/v1/admin/projects/{project_id_str}/chat/threads/"
        f"{thread.id}/mark-read",
    )

    assert first.status_code == 200
    assert first.json()["marked_count"] == 1
    assert second.status_code == 200
    assert second.json()["marked_count"] == 0

    audit_count = (await db.execute(
        text(
            "SELECT COUNT(*) FROM audit_log "
            "WHERE tabla = 'chat_messages' "
            "AND accion = 'chat.message.read' "
            "AND registro_id = :tid"
        ),
        {"tid": str(thread.id)},
    )).scalar_one()
    assert audit_count == 1
