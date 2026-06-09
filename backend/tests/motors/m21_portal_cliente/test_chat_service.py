"""Tests ChatService SSE+REST + SLA tracking (ADR-038 SAN-D MB-14.5)."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text

from backend.app.motors.m21_portal_cliente.chat_service import (
    ChatError,
    ChatService,
)
from backend.app.motors.m21_portal_cliente.models_chat import (
    ChatMessage,
    ChatThread,
)
from backend.tests.conftest import _admin_setup


async def _setup_project(db):
    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
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
                "INSERT INTO projects (id, client_id, nombre, created_at) "
                "VALUES (:id, :cid, 'P', now())"
            ),
            {"id": str(project_id), "cid": str(client_id)},
        )
    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": str(project_id)},
    )
    await db.execute(
        text("SELECT set_config('app.current_client_id', :cid, true)"),
        {"cid": str(client_id)},
    )
    await db.flush()
    return project_id


@pytest.mark.asyncio
async def test_get_or_create_thread_creates_first(db):
    project_id = await _setup_project(db)
    service = ChatService(db)

    thread = await service.get_or_create_thread(
        project_id=project_id, subject="Consulta inicial",
    )
    assert thread.project_id == project_id
    assert thread.status == "open"
    assert thread.messages_count == 0


@pytest.mark.asyncio
async def test_get_or_create_thread_returns_existing(db):
    project_id = await _setup_project(db)
    service = ChatService(db)

    t1 = await service.get_or_create_thread(project_id=project_id)
    t2 = await service.get_or_create_thread(project_id=project_id)
    assert t1.id == t2.id


@pytest.mark.asyncio
async def test_post_message_client_increments_count_and_updates_ts(db):
    project_id = await _setup_project(db)
    service = ChatService(db)

    thread = await service.get_or_create_thread(project_id=project_id)
    msg = await service.post_message(
        thread_id=thread.id,
        sender_type="client",
        content="Hola Marcos",
    )

    assert msg.sender_type == "client"
    assert msg.content == "Hola Marcos"

    await db.refresh(thread)
    assert thread.messages_count == 1
    assert thread.last_client_message_at is not None
    assert thread.last_admin_response_at is None


@pytest.mark.asyncio
async def test_post_message_admin_updates_response_ts(db):
    project_id = await _setup_project(db)
    service = ChatService(db)

    thread = await service.get_or_create_thread(project_id=project_id)
    await service.post_message(
        thread.id, "client", "Cliente question",
    )
    await service.post_message(
        thread.id, "admin", "Respuesta Marcos",
    )

    await db.refresh(thread)
    assert thread.messages_count == 2
    assert thread.last_admin_response_at is not None


@pytest.mark.asyncio
async def test_post_message_invalid_sender_raises(db):
    project_id = await _setup_project(db)
    service = ChatService(db)
    thread = await service.get_or_create_thread(project_id=project_id)

    with pytest.raises(ChatError):
        await service.post_message(thread.id, "robot", "test")


@pytest.mark.asyncio
async def test_post_message_empty_content_raises(db):
    project_id = await _setup_project(db)
    service = ChatService(db)
    thread = await service.get_or_create_thread(project_id=project_id)

    with pytest.raises(ChatError):
        await service.post_message(thread.id, "client", "   ")


@pytest.mark.asyncio
async def test_list_messages_ordered_asc(db):
    project_id = await _setup_project(db)
    service = ChatService(db)
    thread = await service.get_or_create_thread(project_id=project_id)

    await service.post_message(thread.id, "client", "msg1")
    await service.post_message(thread.id, "admin", "msg2")
    await service.post_message(thread.id, "client", "msg3")

    messages = await service.list_messages(thread.id)
    assert len(messages) == 3
    assert messages[0].content == "msg1"
    assert messages[2].content == "msg3"


@pytest.mark.asyncio
async def test_sla_status_no_breach_when_admin_responded(db):
    project_id = await _setup_project(db)
    service = ChatService(db)
    thread = await service.get_or_create_thread(project_id=project_id)

    await service.post_message(thread.id, "client", "q")
    await service.post_message(thread.id, "admin", "a")

    sla = await service.get_sla_status(thread.id)
    assert sla["sla_breached"] is False
    assert sla["reason"] == "admin_responded"


@pytest.mark.asyncio
async def test_sla_status_breach_when_admin_late(db):
    project_id = await _setup_project(db)
    service = ChatService(db)
    thread = await service.get_or_create_thread(project_id=project_id)

    # Insert client message with backdated last_client_message_at (3h ago)
    msg = await service.post_message(thread.id, "client", "urgent")
    backdated = datetime.now(timezone.utc) - timedelta(hours=3)
    thread.last_client_message_at = backdated
    await db.flush()

    sla = await service.get_sla_status(thread.id)
    assert sla["sla_breached"] is True
    assert sla["reason"] == "awaiting_admin_response"
    assert sla["minutes_since_last_client_msg"] >= 180


@pytest.mark.asyncio
async def test_sla_no_breach_no_client_messages_yet(db):
    project_id = await _setup_project(db)
    service = ChatService(db)
    thread = await service.get_or_create_thread(project_id=project_id)

    sla = await service.get_sla_status(thread.id)
    assert sla["sla_breached"] is False
    assert sla["reason"] == "no_client_messages_yet"


# ════════════════════════════════════════════════════════════════════
# CLUSTER 5 Phase 5A delta · read_at + audit_log Sub-atom 5.A
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_post_message_persists_read_at_null_by_default(db):
    """read_at column starts NULL until counterparty mark-read endpoint."""
    project_id = await _setup_project(db)
    service = ChatService(db)
    thread = await service.get_or_create_thread(project_id=project_id)

    msg = await service.post_message(thread.id, "client", "test")
    await db.refresh(msg)
    assert msg.read_at is None


@pytest.mark.asyncio
async def test_post_message_emits_audit_log_chat_sent(db):
    """ChatService.post_message emits audit_log chat.message.sent Sub-atom 5.A."""
    project_id = await _setup_project(db)
    service = ChatService(db)
    thread = await service.get_or_create_thread(project_id=project_id)

    msg = await service.post_message(
        thread.id, "client", "audit trail content",
    )

    row = (await db.execute(
        text(
            "SELECT accion, project_id, payload_new::text FROM audit_log "
            "WHERE tabla = 'chat_messages' "
            "AND registro_id = :rid "
            "ORDER BY timestamp DESC LIMIT 1"
        ),
        {"rid": str(msg.id)},
    )).first()
    assert row is not None
    assert row[0] == "chat.message.sent"
    assert str(row[1]) == str(project_id)
    assert "audit trail content" in row[2]


@pytest.mark.asyncio
async def test_mark_messages_read_bulk_admin_marks_client_messages(db):
    """Admin reading marks all sender_type=client messages as read."""
    project_id = await _setup_project(db)
    service = ChatService(db)
    thread = await service.get_or_create_thread(project_id=project_id)

    await service.post_message(thread.id, "client", "msg1")
    await service.post_message(thread.id, "client", "msg2")
    await service.post_message(thread.id, "admin", "reply")

    marked = await service.mark_messages_read(
        thread.id, reader_role="admin",
    )
    assert marked == 2

    all_msgs = await service.list_messages(thread.id)
    client_msgs = [m for m in all_msgs if m.sender_type == "client"]
    admin_msgs = [m for m in all_msgs if m.sender_type == "admin"]
    assert all(m.read_at is not None for m in client_msgs)
    assert all(m.read_at is None for m in admin_msgs)


@pytest.mark.asyncio
async def test_mark_messages_read_idempotent_no_double_audit(db):
    """Second mark-read call returns 0 · NO duplicate audit_log emission."""
    project_id = await _setup_project(db)
    service = ChatService(db)
    thread = await service.get_or_create_thread(project_id=project_id)

    await service.post_message(thread.id, "client", "msg1")
    first = await service.mark_messages_read(thread.id, reader_role="admin")
    second = await service.mark_messages_read(thread.id, reader_role="admin")

    assert first == 1
    assert second == 0

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


@pytest.mark.asyncio
async def test_mark_messages_read_invalid_role_raises(db):
    project_id = await _setup_project(db)
    service = ChatService(db)
    thread = await service.get_or_create_thread(project_id=project_id)

    with pytest.raises(ChatError):
        await service.mark_messages_read(thread.id, reader_role="auditor")
