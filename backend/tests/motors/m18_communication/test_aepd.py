"""Tests AEPD decision tree + connector + API · SAN-C MB-11.2."""
from __future__ import annotations

import pytest

from backend.app.motors.m18_communication.aepd_connector import (
    AEPD_PORTAL_URL,
    prepare_aepd_payload,
)
from backend.app.motors.m18_communication.aepd_decision_tree import (
    IncidentInput,
    evaluate_decision_tree,
)


# ============================================================
# Decision tree (4 paths · briefing)
# ============================================================


def test_no_personal_data_returns_no_notify():
    d = evaluate_decision_tree(
        IncidentInput(affects_personal_data=False, risk_to_rights="high"),
    )
    assert d.notify is False
    assert d.notify_subjects is False
    assert d.register_only is False
    assert any("No afecta datos personales" in s for s in d.path)


def test_low_risk_personal_data_register_only():
    d = evaluate_decision_tree(
        IncidentInput(affects_personal_data=True, risk_to_rights="low"),
    )
    assert d.notify is False
    assert d.register_only is True
    assert any("Riesgo bajo" in s for s in d.path)


def test_medium_risk_notify_72h():
    d = evaluate_decision_tree(
        IncidentInput(affects_personal_data=True, risk_to_rights="medium"),
    )
    assert d.notify is True
    assert d.notify_subjects is False
    assert d.deadline_hours == 72
    assert any("Riesgo medio" in s for s in d.path)


def test_high_risk_notify_with_subjects():
    d = evaluate_decision_tree(
        IncidentInput(affects_personal_data=True, risk_to_rights="high"),
    )
    assert d.notify is True
    assert d.notify_subjects is True
    assert d.deadline_hours == 72
    assert any("Alto riesgo" in s for s in d.path)


def test_unknown_risk_defaults_to_medium():
    """Risk vacío con datos personales asume medio (defensive default)."""
    d = evaluate_decision_tree(
        IncidentInput(affects_personal_data=True, risk_to_rights=""),
    )
    assert d.notify is True
    assert d.deadline_hours == 72


# ============================================================
# Connector pre-fill
# ============================================================


def test_prepare_aepd_payload_full_fields():
    from datetime import datetime, timezone

    detected = datetime(2026, 5, 5, 10, 0, tzinfo=timezone.utc)
    payload = prepare_aepd_payload(
        responsable_nombre="Cliente XYZ S.L.",
        responsable_cif="B12345678",
        detected_at=detected,
        description="Brecha base datos clientes",
        data_categories=["nombre", "email", "telefono"],
        consequences="Posible identity theft",
        measures_taken="Reset passwords + comunicación",
    )
    assert payload["responsable"]["nombre"] == "Cliente XYZ S.L."
    assert payload["responsable"]["cif"] == "B12345678"
    assert payload["fecha_incidente"] == detected.isoformat()
    assert "nombre" in payload["categorias_datos_afectados"]
    assert payload["submission_method"] == "manual_portal"
    assert payload["portal_url"] == AEPD_PORTAL_URL
    assert len(payload["manual_steps"]) >= 3


def test_prepare_aepd_payload_minimal_fields():
    payload = prepare_aepd_payload(
        responsable_nombre="X",
        responsable_cif="B00000000",
    )
    assert payload["fecha_incidente"] is None
    assert payload["categorias_datos_afectados"] == []


# ============================================================
# HTTP API endpoint integration
# ============================================================


@pytest.mark.asyncio
async def test_evaluate_high_risk_persists_notification(async_client, db):
    from backend.tests.conftest import setup_test_project

    _, project_id = await setup_test_project(db)
    response = await async_client.post(
        f"/api/v1/projects/{project_id}/aepd/evaluate",
        json={
            "affects_personal_data": True,
            "risk_to_rights": "high",
            "severity": "high",
            "description": "Brecha base datos",
            "data_categories": ["email"],
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["requires_notification"] is True
    assert data["notify_subjects"] is True
    assert data["deadline_hours"] == 72
    assert data["notification_id"] is not None
    assert data["prefilled_payload"] is not None
    assert "portal_url" in data["prefilled_payload"]


@pytest.mark.asyncio
async def test_evaluate_no_personal_data_no_notification_persisted(
    async_client, db,
):
    from backend.tests.conftest import setup_test_project

    _, project_id = await setup_test_project(db)
    response = await async_client.post(
        f"/api/v1/projects/{project_id}/aepd/evaluate",
        json={
            "affects_personal_data": False,
            "risk_to_rights": "high",
            "severity": "low",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["requires_notification"] is False
    assert data["notification_id"] is None  # No persiste si no aplica


@pytest.mark.asyncio
async def test_list_notifications_with_countdown(async_client, db):
    from backend.tests.conftest import setup_test_project

    _, project_id = await setup_test_project(db)
    # Create one high-risk notification
    await async_client.post(
        f"/api/v1/projects/{project_id}/aepd/evaluate",
        json={
            "affects_personal_data": True,
            "risk_to_rights": "high",
            "severity": "critical",
        },
    )
    response = await async_client.get(
        f"/api/v1/projects/{project_id}/aepd/notifications",
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["requires_notification"] is True
    assert data[0]["deadline_hours_remaining"] is not None
    assert data[0]["deadline_hours_remaining"] <= 72


@pytest.mark.asyncio
async def test_evaluate_unknown_project_returns_404(async_client):
    response = await async_client.post(
        "/api/v1/projects/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/aepd/evaluate",
        json={"affects_personal_data": True, "risk_to_rights": "low"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_evaluate_invalid_risk_returns_422(async_client, db):
    from backend.tests.conftest import setup_test_project

    _, project_id = await setup_test_project(db)
    response = await async_client.post(
        f"/api/v1/projects/{project_id}/aepd/evaluate",
        json={
            "affects_personal_data": True,
            "risk_to_rights": "invalid_risk_level",
        },
    )
    assert response.status_code == 422
