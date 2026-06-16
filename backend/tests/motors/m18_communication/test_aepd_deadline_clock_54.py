"""H#54 (FRENTE H · DEC-5) · reloj de deadline de notificación AEPD (RGPD Art.33).

Verifica: una brecha pending con plazo 72h próximo a vencer escala a Marcos (M18)
· idempotente (no re-escala) · un plazo aún lejano NO escala · vencido marca VENCIDO.
Gemelo de C#35 (CCN-CERT/LUCIA).
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text as sa_text

from backend.app.motors.m18_communication.aepd_tasks import (
    _run_check_aepd_deadlines,
)
from backend.tests.conftest import setup_test_project

pytestmark = pytest.mark.asyncio


async def _insert_aepd_notification(
    db, project_id: str, *, hours_ago: int, deadline_hours: int = 72,
    severity: str = "high", status: str = "pending",
    requires: bool = True,
) -> uuid.UUID:
    nid = uuid.uuid4()
    await db.execute(sa_text(
        "INSERT INTO aepd_notifications (id, project_id, severity, "
        "requires_notification, notify_subjects, deadline_hours, "
        "notification_status, detected_at, created_at, updated_at) VALUES ("
        ":id, :pid, :sev, :req, false, :dh, :st, "
        "now() - make_interval(hours => :h), now(), now())"
    ), {
        "id": str(nid), "pid": project_id, "sev": severity, "req": requires,
        "dh": deadline_hours, "st": status, "h": hours_ago,
    })
    await db.flush()
    return nid


async def test_aepd_near_deadline_escalates_and_idempotent(db):
    _, project_id = await setup_test_project(db)
    # plazo 72h, detectada hace 65h → vence en ~7h (< PRE_WARNING_HOURS=12) → escala
    nid = await _insert_aepd_notification(db, project_id, hours_ago=65)

    r1 = await _run_check_aepd_deadlines(session=db)
    assert r1["escalated"] == 1, r1

    ev = (await db.execute(sa_text(
        "SELECT trigger, descripcion FROM escalation_events "
        "WHERE project_id = :pid AND "
        "trigger = 'aepd_deadline_notificacion_72h'"
    ), {"pid": project_id})).mappings().all()
    assert len(ev) == 1
    # WAVE C1 · §4.4/370: la idempotencia usa el marcador canónico [src:<id>]
    # (antes un UUID embebido en la prosa como "id=<uuid>").
    assert f"[src:{nid}]" in ev[0]["descripcion"]

    # idempotente: segunda corrida no re-escala
    r2 = await _run_check_aepd_deadlines(session=db)
    assert r2["escalated"] == 0
    assert r2["skipped_existing"] == 1


async def test_aepd_far_from_deadline_not_escalated(db):
    _, project_id = await setup_test_project(db)
    # plazo 72h, detectada hace 1h → vence en ~71h → NO escala todavía
    await _insert_aepd_notification(db, project_id, hours_ago=1)
    r = await _run_check_aepd_deadlines(session=db)
    assert r["escalated"] == 0
    assert r["checked"] >= 1


async def test_aepd_overdue_escalates(db):
    _, project_id = await setup_test_project(db)
    # plazo 72h, detectada hace 80h → VENCIDO → escala con marca VENCIDO
    await _insert_aepd_notification(db, project_id, hours_ago=80)
    r = await _run_check_aepd_deadlines(session=db)
    assert r["escalated"] == 1
    ev = (await db.execute(sa_text(
        "SELECT descripcion FROM escalation_events WHERE project_id = :pid"
    ), {"pid": project_id})).mappings().first()
    assert "VENCIDO" in ev["descripcion"]


async def test_aepd_register_only_not_escalated(db):
    _, project_id = await setup_test_project(db)
    # requires_notification=false (register_only) → NUNCA escala aunque venza
    await _insert_aepd_notification(
        db, project_id, hours_ago=80, status="register_only", requires=False,
    )
    r = await _run_check_aepd_deadlines(session=db)
    assert r["escalated"] == 0
