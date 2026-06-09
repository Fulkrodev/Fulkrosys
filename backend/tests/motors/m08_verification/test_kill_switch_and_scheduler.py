"""M8 v5.1 — Tests de kill switch (SIGTERM <5s) y scheduler nocturno."""
from __future__ import annotations

import asyncio
import os
import time
import uuid
from datetime import datetime, time as time_type, timedelta, timezone

import pytest

from backend.app.database import set_tenant_context
from backend.app.motors.m08_verification.kill_switch import (
    force_kill_run_processes,
    register_subprocess,
    request_kill,
    tracked_subprocess,
    unregister_subprocess,
)
from backend.app.motors.m08_verification.scheduler import (
    dispatch_due_runs,
    is_in_scan_window,
    list_due_runs,
)
from backend.app.motors.m08_verification.service import (
    RunStateError,
    VerificationService,
)
from backend.tests.conftest import setup_test_project


# ════════════════════════════════════════════════════════════════════
# Kill switch — registro y kill
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_kill_switch_marks_db_and_kills_in_under_5s(db):
    """E2E: lanza un sleep largo, registra su pgid, request_kill,
    verifica muerte en <5s."""
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(
        db, client_id=uuid.UUID(client_id),
        project_id=uuid.UUID(project_id),
    )
    svc = VerificationService(db)
    run = await svc.create_run(
        project_id=uuid.UUID(project_id),
        category="BASICO",
        mode="internal",
    )

    # Lanzar sleep 60s en su propio process group
    proc = await asyncio.create_subprocess_exec(
        "sleep", "60",
        preexec_fn=os.setsid,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    pid = proc.pid
    pgid = os.getpgid(pid)
    register_subprocess(run.id, pgid)

    start = time.monotonic()
    # request_kill marca BD + intenta SIGTERM inmediato
    await request_kill(db, run.id)
    # Esperar muerte del proceso
    try:
        await asyncio.wait_for(proc.wait(), timeout=5.0)
    except asyncio.TimeoutError:
        # Como ultima medida fuerza SIGKILL
        force_kill_run_processes(run.id)
        await asyncio.wait_for(proc.wait(), timeout=2.0)
    elapsed = time.monotonic() - start

    unregister_subprocess(run.id, pgid)
    assert elapsed < 5.0, f"Kill tardo {elapsed:.2f}s (debe ser <5s)"
    assert proc.returncode != 0  # killed (-15 SIGTERM o -9 SIGKILL)

    # Verificar BD
    refreshed = await svc.get_run(run.id)
    assert refreshed.status == "cancelled"
    assert refreshed.cancel_requested_at is not None


@pytest.mark.asyncio
async def test_kill_idempotent(db):
    """Llamar request_kill dos veces no rompe."""
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(
        db, client_id=uuid.UUID(client_id),
        project_id=uuid.UUID(project_id),
    )
    svc = VerificationService(db)
    run = await svc.create_run(
        project_id=uuid.UUID(project_id), category="BASICO",
    )
    r1 = await request_kill(db, run.id)
    r2 = await request_kill(db, run.id)
    assert r1.id == r2.id
    assert r1.cancel_requested_at == r2.cancel_requested_at


@pytest.mark.asyncio
async def test_kill_rejects_completed_runs(db):
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(
        db, client_id=uuid.UUID(client_id),
        project_id=uuid.UUID(project_id),
    )
    svc = VerificationService(db)
    run = await svc.create_run(
        project_id=uuid.UUID(project_id), category="BASICO",
    )
    run.status = "completed"
    run.completed_at = datetime.now(timezone.utc)
    await db.flush()
    with pytest.raises(RunStateError):
        await request_kill(db, run.id)


def test_register_subprocess_idempotent_set():
    rid = uuid.uuid4()
    register_subprocess(rid, 12345)
    register_subprocess(rid, 12345)
    register_subprocess(rid, 67890)
    # No duplica
    from backend.app.motors.m08_verification.kill_switch import _REGISTRY
    pgids = _REGISTRY.pgids_for(rid)
    assert pgids == {12345, 67890}
    unregister_subprocess(rid, 12345)
    unregister_subprocess(rid, 67890)


@pytest.mark.asyncio
async def test_tracked_subprocess_context_unregisters():
    """tracked_subprocess() registra y al salir desregistra."""
    proc = await asyncio.create_subprocess_exec(
        "sleep", "1", preexec_fn=os.setsid,
        stdout=asyncio.subprocess.DEVNULL,
    )
    rid = uuid.uuid4()
    with tracked_subprocess(rid, proc.pid) as pgid:
        from backend.app.motors.m08_verification.kill_switch import _REGISTRY
        assert pgid in _REGISTRY.pgids_for(rid)
    # Tras salir del context, desregistrado
    from backend.app.motors.m08_verification.kill_switch import _REGISTRY
    assert pgid not in _REGISTRY.pgids_for(rid)
    await proc.wait()


# ════════════════════════════════════════════════════════════════════
# Scheduler — ventana
# ════════════════════════════════════════════════════════════════════

def test_is_in_scan_window_default_22_06():
    # 23:30 UTC dentro
    night = datetime(2026, 4, 21, 23, 30, tzinfo=timezone.utc)
    assert is_in_scan_window(night) is True
    # 03:00 UTC dentro
    early = datetime(2026, 4, 22, 3, 0, tzinfo=timezone.utc)
    assert is_in_scan_window(early) is True
    # 14:00 UTC fuera
    afternoon = datetime(2026, 4, 21, 14, 0, tzinfo=timezone.utc)
    assert is_in_scan_window(afternoon) is False
    # Justo a las 22:00 dentro; 06:00 fuera (intervalo abierto)
    assert is_in_scan_window(datetime(2026, 4, 21, 22, 0, tzinfo=timezone.utc))
    assert not is_in_scan_window(datetime(2026, 4, 22, 6, 0, tzinfo=timezone.utc))


def test_is_in_scan_window_custom_window():
    # Ventana 02:00-04:00
    assert is_in_scan_window(
        datetime(2026, 4, 21, 3, 0, tzinfo=timezone.utc),
        window_start=time_type(2), window_end=time_type(4),
    ) is True
    assert not is_in_scan_window(
        datetime(2026, 4, 21, 5, 0, tzinfo=timezone.utc),
        window_start=time_type(2), window_end=time_type(4),
    )


# ════════════════════════════════════════════════════════════════════
# Scheduler — list_due_runs y dispatch
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_list_due_runs_returns_only_scheduled_due(db):
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(
        db, client_id=uuid.UUID(client_id),
        project_id=uuid.UUID(project_id),
    )
    svc = VerificationService(db)
    # Run scheduled en el pasado → due
    r1 = await svc.create_run(
        project_id=uuid.UUID(project_id), category="BASICO",
    )
    r1.status = "scheduled"
    r1.scheduled_start = datetime.now(timezone.utc) - timedelta(minutes=10)
    # Run scheduled en el futuro → no due todavia
    r2 = await svc.create_run(
        project_id=uuid.UUID(project_id), category="BASICO",
    )
    r2.status = "scheduled"
    r2.scheduled_start = datetime.now(timezone.utc) + timedelta(hours=2)
    # Run pending → no due (no scheduled)
    await svc.create_run(
        project_id=uuid.UUID(project_id), category="BASICO",
    )
    # Run scheduled en el pasado pero cancel_requested → no due
    r4 = await svc.create_run(
        project_id=uuid.UUID(project_id), category="BASICO",
    )
    r4.status = "scheduled"
    r4.scheduled_start = datetime.now(timezone.utc) - timedelta(minutes=5)
    r4.cancel_requested_at = datetime.now(timezone.utc)
    await db.flush()

    due = await list_due_runs(db)
    due_ids = {r.id for r in due}
    assert r1.id in due_ids
    assert r2.id not in due_ids
    assert r4.id not in due_ids


@pytest.mark.asyncio
async def test_dispatch_skips_outside_window_when_enforce(db):
    """Si no estamos en ventana y enforce_window=True → skip."""
    fake_now = datetime(2026, 4, 21, 14, 0, tzinfo=timezone.utc)
    res = await dispatch_due_runs(db, enforce_window=True, now=fake_now)
    assert res["reason"] == "outside_scan_window"
    assert res["runs_dispatched"] == 0


@pytest.mark.asyncio
async def test_dispatch_runs_when_in_window(db):
    """Forzando ventana valida, intenta dispatchar (no falla aunque
    Celery no este configurado)."""
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(
        db, client_id=uuid.UUID(client_id),
        project_id=uuid.UUID(project_id),
    )
    svc = VerificationService(db)
    r = await svc.create_run(
        project_id=uuid.UUID(project_id), category="BASICO",
    )
    r.status = "scheduled"
    r.scheduled_start = datetime.now(timezone.utc) - timedelta(minutes=5)
    await db.flush()

    # Ventana scan 22:00-06:00 UTC. Usamos "hoy 23:30 UTC" asi el
    # cutoff se calcula relativo a hoy (no a una fecha hardcoded que
    # quedaria antes que el scheduled_start del run).
    night = datetime.now(timezone.utc).replace(
        hour=23, minute=30, second=0, microsecond=0,
    )
    res = await dispatch_due_runs(db, enforce_window=True, now=night)
    assert res["runs_found"] >= 1
    # dispatched puede ser 0 si Celery no esta listo, pero runs_found > 0
