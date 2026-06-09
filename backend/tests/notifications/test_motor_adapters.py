"""Tests motor adapters NotificationOrchestrator MB-16.6 (ADR-039).

Cubre:
- notify_chat_admin_reply integra chat_service.post_message admin →
  enqueue_with_template chat_admin_reply.
- _safe_dispatch captura excepciones · no bloquea flow motor.
- Adapter resuelve cta_url vía DeepLinkGenerator.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select, text

from backend.app.auth.crypto import hash_password
from backend.app.core.email.sender import EmailResult
from backend.app.models.client_portal import ClientUser
from backend.app.models.notifications import NotificationEvent
from backend.app.motors.m21_portal_cliente.chat_service import ChatService
from backend.app.motors.m21_portal_cliente.models_chat import ChatThread
from backend.app.notifications import NotificationOrchestrator
from backend.app.notifications.motor_adapters import (
    notify_chat_admin_reply,
    notify_evidence_expiring,
    notify_phase_changed,
    notify_task_assigned,
)
from backend.tests.conftest import _admin_setup


class _FakeEmailSender:
    def __init__(self, *, ok: bool = True):
        self.ok = ok
        self.calls: list[dict] = []

    async def send(self, db, **kwargs):
        self.calls.append(kwargs)
        return EmailResult(
            ok=self.ok,
            message_id="msg-test" if self.ok else None,
            backend_used="mock",
            retry_count=0,
            error=None if self.ok else "stub-failure",
            email_log_id=uuid.uuid4() if self.ok else None,
        )


async def _bootstrap(db) -> tuple[uuid.UUID, uuid.UUID, ClientUser]:
    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO clients (id, nombre, cif, created_at) "
                "VALUES (:id, 'T-Adapter', :cif, now())"
            ),
            {"id": str(client_id), "cif": cif},
        )
        await db.execute(
            text(
                "INSERT INTO projects (id, client_id, nombre, created_at) "
                "VALUES (:id, :cid, 'Proyecto Adapter', now())"
            ),
            {"id": str(project_id), "cid": str(client_id)},
        )
        user = ClientUser(
            client_id=client_id,
            email=f"adapter-{uuid.uuid4().hex[:8]}@example.com",
            password_hash=hash_password("TestP@ssw0rd123!"),
            full_name="Ana López",
            must_change_password=False,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": str(project_id)},
    )
    await db.execute(
        text("SELECT set_config('app.current_client_id', :cid, true)"),
        {"cid": str(client_id)},
    )
    return client_id, project_id, user


@pytest.mark.asyncio
async def test_notify_chat_admin_reply_enqueues_event(db):
    _, project_id, user = await _bootstrap(db)
    fake = _FakeEmailSender()
    orch = NotificationOrchestrator(db, email_sender=fake)  # type: ignore[arg-type]

    outcome = await notify_chat_admin_reply(
        db,
        recipient_user_id=user.id,
        recipient_email=user.email,
        recipient_name=user.full_name or user.email,
        project_id=project_id,
        project_name="Proyecto Adapter",
        thread_id=uuid.uuid4(),
        message_preview="He revisado el ENS y...",
        orchestrator=orch,
    )

    assert outcome is not None
    assert outcome.status == "delivered"
    assert "email" in outcome.channels_succeeded
    assert "Ana López" in fake.calls[0]["html_body"]
    assert "He revisado el ENS y..." in fake.calls[0]["html_body"]


@pytest.mark.asyncio
async def test_notify_task_assigned_enqueues_event(db):
    _, project_id, user = await _bootstrap(db)
    fake = _FakeEmailSender()
    orch = NotificationOrchestrator(db, email_sender=fake)  # type: ignore[arg-type]

    outcome = await notify_task_assigned(
        db,
        recipient_user_id=user.id,
        recipient_email=user.email,
        recipient_name=user.full_name or user.email,
        project_id=project_id,
        project_name="Proyecto Adapter",
        task_id=uuid.uuid4(),
        task_title="Validar política backup",
        task_description="Revisar versión 2.3 firmada",
        task_due_date="2026-05-30",
        orchestrator=orch,
    )

    assert outcome is not None
    assert outcome.status == "delivered"
    assert "Validar política backup" in fake.calls[0]["html_body"]
    assert "2026-05-30" in fake.calls[0]["html_body"]


@pytest.mark.asyncio
async def test_notify_evidence_expiring_enqueues_event(db):
    _, project_id, user = await _bootstrap(db)
    fake = _FakeEmailSender()
    orch = NotificationOrchestrator(db, email_sender=fake)  # type: ignore[arg-type]

    outcome = await notify_evidence_expiring(
        db,
        recipient_user_id=user.id,
        recipient_email=user.email,
        recipient_name=user.full_name or user.email,
        project_id=project_id,
        project_name="P",
        evidence_id=uuid.uuid4(),
        evidence_name="Política backup v1.2",
        days_to_expire=14,
        expiration_date="2026-05-30",
        orchestrator=orch,
    )

    assert outcome is not None
    assert "Política backup v1.2" in fake.calls[0]["html_body"]
    assert "14 días" in fake.calls[0]["html_body"]


@pytest.mark.asyncio
async def test_notify_phase_changed_enqueues_event(db):
    _, project_id, user = await _bootstrap(db)
    fake = _FakeEmailSender()
    orch = NotificationOrchestrator(db, email_sender=fake)  # type: ignore[arg-type]

    outcome = await notify_phase_changed(
        db,
        recipient_user_id=user.id,
        recipient_email=user.email,
        recipient_name=user.full_name or user.email,
        project_id=project_id,
        project_name="P",
        new_phase="Auditoría",
        previous_phase="Operación",
        orchestrator=orch,
    )

    assert outcome is not None
    assert "Auditoría" in fake.calls[0]["html_body"]


@pytest.mark.asyncio
async def test_safe_dispatch_swallows_exceptions(db, monkeypatch):
    _, project_id, user = await _bootstrap(db)

    class _ExplodingOrch:
        async def enqueue_with_template(self, **kwargs):
            raise RuntimeError("simulated orchestrator failure")

    outcome = await notify_chat_admin_reply(
        db,
        recipient_user_id=user.id,
        recipient_email=user.email,
        recipient_name="X",
        project_id=project_id,
        project_name="P",
        thread_id=uuid.uuid4(),
        message_preview="msg",
        orchestrator=_ExplodingOrch(),  # type: ignore[arg-type]
    )

    assert outcome is None


@pytest.mark.asyncio
async def test_chat_service_admin_post_triggers_notification(db, monkeypatch):
    """Integration · ChatService.post_message admin → enqueue notification."""
    _, project_id, user = await _bootstrap(db)

    thread = ChatThread(
        project_id=project_id,
        client_user_id=user.id,
        subject="Consulta inicial",
        status="open",
        messages_count=0,
    )
    db.add(thread)
    await db.flush()
    await db.refresh(thread)

    fake = _FakeEmailSender()
    import backend.app.notifications.motor_adapters as adapters_mod
    original_orch = adapters_mod.NotificationOrchestrator

    def patched_orch(db, **kw):
        return original_orch(db, email_sender=fake)

    monkeypatch.setattr(
        adapters_mod, "NotificationOrchestrator", patched_orch,
    )

    chat = ChatService(db)
    await chat.post_message(
        thread_id=thread.id,
        sender_type="admin",
        content="Te he respondido tras revisar el dictamen ENS.",
    )

    events = (await db.execute(
        select(NotificationEvent).where(
            NotificationEvent.event_type == "chat_admin_reply",
            NotificationEvent.recipient_user_id == user.id,
        )
    )).scalars().all()
    assert len(events) == 1
    event = events[0]
    assert event.template_used == "chat_admin_reply"
    assert event.payload_jsonb["thread_id"] == str(thread.id)
    assert "Proyecto Adapter" in fake.calls[0]["html_body"]


@pytest.mark.asyncio
async def test_chat_service_client_post_does_not_trigger_admin_reply(db):
    """Cliente post_message NO dispara notify_chat_admin_reply."""
    _, project_id, user = await _bootstrap(db)

    thread = ChatThread(
        project_id=project_id,
        client_user_id=user.id,
        subject="X",
        status="open",
    )
    db.add(thread)
    await db.flush()
    await db.refresh(thread)

    chat = ChatService(db)
    await chat.post_message(
        thread_id=thread.id,
        sender_type="client",
        content="Tengo una duda...",
    )

    events = (await db.execute(
        select(NotificationEvent).where(
            NotificationEvent.event_type == "chat_admin_reply",
        )
    )).scalars().all()
    assert events == []
