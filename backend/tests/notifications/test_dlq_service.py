"""DLQ service tests · Phase 11.3 Ejecutable 6 Sesión 3B-2B.11.

Verifica:
1. list_dlq_entries returns failed events con retry_count >= MAX_RETRIES
2. get_dlq_summary aggregated counts + by_event_type breakdown
3. reprocess_dlq_entry resets status='queued' + retry_count=0
4. resolve_dlq_entry soft-delete + audit_log emit notification.dlq.resolved
5. atomic UPDATE WHERE guard protects concurrent reprocess race
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text as sa_text

from backend.app.notifications.dlq_service import (
    MAX_RETRIES,
    get_dlq_summary,
    list_dlq_entries,
    reprocess_dlq_entry,
    resolve_dlq_entry,
)
from backend.tests.conftest import _admin_setup, setup_test_project


async def _insert_notification_event(
    db, *, event_type: str, recipient_email: str,
    project_id: uuid.UUID, status: str = "failed",
    retry_count: int = MAX_RETRIES, error: str = "SMTP timeout",
) -> uuid.UUID:
    """Helper · insert raw NotificationEvent row bypass orchestrator."""
    event_id = uuid.uuid4()
    await db.execute(sa_text(
        "INSERT INTO notification_events "
        "(id, event_type, recipient_email, project_id, channels_attempted, "
        "channels_succeeded, channels_failed, payload_jsonb, status, "
        "retry_count, error, created_at, updated_at) "
        "VALUES (:id, :et, :em, :pid, :att, :suc, :fai, :pay, :st, :rc, :err, "
        "now(), now())"
    ), {
        "id": str(event_id),
        "et": event_type,
        "em": recipient_email,
        "pid": str(project_id),
        "att": '["email", "portal_sse"]',
        "suc": "[]",
        "fai": '["email", "portal_sse"]',
        "pay": '{}',
        "st": status,
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
async def test_reprocess_dlq_entry_resets_status_and_retry_count(db):
    """reprocess marks status='queued' + retry_count=0 + atomic guard."""
    client_id, project_id_str = await setup_test_project(db)
    project_id = uuid.UUID(project_id_str)

    async with _admin_setup(db):
        event_id = await _insert_notification_event(
            db, event_type="phase_unblocked",
            recipient_email="reprocess@test.com",
            project_id=project_id,
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
    assert row[0] == "queued"
    assert row[1] == 0


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
