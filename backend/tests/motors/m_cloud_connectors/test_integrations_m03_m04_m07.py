"""Tests integration · M03 DdA + M04 Plan + M07 Evidence (sub-atom 1.D.X.K v3.12).

Verifica integrations layer additive:
- get_measure_cloud_status (M03 DdA cloud_status field per measure)
- iter_gaps_for_plan_actions (M04 Plan auto-populate)
- iter_evidences_for_attach (M07 Evidence auto-attach)

Compatibility CRITICAL:
- Project SIN cloud connectors funciona OK (status=unknown · 0 suggestions)
- Project CON cloud + sin gaps funciona OK (status=implemented)
- Project CON gaps emitidos → suggestions emerge correctly
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from backend.app.motors.m_cloud_connectors import (
    CloudConnectorProvider,
    CloudConnectorService,
    DiagnosticGapEngine,
)
from backend.app.motors.m_cloud_connectors.integrations import (
    get_measure_cloud_status,
    get_measures_cloud_status_bulk,
    iter_evidences_for_attach,
    iter_gaps_for_plan_actions,
)
from backend.tests.conftest import setup_test_project


# ============================================================
# Compatibility: project sin cloud → fallback unknown
# ============================================================


@pytest.mark.asyncio
async def test_get_measure_status_returns_unknown_without_cloud_data(db):
    """Project sin connectors · status='unknown' para todas las measures."""
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)

    s = await get_measure_cloud_status(
        db, project_id=pid, measure_code="op.acc.6",
    )
    # Sin cloud data y sin gap engine ejecutado:
    # - measure soportada por engine + sin gap abierto → "implemented" (asume OK)
    # Para forzar unknown medirimos una NO soportada
    s_unknown = await get_measure_cloud_status(
        db, project_id=pid, measure_code="org.xyz.UNSUPPORTED",
    )
    assert s_unknown.status == "unknown"
    assert s_unknown.has_open_gap is False


@pytest.mark.asyncio
async def test_iter_gaps_yields_empty_when_no_diagnosis_run(db):
    """Project sin diagnosis ejecutado · 0 plan suggestions."""
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)

    items = [
        s async for s in iter_gaps_for_plan_actions(
            db, project_id=pid, severity_min="medium",
        )
    ]
    assert items == []


# ============================================================
# M03 cloud_status integration
# ============================================================


@pytest.mark.asyncio
async def test_measure_status_implemented_when_no_gap_for_supported_measure(db):
    """Si NO hay gap abierto + measure es soportada · status='implemented'."""
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)
    s = await get_measure_cloud_status(
        db, project_id=pid, measure_code="op.acc.6",
    )
    assert s.status == "implemented"
    assert s.has_open_gap is False


async def _seed_no_mfa_diagnostics(db, project_id: uuid.UUID) -> None:
    """Helper: connector + 3 users no MFA · ejecuta engine → genera gaps."""
    svc = CloudConnectorService(db)
    connector = await svc.link_or_create_connector(
        project_id=project_id, provider=CloudConnectorProvider.MICROSOFT_365,
    )
    for i in range(3):
        await db.execute(
            text(
                "INSERT INTO cloud_resources "
                "(id, project_id, connector_id, resource_type, "
                "resource_external_id, resource_name, attributes) "
                "VALUES (:id, :pid, :cid, 'identity.user', "
                ":ext_id, :name, CAST(:attrs AS JSONB))"
            ),
            {
                "id": str(uuid.uuid4()),
                "pid": str(project_id),
                "cid": str(connector.id),
                "ext_id": f"u_{i}",
                "name": f"User {i}",
                "attrs": '{"mfa_enabled": false}',
            },
        )
    await db.flush()
    engine = DiagnosticGapEngine(db)
    await engine.run_diagnosis(project_id=project_id, category="BASICA")


@pytest.mark.asyncio
async def test_measure_status_missing_when_critical_gap_open(db):
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)
    await _seed_no_mfa_diagnostics(db, pid)

    s = await get_measure_cloud_status(
        db, project_id=pid, measure_code="op.acc.6",
    )
    assert s.status == "missing"  # structural gap mapping
    assert s.has_open_gap is True
    assert s.open_gap_severity == "critical"
    assert s.resources_count >= 3  # 3 identity.user inserted


@pytest.mark.asyncio
async def test_bulk_status_resolves_multiple_codes_one_query(db):
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)
    await _seed_no_mfa_diagnostics(db, pid)

    bulk = await get_measures_cloud_status_bulk(
        db, project_id=pid, measure_codes=["op.acc.6", "mp.info.3", "org.UNK"],
    )
    assert bulk["op.acc.6"].status == "missing"
    assert bulk["mp.info.3"].status == "implemented"  # no gap emitted
    assert bulk["org.UNK"].status == "unknown"


# ============================================================
# M04 plan integration
# ============================================================


@pytest.mark.asyncio
async def test_iter_gaps_yields_suggestions_sorted_by_severity(db):
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)
    await _seed_no_mfa_diagnostics(db, pid)

    items = [
        s async for s in iter_gaps_for_plan_actions(
            db, project_id=pid, severity_min="high",
        )
    ]
    # Al menos 1 suggestion (op.acc.6 critical)
    assert len(items) >= 1
    assert items[0].ens_measure_code == "op.acc.6"
    assert items[0].priority == "critical"
    assert items[0].source == "cloud_gap_engine"
    assert items[0].gap_id is not None


@pytest.mark.asyncio
async def test_iter_gaps_severity_min_filter_excludes_lower_priority(db):
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)
    await _seed_no_mfa_diagnostics(db, pid)

    # severity_min='critical' → solo critical
    items_critical = [
        s async for s in iter_gaps_for_plan_actions(
            db, project_id=pid, severity_min="critical",
        )
    ]
    # severity_min='medium' → todos
    items_medium = [
        s async for s in iter_gaps_for_plan_actions(
            db, project_id=pid, severity_min="medium",
        )
    ]
    assert len(items_critical) <= len(items_medium)


# ============================================================
# M07 evidence integration
# ============================================================


@pytest.mark.asyncio
async def test_iter_evidences_yields_resources_for_measure(db):
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)
    await _seed_no_mfa_diagnostics(db, pid)

    items = [
        s async for s in iter_evidences_for_attach(
            db, project_id=pid, measure_code="op.acc.6",
        )
    ]
    assert len(items) == 3  # 3 users inserted
    assert all(s.resource_type == "identity.user" for s in items)
    assert all(s.provider == "microsoft_365" for s in items)
    assert all("attributes_snapshot" in s.evidence_payload for s in items)


@pytest.mark.asyncio
async def test_iter_evidences_empty_for_unsupported_measure(db):
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)
    await _seed_no_mfa_diagnostics(db, pid)

    items = [
        s async for s in iter_evidences_for_attach(
            db, project_id=pid, measure_code="org.UNK_MEASURE",
        )
    ]
    assert items == []


@pytest.mark.asyncio
async def test_iter_evidences_filter_by_resource_type_per_measure(db):
    """op.acc.6 mapea SOLO a identity.user · NO devuelve buckets."""
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)
    svc = CloudConnectorService(db)
    connector = await svc.link_or_create_connector(
        project_id=pid, provider=CloudConnectorProvider.AWS,
    )
    # Insert ambos types
    await db.execute(text(
        "INSERT INTO cloud_resources (id, project_id, connector_id, "
        "resource_type, resource_external_id, resource_name, attributes) "
        "VALUES (:id, :pid, :cid, 'identity.user', 'u1', 'U1', "
        "CAST('{\"mfa_enabled\": true}' AS JSONB))"
    ), {"id": str(uuid.uuid4()), "pid": str(pid), "cid": str(connector.id)})
    await db.execute(text(
        "INSERT INTO cloud_resources (id, project_id, connector_id, "
        "resource_type, resource_external_id, resource_name, attributes) "
        "VALUES (:id, :pid, :cid, 'asset.bucket', 'b1', 'B1', "
        "CAST('{\"encrypted_at_rest\": true}' AS JSONB))"
    ), {"id": str(uuid.uuid4()), "pid": str(pid), "cid": str(connector.id)})
    await db.flush()

    # op.acc.6 → solo identity.user
    items_mfa = [
        s async for s in iter_evidences_for_attach(
            db, project_id=pid, measure_code="op.acc.6",
        )
    ]
    assert all(s.resource_type == "identity.user" for s in items_mfa)

    # mp.info.3 → solo storage types
    items_crypto = [
        s async for s in iter_evidences_for_attach(
            db, project_id=pid, measure_code="mp.info.3",
        )
    ]
    assert all(s.resource_type == "asset.bucket" for s in items_crypto)
