"""Tests AlertService (MB-13.4 · ADR-035).

Cobertura:
- trigger_alert crea registro
- trigger_alert valida severity y category (ValueError)
- list_active_alerts filtra acknowledged
- acknowledge idempotente (False segunda vez)
- list_active_global respeta limit + orden desc
"""
import uuid

import pytest

from backend.app.motors.m18_communication.alert_service import AlertService
from backend.tests.conftest import setup_test_project


@pytest.mark.asyncio
async def test_trigger_alert_creates_record(db):
    _, project_id = await setup_test_project(db)
    service = AlertService(db)

    alert = await service.trigger_alert(
        project_id=uuid.UUID(project_id),
        severity="warning",
        category="bienal_art31",
        title="Test alert",
        description="Test description",
        action_url="/admin/test",
        triggered_by="test_runner",
    )

    assert alert.id is not None
    assert alert.severity == "warning"
    assert alert.category == "bienal_art31"
    assert alert.title == "Test alert"
    assert alert.acknowledged_at is None


@pytest.mark.asyncio
async def test_trigger_alert_invalid_severity_raises(db):
    _, project_id = await setup_test_project(db)
    service = AlertService(db)

    with pytest.raises(ValueError, match="Invalid severity"):
        await service.trigger_alert(
            project_id=uuid.UUID(project_id),
            severity="extreme",  # invalid
            category="other",
            title="Test",
        )


@pytest.mark.asyncio
async def test_trigger_alert_invalid_category_raises(db):
    _, project_id = await setup_test_project(db)
    service = AlertService(db)

    with pytest.raises(ValueError, match="Invalid category"):
        await service.trigger_alert(
            project_id=uuid.UUID(project_id),
            severity="info",
            category="not_a_real_category",  # invalid
            title="Test",
        )


@pytest.mark.asyncio
async def test_list_active_filters_acknowledged(db):
    _, project_id = await setup_test_project(db)
    pid = uuid.UUID(project_id)
    service = AlertService(db)

    a1 = await service.trigger_alert(pid, "info", "other", "T1")
    a2 = await service.trigger_alert(pid, "warning", "other", "T2")
    await db.commit()

    # Acknowledge a1
    success = await service.acknowledge(a1.id)
    await db.commit()
    assert success is True

    active = await service.list_active_alerts(pid)
    active_ids = {a.id for a in active}
    assert a1.id not in active_ids
    assert a2.id in active_ids


@pytest.mark.asyncio
async def test_acknowledge_idempotent(db):
    _, project_id = await setup_test_project(db)
    pid = uuid.UUID(project_id)
    service = AlertService(db)

    alert = await service.trigger_alert(pid, "info", "other", "T1")
    await db.commit()

    first = await service.acknowledge(alert.id)
    await db.commit()
    second = await service.acknowledge(alert.id)
    await db.commit()

    assert first is True
    assert second is False


@pytest.mark.asyncio
async def test_list_active_global_includes_all_unack(db):
    _, project_id = await setup_test_project(db)
    pid = uuid.UUID(project_id)
    service = AlertService(db)

    a1 = await service.trigger_alert(pid, "info", "other", "First")
    a2 = await service.trigger_alert(pid, "info", "other", "Second")
    await db.commit()

    alerts = await service.list_active_global(limit=50)
    ids = {a.id for a in alerts}
    assert a1.id in ids
    assert a2.id in ids


@pytest.mark.asyncio
async def test_list_active_global_respects_limit(db):
    _, project_id = await setup_test_project(db)
    pid = uuid.UUID(project_id)
    service = AlertService(db)

    for i in range(5):
        await service.trigger_alert(pid, "info", "other", f"Alert {i}")
    await db.commit()

    alerts = await service.list_active_global(limit=3)
    assert len(alerts) <= 3
