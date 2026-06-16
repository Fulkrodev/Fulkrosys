"""DLQ service tests · Phase 11.3 Ejecutable 6 Sesión 3B-2B.11.

Verifica:
1. list_dlq_entries returns failed events con retry_count >= MAX_RETRIES
2. get_dlq_summary aggregated counts + by_event_type breakdown
3. reprocess_dlq_entry re-envía REAL (re-render template + dispatch) y saca la
   fila de la cola DLQ (audit-roundup-W3 §4.5/390c · ya NO es un no-op)
4. resolve_dlq_entry soft-delete + audit_log emit notification.dlq.resolved
5. atomic UPDATE WHERE guard protects concurrent reprocess race
"""
from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy import text as sa_text

from backend.app.core.email.sender import EmailResult
from backend.app.notifications.dlq_service import (
    MAX_RETRIES,
    get_dlq_summary,
    list_dlq_entries,
    reprocess_dlq_entry,
    resolve_dlq_entry,
)
from backend.tests.conftest import _admin_setup, setup_test_project


class _FakeEmailSender:
    """Stub EmailSender · captura las llamadas send() para assertions."""

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


async def _insert_notification_event(
    db, *, event_type: str, recipient_email: str,
    project_id: uuid.UUID, status: str = "failed",
    retry_count: int = MAX_RETRIES, error: str = "SMTP timeout",
    payload: dict | None = None, template_used: str | None = None,
) -> uuid.UUID:
    """Helper · insert raw NotificationEvent row bypass orchestrator."""
    event_id = uuid.uuid4()
    await db.execute(sa_text(
        "INSERT INTO notification_events "
        "(id, event_type, recipient_email, project_id, channels_attempted, "
        "channels_succeeded, channels_failed, payload_jsonb, status, "
        "template_used, retry_count, error, created_at, updated_at) "
        "VALUES (:id, :et, :em, :pid, :att, :suc, :fai, :pay, :st, :tpl, :rc, "
        ":err, now(), now())"
    ), {
        "id": str(event_id),
        "et": event_type,
        "em": recipient_email,
        "pid": str(project_id),
        "att": '["email", "portal_sse"]',
        "suc": "[]",
        "fai": '["email", "portal_sse"]',
        "pay": json.dumps(payload or {}),
        "st": status,
        "tpl": template_used,
        "rc": retry_count,
        "err": error,
    })
    return event_id


@pytest.mark.asyncio
async def test_list_dlq_entries_filters_failed_max_retries(db):
    """list_dlq_entries devuelve solo failed con retry_count >= MAX_RETRIES."""
    client_id, project_id_str = await setup_test_project(db)
    project_id = uuid.UUID(project_id_str)

    async with _admin_setup(db):
        dlq_id = await _insert_notification_event(
            db, event_type="phase_unblocked",
            recipient_email="dlq@test.com",
            project_id=project_id,
            status="failed", retry_count=MAX_RETRIES,
        )
        await _insert_notification_event(
            db, event_type="phase_unblocked",
            recipient_email="ok@test.com",
            project_id=project_id,
            status="delivered", retry_count=0,
        )
        await _insert_notification_event(
            db, event_type="phase_unblocked",
            recipient_email="below@test.com",
            project_id=project_id,
            status="failed", retry_count=MAX_RETRIES - 1,
        )

        entries = await list_dlq_entries(db, project_id=project_id)

    dlq_ids = {e.event_id for e in entries}
    assert str(dlq_id) in dlq_ids
    assert all(e.retry_count >= MAX_RETRIES for e in entries)
    assert all(e.status == "failed" for e in entries)


@pytest.mark.asyncio
async def test_get_dlq_summary_counts(db):
    """get_dlq_summary aggregated total + by_event_type breakdown."""
    client_id, project_id_str = await setup_test_project(db)
    project_id = uuid.UUID(project_id_str)

    async with _admin_setup(db):
        for _ in range(3):
            await _insert_notification_event(
                db, event_type="phase_unblocked",
                recipient_email="a@test.com",
                project_id=project_id,
            )
        await _insert_notification_event(
            db, event_type="evidence_request",
            recipient_email="b@test.com",
            project_id=project_id,
        )

        summary = await get_dlq_summary(db, project_id=project_id)

    assert summary.total_count >= 4
    assert summary.last_24h_count >= 4
    assert summary.by_event_type.get("phase_unblocked", 0) >= 3
    assert summary.by_event_type.get("evidence_request", 0) >= 1


