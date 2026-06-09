"""Smoke tests for admin dashboard endpoints · FASE 2 H4.

Validates 4 endpoints registered + Pydantic schemas correct + queries don't
error on empty BD (greenfield safety).
"""
from __future__ import annotations

import pytest

from backend.app.services.admin_dashboard_service import (
    AdminDashboardService,
    DashboardKpis,
)


pytestmark = pytest.mark.asyncio


async def test_dashboard_service_get_kpis_empty_bd(db):
    """KPIs query empty BD returns zero values (no crash)."""
    service = AdminDashboardService(db)
    kpis = await service.get_kpis()
    assert isinstance(kpis, DashboardKpis)
    assert kpis.active_projects >= 0
    assert kpis.leads_count >= 0
    assert kpis.leads_value_eur >= 0.0
    assert kpis.retainers_active >= 0
    assert kpis.mrr_eur >= 0.0
    assert kpis.treasury_30d_eur >= 0.0
    assert kpis.projects_rag in ("green", "amber", "red")


async def test_dashboard_service_get_my_day_empty_bd(db):
    """MyDay query empty BD returns list (no crash)."""
    service = AdminDashboardService(db)
    items = await service.get_my_day()
    assert isinstance(items, list)
    for item in items:
        assert item.type in ("review_docs", "signature", "meeting", "other")


async def test_dashboard_service_get_alerts_empty_bd(db):
    """Alerts query empty BD returns list (no crash)."""
    service = AdminDashboardService(db)
    alerts = await service.get_alerts()
    assert isinstance(alerts, list)
    for alert in alerts:
        assert alert.severity in ("green", "amber", "red")


async def test_dashboard_service_get_activity_empty_bd(db):
    """Activity query empty BD returns list (no crash)."""
    service = AdminDashboardService(db)
    activity = await service.get_activity()
    assert isinstance(activity, list)
    valid_types = {
        "evidence_generated", "scan_completed", "proposal_sent",
        "document_signed", "agent_run", "other",
    }
    for event in activity:
        assert event.type in valid_types


async def test_dashboard_kpis_endpoint_smoke(async_client):
    """GET /api/v1/dashboard/kpis returns 200 + DashboardKpis schema."""
    response = await async_client.get("/api/v1/dashboard/kpis")
    assert response.status_code == 200, response.text
    data = response.json()
    assert "active_projects" in data
    assert "leads_count" in data
    assert "mrr_eur" in data
    assert "projects_rag" in data
    assert data["projects_rag"] in ("green", "amber", "red")


async def test_dashboard_my_day_endpoint_smoke(async_client):
    """GET /api/v1/dashboard/my-day returns 200 + list."""
    response = await async_client.get("/api/v1/dashboard/my-day")
    assert response.status_code == 200, response.text
    data = response.json()
    assert isinstance(data, list)


async def test_dashboard_alerts_endpoint_smoke(async_client):
    """GET /api/v1/dashboard/alerts returns 200 + list."""
    response = await async_client.get("/api/v1/dashboard/alerts")
    assert response.status_code == 200, response.text
    data = response.json()
    assert isinstance(data, list)


async def test_dashboard_activity_endpoint_smoke(async_client):
    """GET /api/v1/dashboard/activity returns 200 + list."""
    response = await async_client.get("/api/v1/dashboard/activity")
    assert response.status_code == 200, response.text
    data = response.json()
    assert isinstance(data, list)
