"""Tests Celery tasks NotificationOrchestrator MB-16.4 (ADR-039).

Cubre:
- ``scan_client_inactivity_with_session`` detecta usuarios inactivos
  + dispara AlertService + NotificationOrchestrator.
- ``redispatch_event_with_session`` re-dispatcha event failed con
  template + render_context · idempotencia para already_delivered.
- Beat schedule contiene ``notifications.scan_client_inactivity`` daily 09:00.
- Tasks include registry contiene ``backend.app.notifications.tasks``.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text

from backend.app.auth.crypto import hash_password
from backend.app.config import get_settings
from backend.app.core.email.sender import EmailResult
from backend.app.models.alerts import Alert
from backend.app.models.client_portal import ClientUser
from backend.app.models.notifications import NotificationEvent
from backend.app.notifications import NotificationOrchestrator
from backend.app.notifications.tasks import (
    redispatch_event_with_session,
    scan_client_inactivity_with_session,
)
from backend.tests.conftest import _admin_setup


class _FakeEmailSender:
    """Stub EmailSender · ok configurable + capture calls."""

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


async def _bootstrap_inactive_user(
    db, *, days_since_login: int = 30,
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    """Crea Client + ClientUser + Project para scan_client_inactivity."""
    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    user_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    last_login = datetime.now(timezone.utc) - timedelta(days=days_since_login)
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO clients (id, nombre, cif, created_at) "
                "VALUES (:id, 'T-Inactive', :cif, now())"
            ),
            {"id": str(client_id), "cif": cif},
        )
        await db.execute(
            text(
                "INSERT INTO projects (id, client_id, nombre, created_at) "
                "VALUES (:id, :cid, 'P-Inactive', now())"
            ),
            {"id": str(project_id), "cid": str(client_id)},
        )
        user = ClientUser(
            id=user_id,
            client_id=client_id,
            email=f"inactive-{uuid.uuid4().hex[:8]}@example.com",
            password_hash=hash_password("TestP@ssw0rd123!"),
            must_change_password=False,
            last_login=last_login,
        )
        db.add(user)
        await db.flush()
    return client_id, project_id, user_id


@pytest.fixture(autouse=True)
def _reset_settings():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_scan_client_inactivity_finds_inactive_users(db, monkeypatch):
    monkeypatch.setattr(
        "backend.app.notifications.tasks.get_email_sender", lambda: None,
        raising=False,
    )
    cid, pid, uid = await _bootstrap_inactive_user(db, days_since_login=20)

    fake = _FakeEmailSender()

    import backend.app.notifications.tasks as tasks_mod

    original_orch = tasks_mod.NotificationOrchestrator

    def patched_orch(db, **kw):
        return original_orch(db, email_sender=fake)

    monkeypatch.setattr(tasks_mod, "NotificationOrchestrator", patched_orch)

    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    stats = await scan_client_inactivity_with_session(db)
    await db.execute(text("RESET ROLE"))

    assert stats["inactive_count"] >= 1
    assert stats["alerts_created"] >= 1
    assert stats["notifications_enqueued"] >= 1
    assert stats["threshold_days"] == 14


@pytest.mark.asyncio
async def test_scan_creates_alert_in_alert_queue(db, monkeypatch):
    cid, pid, uid = await _bootstrap_inactive_user(db, days_since_login=21)

    fake = _FakeEmailSender()
    import backend.app.notifications.tasks as tasks_mod

    original = tasks_mod.NotificationOrchestrator
    monkeypatch.setattr(
        tasks_mod, "NotificationOrchestrator",
        lambda db, **kw: original(db, email_sender=fake),
    )

    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    await scan_client_inactivity_with_session(db)
    await db.execute(text("RESET ROLE"))

    # Post role-surgery (commit 1db2d420) fulkro_app YA NO bypassa RLS · leer la
    # fila persistida exige contexto de tenant explicito (set_config tx-local).
    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": str(pid)},
    )
    alerts = (await db.execute(
        select(Alert).where(
            Alert.category == "client_inactivity",
            Alert.project_id == pid,
        )
    )).scalars().all()

    assert len(alerts) >= 1
    alert = alerts[0]
    assert alert.severity == "warning"
    assert alert.triggered_by == "notifications.scan_client_inactivity"
    assert alert.metadata_jsonb["client_user_id"] == str(uid)


@pytest.mark.asyncio
async def test_scan_enqueues_notification_event_to_marcos(db, monkeypatch):
    cid, pid, uid = await _bootstrap_inactive_user(db, days_since_login=15)
    fake = _FakeEmailSender()

    import backend.app.notifications.tasks as tasks_mod

    original = tasks_mod.NotificationOrchestrator
    monkeypatch.setattr(
        tasks_mod, "NotificationOrchestrator",
        lambda db, **kw: original(db, email_sender=fake),
    )

    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    await scan_client_inactivity_with_session(db)
    await db.execute(text("RESET ROLE"))

    # Post role-surgery (commit 1db2d420) fulkro_app YA NO bypassa RLS · la policy
    # notification_events_isolation exige contexto de tenant para ver la fila.
    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": str(pid)},
    )
    events = (await db.execute(
        select(NotificationEvent).where(
            NotificationEvent.event_type == "client_inactivity_admin",
        )
    )).scalars().all()

    assert len(events) >= 1
    matching = [
        e for e in events
        if e.payload_jsonb.get("client_user_id") == str(uid)
    ]
    assert len(matching) == 1
    event = matching[0]
    assert event.template_used == "client_inactivity_admin"
    assert event.payload_jsonb["client_user_id"] == str(uid)
    assert "_render_context" in event.payload_jsonb
    assert event.recipient_email == get_settings().marcos_admin_email


@pytest.mark.asyncio
async def test_scan_skips_recently_active(db, monkeypatch):
    """Usuarios con last_login dentro del threshold NO disparan alerts."""
    cid_active = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO clients (id, nombre, cif, created_at) "
                "VALUES (:id, 'T-Active', :cif, now())"
            ),
            {"id": str(cid_active), "cif": cif},
        )
        recent_user = ClientUser(
            client_id=cid_active,
            email=f"active-{uuid.uuid4().hex[:8]}@example.com",
            password_hash=hash_password("TestP@ssw0rd123!"),
            last_login=datetime.now(timezone.utc) - timedelta(days=2),
        )
        db.add(recent_user)
        await db.flush()
        recent_user_id = recent_user.id

    fake = _FakeEmailSender()
    import backend.app.notifications.tasks as tasks_mod
    original = tasks_mod.NotificationOrchestrator
    monkeypatch.setattr(
        tasks_mod, "NotificationOrchestrator",
        lambda db, **kw: original(db, email_sender=fake),
    )

    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    await scan_client_inactivity_with_session(db)
    await db.execute(text("RESET ROLE"))

    notif_events = (await db.execute(
        select(NotificationEvent).where(
            NotificationEvent.event_type == "client_inactivity_admin",
        )
    )).scalars().all()
    notif_user_ids = {
        e.payload_jsonb.get("client_user_id") for e in notif_events
    }
    assert str(recent_user_id) not in notif_user_ids


@pytest.mark.asyncio
async def test_redispatch_event_with_template_context(db, monkeypatch):
    project_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    cid = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO clients (id, nombre, cif, created_at) "
                "VALUES (:id, 'T-Redisp', :cif, now())"
            ),
            {"id": str(cid), "cif": cif},
        )
        await db.execute(
            text(
                "INSERT INTO projects (id, client_id, nombre, created_at) "
                "VALUES (:id, :cid, 'P-Redisp', now())"
            ),
            {"id": str(project_id), "cid": str(cid)},
        )
    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": str(project_id)},
    )

    failed_event = NotificationEvent(
        event_type="task_assigned",
        recipient_email="ana@example.com",
        project_id=project_id,
        template_used="task_assigned",
        status="failed",
        error="postmark 5xx",
        retry_count=1,
        channels_attempted=["email"],
        channels_failed=["email"],
        payload_jsonb={
            "task_id": "abc",
            "_render_context": {
                "recipient_name": "Ana",
                "project_name": "P-Redisp",
                "task_title": "Validar política",
                "task_description": "Revisar v2",
                "task_due_date": "2026-05-30",
                "cta_url": "https://fulkro.es/client-portal/tasks/abc",
            },
        },
    )
    db.add(failed_event)
    await db.flush()
    await db.refresh(failed_event)

    fake = _FakeEmailSender(ok=True)
    import backend.app.notifications.tasks as tasks_mod
    original = tasks_mod.NotificationOrchestrator
    monkeypatch.setattr(
        tasks_mod, "NotificationOrchestrator",
        lambda db, **kw: original(db, email_sender=fake),
    )

    result = await redispatch_event_with_session(db, str(failed_event.id))
    assert result["status"] == "delivered"
    assert "email" in result["channels_succeeded"]
    assert result["redispatch_of"] == str(failed_event.id)
    assert len(fake.calls) == 1
    assert fake.calls[0]["to"] == "ana@example.com"


@pytest.mark.asyncio
async def test_redispatch_event_already_delivered_skip(db):
    project_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    cid = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO clients (id, nombre, cif, created_at) "
                "VALUES (:id, 'T-Already', :cif, now())"
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

    delivered = NotificationEvent(
        event_type="task_assigned",
        recipient_email="x@example.com",
        project_id=project_id,
        status="delivered",
    )
    db.add(delivered)
    await db.flush()
    await db.refresh(delivered)

    result = await redispatch_event_with_session(db, str(delivered.id))
    assert result["status"] == "already_delivered"


@pytest.mark.asyncio
async def test_redispatch_event_not_found(db):
    # Usa la sesión de test (transaccional, aislada) en vez de abrir una sesión
    # cruda del engine global async_session(): bajo pytest-asyncio con event
    # loops por test, las conexiones del pool global quedan ligadas al loop que
    # las creó · cualquier test previo que use el engine global podía dejar una
    # conexión que aquí disparaba InterfaceError "another operation in progress".
    # redispatch_event_with_session acepta cualquier sesión. Ejecutable 8 Pasada 16.
    result = await redispatch_event_with_session(
        db, str(uuid.uuid4()),
    )
    assert result["status"] == "not_found"


@pytest.mark.asyncio
async def test_redispatch_event_missing_render_context(db):
    project_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    cid = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO clients (id, nombre, cif, created_at) "
                "VALUES (:id, 'T-NoCtx', :cif, now())"
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

    event = NotificationEvent(
        event_type="task_assigned",
        recipient_email="x@example.com",
        project_id=project_id,
        template_used="task_assigned",
        status="failed",
        payload_jsonb={"task_id": "abc"},
    )
    db.add(event)
    await db.flush()
    await db.refresh(event)

    result = await redispatch_event_with_session(db, str(event.id))
    assert result["status"] == "failed_no_context"


def test_beat_schedule_contains_scan_inactivity():
    from backend.app.core.celery_app import get_beat_schedule

    schedule = get_beat_schedule()
    assert "notifications-scan-client-inactivity" in schedule


def test_celery_app_includes_notifications_tasks():
    from backend.app.core.celery_app import celery_app

    if hasattr(celery_app, "conf") and isinstance(celery_app.conf, dict):
        return
    include = list(celery_app.conf.include or [])
    assert "backend.app.notifications.tasks" in include