@pytest.mark.asyncio
async def test_reprocess_dlq_entry_resends_real(db, monkeypatch):
    """reprocess re-envía REAL: re-renderiza template + dispara email (mock sender).

    Antes era un no-op (solo seteaba status='queued'); ahora ejecuta el envío
    vía redispatch_event_with_session. Verifica que el EmailSender se invoca y
    que la fila DLQ original sale de la cola (status != 'failed').
    """
    client_id, project_id_str = await setup_test_project(db)
    project_id = uuid.UUID(project_id_str)

    fake = _FakeEmailSender(ok=True)
    import backend.app.notifications.tasks as tasks_mod
    original_orch = tasks_mod.NotificationOrchestrator
    monkeypatch.setattr(
        tasks_mod, "NotificationOrchestrator",
        lambda db, **kw: original_orch(db, email_sender=fake),
    )

    async with _admin_setup(db):
        event_id = await _insert_notification_event(
            db, event_type="task_assigned",
            recipient_email="reprocess@test.com",
            project_id=project_id,
            template_used="task_assigned",
            payload={
                "task_id": "abc",
                "_render_context": {
                    "recipient_name": "Ana",
                    "project_name": "Test Project",
                    "task_title": "Validar política",
                    "task_description": "Revisar v2",
                    "task_due_date": "2026-05-30",
                    "cta_url": "https://fulkro.es/client-portal/tasks/abc",
                },
            },
        )

        result = await reprocess_dlq_entry(
            db, event_id, usuario="admin@test.com",
        )
        await db.flush()

        row = (await db.execute(sa_text(
            "SELECT status, retry_count FROM notification_events WHERE id = :id"
        ), {"id": str(event_id)})).first()

    assert result["reprocessed"] is True
    assert result["rows_affected"] == 1
    # El re-envío real ocurrió: el EmailSender fue invocado.
    assert len(fake.calls) == 1
    assert fake.calls[0]["to"] == "reprocess@test.com"
    assert result["redispatch_status"] == "delivered"
    # La entrada original salió de la cola DLQ (ya no es 'failed' con retry>=MAX).
    assert row[0] == "queued"
    assert row[1] == 0


@pytest.mark.asyncio
async def test_reprocess_dlq_entry_without_render_context_no_send(db, monkeypatch):
    """Sin _render_context el re-envío no puede renderizar → NO envía (graceful).

    El reprocess sigue siendo 'reprocessed' (sacó la fila de la cola), pero el
    redispatch_status refleja failed_no_context y el sender NO se invoca.
    """
    client_id, project_id_str = await setup_test_project(db)
    project_id = uuid.UUID(project_id_str)

    fake = _FakeEmailSender(ok=True)
    import backend.app.notifications.tasks as tasks_mod
    original_orch = tasks_mod.NotificationOrchestrator
    monkeypatch.setattr(
        tasks_mod, "NotificationOrchestrator",
        lambda db, **kw: original_orch(db, email_sender=fake),
    )

    async with _admin_setup(db):
        event_id = await _insert_notification_event(
            db, event_type="phase_unblocked",
            recipient_email="noctx@test.com",
            project_id=project_id,
            template_used="phase_unblocked",
            payload={"task_id": "abc"},  # sin _render_context
        )

        result = await reprocess_dlq_entry(db, event_id)

    assert result["reprocessed"] is True
    assert result["redispatch_status"] == "failed_no_context"
    assert len(fake.calls) == 0


@pytest.mark.asyncio
async def test_reprocess_idempotent_second_call_zero_rows(db):
    """Reprocess second call NO affect (status no longer failed · WHERE guard)."""
    client_id, project_id_str = await setup_test_project(db)
    project_id = uuid.UUID(project_id_str)

    async with _admin_setup(db):
        event_id = await _insert_notification_event(
            db, event_type="phase_unblocked",
            recipient_email="idem@test.com",
            project_id=project_id,
        )

        await reprocess_dlq_entry(db, event_id)
        result2 = await reprocess_dlq_entry(db, event_id)

    assert result2["reprocessed"] is False
    assert result2["rows_affected"] == 0


@pytest.mark.asyncio
async def test_resolve_dlq_entry_soft_deletes_and_audit_log(db):
    """resolve soft-deletes (deleted_at=now) + emit audit_log notification.dlq.resolved."""
    client_id, project_id_str = await setup_test_project(db)
    project_id = uuid.UUID(project_id_str)

    async with _admin_setup(db):
        event_id = await _insert_notification_event(
            db, event_type="evidence_request",
            recipient_email="resolve@test.com",
            project_id=project_id,
        )

        result = await resolve_dlq_entry(
            db, event_id, resolution_note="Manual contact via WhatsApp",
            usuario="admin@test.com",
        )
        await db.flush()

        row = (await db.execute(sa_text(
            "SELECT deleted_at, error FROM notification_events WHERE id = :id"
        ), {"id": str(event_id)})).first()

        audit_row = (await db.execute(sa_text(
            "SELECT accion FROM audit_log "
            "WHERE registro_id = :rid AND accion = 'notification.dlq.resolved' "
            "ORDER BY seq DESC LIMIT 1"
        ), {"rid": str(event_id)})).first()

    assert result["resolved"] is True
    assert row[0] is not None
    assert "Manual contact" in (row[1] or "")
    assert audit_row is not None


@pytest.mark.asyncio
async def test_reprocess_event_not_found_returns_not_found(db):
    """reprocess inexistent event_id → reprocessed=False reason=not_found."""
    fake = uuid.uuid4()
    result = await reprocess_dlq_entry(db, fake)
    assert result["reprocessed"] is False
    assert result.get("reason") == "not_found"
