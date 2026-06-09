"""Tests for TimesheetService + admin API · MB-7.bis atom 7.bis.5."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from backend.app.motors.m23_retainer.timesheet_service import TimesheetService
from backend.tests.conftest import _admin_setup


pytestmark = pytest.mark.asyncio


async def _seed_clients(db, n: int = 2) -> list[uuid.UUID]:
    ids = []
    async with _admin_setup(db):
        for i in range(n):
            cid = uuid.uuid4()
            cif = f"B{uuid.uuid4().hex[:8].upper()}"
            await db.execute(text(
                "INSERT INTO clients (id, nombre, cif, created_at) "
                "VALUES (:id, :n, :cif, now())"
            ), {"id": str(cid), "n": f"Cliente {i+1}", "cif": cif})
            ids.append(cid)
    await db.flush()
    return ids


async def test_start_session_creates_open_entry(db):
    [cid] = await _seed_clients(db, n=1)
    svc = TimesheetService()
    entry = await svc.start_session(
        db, client_id=cid, endpoint_path="/api/v1/projects/foo",
    )
    assert entry.ended_at is None
    assert entry.duration_minutes is None
    assert entry.source == "auto_endpoint"
    assert entry.endpoint_path == "/api/v1/projects/foo"


async def test_end_session_computes_duration(db):
    [cid] = await _seed_clients(db, n=1)
    svc = TimesheetService()
    entry = await svc.start_session(db, client_id=cid)
    # Force started_at backwards 15 min for deterministic compute
    entry.started_at = datetime.now(timezone.utc) - timedelta(minutes=15)
    await db.flush()

    closed = await svc.end_session(db, entry.id)
    assert closed is not None
    assert closed.ended_at is not None
    assert closed.duration_minutes is not None
    assert 14 <= closed.duration_minutes <= 16


async def test_end_session_idempotent_on_already_closed(db):
    [cid] = await _seed_clients(db, n=1)
    svc = TimesheetService()
    entry = await svc.add_manual_entry(
        db, client_id=cid, started_at=datetime.now(timezone.utc),
        duration_minutes=30,
    )
    # Calling end_session on closed entry should be a no-op
    same = await svc.end_session(db, entry.id)
    assert same is not None
    assert same.duration_minutes == 30


async def test_add_manual_entry_sets_override_flag(db):
    [cid] = await _seed_clients(db, n=1)
    svc = TimesheetService()
    entry = await svc.add_manual_entry(
        db, client_id=cid,
        started_at=datetime.now(timezone.utc) - timedelta(hours=2),
        duration_minutes=45,
        notes="Conferencia preventa",
    )
    assert entry.manual_override is True
    assert entry.source == "manual"
    assert entry.duration_minutes == 45
    assert entry.notes == "Conferencia preventa"


async def test_top_clients_orders_by_total_minutes(db):
    ids = await _seed_clients(db, n=2)
    svc = TimesheetService()
    now = datetime.now(timezone.utc)
    await svc.add_manual_entry(
        db, client_id=ids[0], started_at=now - timedelta(days=1),
        duration_minutes=30,
    )
    await svc.add_manual_entry(
        db, client_id=ids[1], started_at=now - timedelta(days=1),
        duration_minutes=90,
    )
    await svc.add_manual_entry(
        db, client_id=ids[1], started_at=now - timedelta(hours=4),
        duration_minutes=60,
    )

    top = await svc.get_top_clients_by_hours(db, limit=3)
    assert len(top) == 2
    # Cliente 2 (ids[1]) total 150 min > Cliente 1 (ids[0]) total 30 min
    assert top[0].client_id == str(ids[1])
    assert top[0].total_minutes == 150
    assert top[1].client_id == str(ids[0])
    assert top[1].total_minutes == 30


async def test_monthly_total_minutes_current_month(db):
    [cid] = await _seed_clients(db, n=1)
    svc = TimesheetService()
    now = datetime.now(timezone.utc)
    # Entry this month
    await svc.add_manual_entry(
        db, client_id=cid, started_at=now - timedelta(hours=1),
        duration_minutes=20,
    )
    # Entry well before this month (negative)
    await svc.add_manual_entry(
        db, client_id=cid,
        started_at=now.replace(day=1) - timedelta(days=40),
        duration_minutes=999,
    )
    total = await svc.get_monthly_total_minutes(db)
    assert total == 20


async def test_get_entries_filtered_by_client(db):
    ids = await _seed_clients(db, n=2)
    svc = TimesheetService()
    now = datetime.now(timezone.utc)
    await svc.add_manual_entry(
        db, client_id=ids[0], started_at=now, duration_minutes=10,
    )
    await svc.add_manual_entry(
        db, client_id=ids[1], started_at=now, duration_minutes=20,
    )

    entries = await svc.get_entries_filtered(db, client_id=ids[0])
    assert len(entries) == 1
    assert entries[0].client_id == ids[0]
    assert entries[0].duration_minutes == 10
