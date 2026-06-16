"""C#35 (FRENTE C) · reloj de deadline de notificación CCN-CERT/LUCIA (Art.33).

Verifica: un incidente con plazo 24/72h próximo a vencer y NO notificado escala a
Marcos (M18) · idempotente (no re-escala) · un plazo aún lejano NO escala.
"""
from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy import text as sa_text

from backend.app.motors.m19_risk.tasks import _run_check_incident_deadlines
from backend.tests.conftest import setup_test_project

pytestmark = pytest.mark.asyncio


async def _insert_incident(
    db, project_id: str, *, hours_ago: int, deadline_hours: int,
    severidad: str = "critical",
) -> uuid.UUID:
    inc_id = uuid.uuid4()
    routing = {"route_type": "lucia_federation", "deadline_hours": deadline_hours}
    await db.execute(sa_text(
        "INSERT INTO incidents (id, project_id, fecha, severidad, descripcion, "
        "notificado_lucia, workflow_state, ccn_cert_routing_decision, "
        "created_at, updated_at) VALUES (:id, :pid, "
        "now() - make_interval(hours => :h), :sev, 'incidente de prueba', "
        "false, 'created', CAST(:routing AS jsonb), now(), now())"
    ), {
        "id": str(inc_id), "pid": project_id, "h": hours_ago,
        "sev": severidad, "routing": json.dumps(routing),
    })
    await db.flush()
    return inc_id


async def test_incident_near_deadline_escalates_and_idempotent(db):
    _, project_id = await setup_test_project(db)
    # plazo 24h, ocurrió hace 20h → vence en ~4h (< PRE_WARNING_HOURS=6) → escala
    inc_id = await _insert_incident(db, project_id, hours_ago=20, deadline_hours=24)

    r1 = await _run_check_incident_deadlines(session=db)
    assert r1["escalated"] == 1, r1

    ev = (await db.execute(sa_text(
        "SELECT trigger, descripcion FROM escalation_events "
        "WHERE project_id = :pid AND "
        "trigger = 'incidente_deadline_notificacion_lucia'"
    ), {"pid": project_id})).mappings().all()
    assert len(ev) == 1
    # WAVE C1 · §4.4/370: la idempotencia usa el marcador canónico [src:<id>]
    # (antes un UUID embebido en la prosa como "id=<uuid>").
    assert f"[src:{inc_id}]" in ev[0]["descripcion"]

    # idempotente: segunda corrida no re-escala
    r2 = await _run_check_incident_deadlines(session=db)
    assert r2["escalated"] == 0
    assert r2["skipped_existing"] == 1


async def test_incident_far_from_deadline_not_escalated(db):
    _, project_id = await setup_test_project(db)
    # plazo 72h, ocurrió hace 1h → vence en ~71h → NO escala todavía
    await _insert_incident(db, project_id, hours_ago=1, deadline_hours=72)
    r = await _run_check_incident_deadlines(session=db)
    assert r["escalated"] == 0
    assert r["checked"] >= 1


async def test_incident_overdue_escalates(db):
    _, project_id = await setup_test_project(db)
    # plazo 24h, ocurrió hace 30h → VENCIDO → escala con marca VENCIDO
    await _insert_incident(db, project_id, hours_ago=30, deadline_hours=24)
    r = await _run_check_incident_deadlines(session=db)
    assert r["escalated"] == 1
    ev = (await db.execute(sa_text(
        "SELECT descripcion FROM escalation_events WHERE project_id = :pid"
    ), {"pid": project_id})).mappings().first()
    assert "VENCIDO" in ev["descripcion"]
