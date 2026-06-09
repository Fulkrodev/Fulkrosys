"""FRENTE N · SIEM · agregación de eventos de seguridad + correlación determinista.

Sin tablas nuevas (ADR-025 · ON-QUERY). Reglas R1 (deterministas · sin LLM).
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text as sa_text

from backend.app.motors.m_siem.service import (
    aggregate_security_events,
    compute_correlations,
    normalize_severity,
    siem_overview,
)
from backend.tests.conftest import setup_test_project

pytestmark = pytest.mark.asyncio


async def _seed_run(db, pid: str) -> uuid.UUID:
    run_id = uuid.uuid4()
    await db.execute(sa_text(
        "INSERT INTO verification_runs (id, project_id, category, mode, status, "
        "scope_jsonb, created_at, updated_at) VALUES (:id, :pid, 'MEDIO', "
        "'internal', 'completed', '{}'::jsonb, now(), now())"
    ), {"id": str(run_id), "pid": pid})
    return run_id


async def _seed_finding(db, pid, run_id, *, severity, title, status="open"):
    await db.execute(sa_text(
        "INSERT INTO verification_findings (id, project_id, run_id, finding_hash, "
        "title, description, severity, affected_host, remediation_summary, status, "
        "created_at, updated_at) VALUES (gen_random_uuid(), :pid, :rid, :h, :t, "
        "'desc', :sev, '10.0.0.5', 'remediar', :st, now(), now())"
    ), {"pid": pid, "rid": str(run_id), "h": uuid.uuid4().hex, "t": title,
        "sev": severity, "st": status})


async def _seed_incident(db, pid, *, severidad, notificado=False):
    await db.execute(sa_text(
        "INSERT INTO incidents (id, project_id, fecha, severidad, descripcion, "
        "notificado_lucia, workflow_state, created_at, updated_at) VALUES "
        "(gen_random_uuid(), :pid, now(), :sev, 'brecha', :notif, 'created', "
        "now(), now())"
    ), {"pid": pid, "sev": severidad, "notif": notificado})


async def test_normalize_severity_es_en():  # noqa: RUF029
    assert normalize_severity("critica") == "critical"
    assert normalize_severity("ALTA") == "high"
    assert normalize_severity("media") == "medium"
    assert normalize_severity("critical") == "critical"
    assert normalize_severity(None) == "medium"


async def test_siem_aggregates_and_correlates(db):
    _, pid = await setup_test_project(db)
    run_id = await _seed_run(db, pid)
    # 3 hallazgos críticos de pentest sin resolver + 1 incidente crítico no notif
    await _seed_finding(db, pid, run_id, severity="critical", title="Log4Shell")
    await _seed_finding(db, pid, run_id, severity="critical", title="SQLi")
    await _seed_finding(db, pid, run_id, severity="high", title="XSS")
    await _seed_incident(db, pid, severidad="critica", notificado=False)
    await db.flush()

    events = await aggregate_security_events(db, project_id=uuid.UUID(pid))
    assert len(events) >= 4
    sources = {e.source for e in events}
    assert "pentest" in sources and "incident" in sources
    # ordenado por severidad desc → el primero es crítico
    assert events[0].severity == "critical"

    corr = compute_correlations(events)
    rule_ids = {c.rule_id for c in corr}
    assert "multiple_critical_pentest_findings" in rule_ids
    assert "incident_plus_critical_vuln" in rule_ids
    assert "incident_not_notified_lucia" in rule_ids

    ov = await siem_overview(db, project_id=uuid.UUID(pid))
    assert ov["by_severity"]["critical"] >= 3
    assert ov["by_source"]["pentest"] >= 3
    assert ov["correlation_count"] >= 3
    assert ov["active_events"] >= 4


async def test_siem_counts_exact_independent_of_display_limit(db):
    """Fix verify N-siem: los conteos del overview son EXACTOS (COUNT GROUP BY),
    no se truncan por el limit de display ni sub-cuentan severidades bajas."""
    _, pid = await setup_test_project(db)
    run_id = await _seed_run(db, pid)
    # 5 hallazgos (2 critical + 3 low) · display limit pequeño
    await _seed_finding(db, pid, run_id, severity="critical", title="c1")
    await _seed_finding(db, pid, run_id, severity="critical", title="c2")
    for t in ("l1", "l2", "l3"):
        await _seed_finding(db, pid, run_id, severity="low", title=t)
    await db.flush()

    ov = await siem_overview(db, project_id=uuid.UUID(pid), limit=2)
    # la muestra mostrada respeta el limit...
    assert len(ov["events"]) == 2
    # ...pero los CONTEOS reflejan TODO (no truncados · low no sub-contadas)
    assert ov["total_events"] == 5
    assert ov["by_severity"]["critical"] == 2
    assert ov["by_severity"]["low"] == 3
    assert ov["active_events"] == 5


async def test_siem_resolved_findings_not_in_correlations(db):
    _, pid = await setup_test_project(db)
    run_id = await _seed_run(db, pid)
    # hallazgos críticos pero TODOS remediados → no disparan correlación
    for t in ("a", "b", "c"):
        await _seed_finding(db, pid, run_id, severity="critical", title=t,
                            status="remediated")
    await db.flush()
    events = await aggregate_security_events(db, project_id=uuid.UUID(pid))
    corr = compute_correlations(events)
    assert "multiple_critical_pentest_findings" not in {c.rule_id for c in corr}
