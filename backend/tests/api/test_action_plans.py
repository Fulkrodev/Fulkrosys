"""Tests Action Plans aggregator Dashboard K.3 · sub-atom 1.D.C.A v3.11.

Cobertura:
- _classify_familia · map medida ENS → familia org/op/mp/cross
- aggregate_action_plans · empty project · 0 findings cross-motor
- aggregate_action_plans · M04 finding crítico → top 1
- aggregate_action_plans · A21 discrepancy critical → top 1
- aggregate_action_plans · limit + filters severity
- Endpoint GET /projects/{id}/action-plans · 404 NO existe + 200 con data
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from backend.app.api.v1.action_plans import (
    _classify_familia,
    aggregate_action_plans,
)
from backend.tests.conftest import _admin_setup, setup_test_project


# ════════════════════════════════════════════════════════════════════
# Familia classification
# ════════════════════════════════════════════════════════════════════


def test_classify_familia_org():
    assert _classify_familia("org.4") == "org"


def test_classify_familia_op():
    assert _classify_familia("op.acc.1") == "op"


def test_classify_familia_mp():
    assert _classify_familia("mp.if.2") == "mp"


def test_classify_familia_unknown():
    assert _classify_familia("xx.unknown") == "cross"
    assert _classify_familia(None) == "cross"
    assert _classify_familia("") == "cross"


# ════════════════════════════════════════════════════════════════════
# Aggregator tests
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_aggregate_empty_project_returns_no_items(db):
    """Project sin findings · response total=0 · items=[]."""
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)

    response = await aggregate_action_plans(db, pid)
    assert response.project_id == str(pid)
    assert response.total_count == 0
    assert response.items == []


@pytest.mark.asyncio
async def test_aggregate_m04_critical_finding_top_priority(db):
    """M04 finding crítico abierto · aparece en top 1."""
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)

    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO findings (id, project_id, severidad, estado, "
            "medida_afectada, descripcion, created_at) "
            "VALUES (:fid, :pid, 'critica', 'abierto', 'op.acc.1', "
            "'Control accesos crítico sin implementar', now())",
        ), {"fid": str(uuid.uuid4()), "pid": str(pid)})

    response = await aggregate_action_plans(db, pid)
    assert response.total_count >= 1
    assert response.items[0].severity == "critica"
    assert response.items[0].source == "m04_gap"
    assert response.items[0].familia == "op"
    assert response.items[0].motor_link is not None
    assert "/plan" in response.items[0].motor_link


@pytest.mark.asyncio
async def test_aggregate_a21_discrepancy_critical_aggregated(db):
    """A21 discrepancy critical open · incluida en aggregate."""
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)

    # Create scan_run + discrepancy critical
    scan_run_id = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO a21_scan_runs (id, project_id, run_status, "
            "motors_scanned, discrepancies_found, started_at, created_at) "
            "VALUES (:rid, :pid, 'completed', ARRAY['m04']::text[], 1, "
            "now(), now())",
        ), {"rid": str(scan_run_id), "pid": str(pid)})
        await db.execute(text(
            "INSERT INTO a21_discrepancies (id, scan_run_id, project_id, "
            "discrepancy_type, severity, motor_a, motor_b, description, "
            "resolution_status, created_at) "
            "VALUES (:did, :rid, :pid, 'findings_vs_remediation', 'critical', "
            "'m04', 'm19', 'Test critical discrepancy', 'open', now())",
        ), {
            "did": str(uuid.uuid4()), "rid": str(scan_run_id), "pid": str(pid),
        })

    response = await aggregate_action_plans(db, pid)
    sources = {item.source for item in response.items}
    assert "a21_discrepancy" in sources
    a21_items = [i for i in response.items if i.source == "a21_discrepancy"]
    assert a21_items[0].severity == "critica"
    assert "/discrepancies" in a21_items[0].motor_link


@pytest.mark.asyncio
async def test_aggregate_limit_top_n(db):
    """Limit param limita top N items."""
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)

    async with _admin_setup(db):
        # Insert 5 findings de severidad varia
        for i, sev in enumerate(["critica", "alta", "alta", "media", "media"]):
            await db.execute(text(
                "INSERT INTO findings (id, project_id, severidad, estado, "
                "medida_afectada, descripcion, created_at) "
                "VALUES (:fid, :pid, :sev, 'abierto', :med, :desc, now())",
            ), {
                "fid": str(uuid.uuid4()),
                "pid": str(pid),
                "sev": sev,
                "med": f"op.acc.{i+1}",
                "desc": f"Finding {i+1} sev {sev}",
            })

    # Pass severity_filter to include "media" (default solo crítica/alta)
    response_top3 = await aggregate_action_plans(
        db, pid, limit=3,
        severity_filter=["critica", "alta", "media"],
    )
    assert len(response_top3.items) == 3
    # Sorted by severity: critica → alta → alta
    assert response_top3.items[0].severity == "critica"


@pytest.mark.asyncio
async def test_aggregate_severity_filter_excludes_lower(db):
    """severity_filter=['critica'] solo retorna críticos."""
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)

    async with _admin_setup(db):
        for sev in ["critica", "alta", "media"]:
            await db.execute(text(
                "INSERT INTO findings (id, project_id, severidad, estado, "
                "descripcion, created_at) "
                "VALUES (:fid, :pid, :sev, 'abierto', :desc, now())",
            ), {
                "fid": str(uuid.uuid4()),
                "pid": str(pid),
                "sev": sev,
                "desc": f"sev {sev}",
            })

    response = await aggregate_action_plans(
        db, pid, severity_filter=["critica"],
    )
    severities = {item.severity for item in response.items}
    assert severities == {"critica"}


@pytest.mark.asyncio
async def test_aggregate_source_filter_excludes_others(db):
    """source_filter=['m04_gap'] solo retorna M04 (NO A21 ni M09)."""
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)

    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO findings (id, project_id, severidad, estado, "
            "descripcion, created_at) "
            "VALUES (:fid, :pid, 'critica', 'abierto', 'test M04', now())",
        ), {"fid": str(uuid.uuid4()), "pid": str(pid)})

    response = await aggregate_action_plans(
        db, pid, source_filter=["m04_gap"],
    )
    sources = {item.source for item in response.items}
    assert sources == {"m04_gap"}
    assert "a21_discrepancy" not in sources
    assert "m09_audit_prep" not in sources


@pytest.mark.asyncio
async def test_aggregate_counts_by_source_and_severity_aggregated(db):
    """counts_by_source + counts_by_severity reflejan total items."""
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)

    async with _admin_setup(db):
        for sev in ["critica", "alta"]:
            await db.execute(text(
                "INSERT INTO findings (id, project_id, severidad, estado, "
                "descripcion, created_at) "
                "VALUES (:fid, :pid, :sev, 'abierto', :desc, now())",
            ), {
                "fid": str(uuid.uuid4()),
                "pid": str(pid),
                "sev": sev,
                "desc": f"f-{sev}",
            })

    response = await aggregate_action_plans(db, pid)
    assert response.counts_by_source.get("m04_gap", 0) >= 2
    assert response.counts_by_severity.get("critica", 0) >= 1
    assert response.counts_by_severity.get("alta", 0) >= 1
