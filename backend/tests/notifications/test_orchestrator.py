"""Tests NotificationOrchestrator core service (MB-16.2 ADR-039).

Cubre flujo enqueue end-to-end con email_sender mock + SSE dispatcher
real (in-memory). Verifica:
- Persist NotificationEvent row con defaults + payload.
- Dispatch email + SSE cuando preferences enabled.
- DND timezone-aware → status=suppressed_dnd · sin dispatch.
- Preferences email_enabled=False → skip email.
- Preferences portal_sse_enabled=False → skip SSE.
- Admin event (recipient_user_id=None) → solo email · no SSE.
- Email failure → status=failed + error capturado.
- channels_attempted/succeeded/failed JSONB persistence.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select, text

from backend.app.auth.crypto import hash_password
from backend.app.core.email.sender import EmailResult
from backend.app.core.sse_dispatcher import sse_dispatcher
from backend.app.models.client_portal import ClientUser
from backend.app.models.notifications import (
    NotificationEvent,
    NotificationPreference,
)
from backend.app.notifications import NotificationOrchestrator
from backend.tests.conftest import _admin_setup


class _FakeEmailSender:
    """Stub EmailSender que registra calls + ok configurable."""

    def __init__(self, *, ok: bool = True, error: str | None = None):
        self.ok = ok
        self.error = error
        self.calls: list[dict] = []

    async def send(self, db, **kwargs):
        self.calls.append(kwargs)
        return EmailResult(
            ok=self.ok,
            message_id="msg-test-123" if self.ok else None,
            backend_used="mock",
            retry_count=0,
            error=self.error,
            email_log_id=uuid.uuid4() if self.ok else None,
        )


async def _make_user(db, email="user-orch@example.com") -> ClientUser:
    client_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO clients (id, nombre, cif, created_at) "
                "VALUES (:id, 'T-Orch', :cif, now())"
            ),
            {"id": str(client_id), "cif": cif},
        )
        user = ClientUser(
            client_id=client_id,
            email=email,
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
    await db.execute(
        text(
            "SELECT set_config('app.current_client_user_id', :uid, true)"
        ),
        {"uid": str(user.id)},
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
                "VALUES (:id, 'T-OrchProj', :cif, now())"
            ),
            {"id": str(client_id), "cif": cif},
        )
        await db.execute(
            text(
                "INSERT INTO projects (id, client_id, nombre, created_at) "
                "VALUES (:id, :cid, 'P-Orch', now())"
            ),
            {"id": str(project_id), "cid": str(client_id)},
        )
    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": str(project_id)},
    )
    return project_id


@pytest.mark.asyncio
async def test_enqueue_persists_event_row(db):
    user = await _make_user(db)
    project_id = await _make_project(db)
    fake = _FakeEmailSender()
    orch = NotificationOrchestrator(db, email_sender=fake)  # type: ignore[arg-type]

    outcome = await orch.enqueue(
        event_type="task_assigned",
        recipient_email=user.email,
        subject="Nueva tarea",
        html_body="<p>Tienes una nueva tarea</p>",
        text_body="Tienes una nueva tarea",
        recipient_user_id=user.id,
        project_id=project_id,
        template_used="task_assigned",
        payload={"task_id": "abc-123"},
    )

    assert outcome.status == "delivered"
    result = await db.execute(
        select(NotificationEvent).where(NotificationEvent.id == outcome.event_id)
    )
    event = result.scalar_one()
    assert event.event_type == "task_assigned"
    assert event.recipient_email == user.email
    assert event.template_used == "task_assigned"
    assert event.payload_jsonb == {"task_id": "abc-123"}


@pytest.mark.asyncio
async def test_enqueue_dispatches_email_when_enabled(db):
    user = await _make_user(db)
    project_id = await _make_project(db)
    fake = _FakeEmailSender()
    orch = NotificationOrchestrator(db, email_sender=fake)  # type: ignore[arg-type]

    outcome = await orch.enqueue(
        event_type="chat_admin_reply",
        recipient_email=user.email,
        subject="Respuesta de Marcos",
        html_body="<p>Te he respondido en el chat</p>",
        recipient_user_id=user.id,
        project_id=project_id,
    )

    assert "email" in outcome.channels_succeeded
    assert len(fake.calls) == 1
    assert fake.calls[0]["to"] == user.email
    assert fake.calls[0]["subject"] == "Respuesta de Marcos"


@pytest.mark.asyncio
async def test_enqueue_dispatches_sse_to_client_user_channel(db):
    user = await _make_user(db)
    project_id = await _make_project(db)
    fake = _FakeEmailSender()
    orch = NotificationOrchestrator(db, email_sender=fake)  # type: ignore[arg-type]

    received: list[dict] = []
    channel = f"client_user:{user.id}"

    async def consume():
        async for evt in sse_dispatcher.subscribe(channel):
            received.append({"type": evt.type, "data": evt.data})
            return

    consumer = asyncio.create_task(consume())
    await asyncio.sleep(0.01)

    outcome = await orch.enqueue(
        event_type="evidence_expiring",
        recipient_email=user.email,
        subject="Evidencia próxima a expirar",
        html_body="<p>Tienes una evidencia que expira en 30 días</p>",
        recipient_user_id=user.id,
        project_id=project_id,
    )

    await asyncio.wait_for(consumer, timeout=1.0)

    assert "portal_sse" in outcome.channels_succeeded
    assert len(received) == 1
    assert received[0]["type"] == "notification"
    assert received[0]["data"]["event_type"] == "evidence_expiring"


@pytest.mark.asyncio
async def test_enqueue_suppressed_when_dnd_active(db):
    user = await _make_user(db)
    project_id = await _make_project(db)

    pref = NotificationPreference(
        client_user_id=user.id,
        dnd_start_local="22:00",
        dnd_end_local="08:00",
        timezone="Europe/Madrid",
    )
    db.add(pref)
    await db.flush()

    fake = _FakeEmailSender()
    orch = NotificationOrchestrator(db, email_sender=fake)  # type: ignore[arg-type]

    now = datetime(2026, 1, 15, 23, 0, tzinfo=timezone.utc)
    outcome = await orch.enqueue(
        event_type="phase_changed",
        recipient_email=user.email,
        subject="Cambio de fase",
        html_body="<p>...</p>",
        recipient_user_id=user.id,
        project_id=project_id,
        now_utc=now,
    )

    assert outcome.status == "suppressed_dnd"
    assert outcome.suppressed_by_dnd is True
    assert len(fake.calls) == 0


@pytest.mark.asyncio
async def test_enqueue_email_disabled_skips_email(db):
    user = await _make_user(db)
    project_id = await _make_project(db)

    pref = NotificationPreference(
        client_user_id=user.id,
        email_enabled=False,
    )
    db.add(pref)
    await db.flush()

    fake = _FakeEmailSender()
    orch = NotificationOrchestrator(db, email_sender=fake)  # type: ignore[arg-type]

    outcome = await orch.enqueue(
        event_type="audit_due",
        recipient_email=user.email,
        subject="Auditoría programada",
        html_body="<p>Auditoría próxima</p>",
        recipient_user_id=user.id,
        project_id=project_id,
    )

    assert "email" not in outcome.channels_succeeded
    assert "email" not in outcome.channels_failed
    assert len(fake.calls) == 0
    assert "portal_sse" in outcome.channels_succeeded


@pytest.mark.asyncio
async def test_enqueue_sse_disabled_skips_sse(db):
    user = await _make_user(db)
    project_id = await _make_project(db)

    pref = NotificationPreference(
        client_user_id=user.id,
        portal_sse_enabled=False,
    )
    db.add(pref)
    await db.flush()

    fake = _FakeEmailSender()
    orch = NotificationOrchestrator(db, email_sender=fake)  # type: ignore[arg-type]

    outcome = await orch.enqueue(
        event_type="task_assigned",
        recipient_email=user.email,
        subject="Tarea",
        html_body="<p>...</p>",
        recipient_user_id=user.id,
        project_id=project_id,
    )

    assert "email" in outcome.channels_succeeded
    assert "portal_sse" not in outcome.channels_succeeded
    assert "portal_sse" not in outcome.channels_failed


@pytest.mark.asyncio
async def test_enqueue_admin_event_no_sse(db):
    project_id = await _make_project(db)
    fake = _FakeEmailSender()
    orch = NotificationOrchestrator(db, email_sender=fake)  # type: ignore[arg-type]

    outcome = await orch.enqueue(
        event_type="client_inactivity_admin",
        recipient_email="marcos@fulkro.es",
        subject="Cliente inactivo 14 días",
        html_body="<p>Cliente X sin actividad portal</p>",
        recipient_user_id=None,
        project_id=project_id,
        payload={"client_user_id": str(uuid.uuid4()), "days_inactive": 14},
    )

    assert outcome.status == "delivered"
    assert "email" in outcome.channels_succeeded
    assert "portal_sse" not in outcome.channels_succeeded
    assert "portal_sse" not in outcome.channels_failed


@pytest.mark.asyncio
async def test_enqueue_email_failure_marks_failed(db):
    user = await _make_user(db)
    project_id = await _make_project(db)

    pref = NotificationPreference(
        client_user_id=user.id,
        portal_sse_enabled=False,
    )
    db.add(pref)
    await db.flush()

    fake = _FakeEmailSender(ok=False, error="postmark 503 retry exhausted")
    orch = NotificationOrchestrator(db, email_sender=fake)  # type: ignore[arg-type]

    outcome = await orch.enqueue(
        event_type="task_assigned",
        recipient_email=user.email,
        subject="Tarea",
        html_body="<p>...</p>",
        recipient_user_id=user.id,
        project_id=project_id,
    )

    assert outcome.status == "failed"
    assert "email" in outcome.channels_failed
    assert outcome.error == "postmark 503 retry exhausted"


@pytest.mark.asyncio
async def test_enqueue_with_template_renders_and_dispatches(db):
    """MB-16.3: enqueue_with_template integra TemplateResolver YAML."""
    user = await _make_user(db)
    project_id = await _make_project(db)
    fake = _FakeEmailSender()

    pref = NotificationPreference(
        client_user_id=user.id,
        portal_sse_enabled=False,
    )
    db.add(pref)
    await db.flush()

    orch = NotificationOrchestrator(db, email_sender=fake)  # type: ignore[arg-type]
    outcome = await orch.enqueue_with_template(
        event_type="task_assigned",
        template_name="task_assigned",
        template_context={
            "recipient_name": "Ana López",
            "project_name": "ENS Alta",
            "task_title": "Validar Política",
            "task_description": "Revisar v2.3.",
            "task_due_date": "2026-05-20",
            "cta_url": "https://fulkro.es/client-portal/tasks/abc",
        },
        recipient_email=user.email,
        recipient_user_id=user.id,
        project_id=project_id,
        payload={"task_id": "abc"},
    )

    assert outcome.status == "delivered"
    assert "email" in outcome.channels_succeeded
    assert len(fake.calls) == 1
    sent = fake.calls[0]
    assert "Nueva tarea asignada" in sent["subject"]
    assert "ENS Alta" in sent["subject"]
    assert "Ana López" in sent["html_body"]
    assert "Validar Política" in sent["html_body"]
    assert "https://fulkro.es/client-portal/tasks/abc" in sent["html_body"]
    assert sent["template_used"] == "task_assigned"


@pytest.mark.asyncio
async def test_enqueue_persists_channels_jsonb(db):
    user = await _make_user(db)
    project_id = await _make_project(db)
    fake = _FakeEmailSender()
    orch = NotificationOrchestrator(db, email_sender=fake)  # type: ignore[arg-type]

    outcome = await orch.enqueue(
        event_type="phase_changed",
        recipient_email=user.email,
        subject="Cambio de fase",
        html_body="<p>...</p>",
        recipient_user_id=user.id,
        project_id=project_id,
    )

    row = (
        await db.execute(
            text(
                "SELECT channels_attempted, channels_succeeded, "
                "channels_failed, dispatched_at, delivered_at "
                "FROM notification_events WHERE id = :eid"
            ),
            {"eid": str(outcome.event_id)},
        )
    ).first()
    assert sorted(row[0]) == ["email", "portal_sse"]
    assert sorted(row[1]) == ["email", "portal_sse"]
    assert row[2] == []
    assert row[3] is not None
    assert row[4] is not None
