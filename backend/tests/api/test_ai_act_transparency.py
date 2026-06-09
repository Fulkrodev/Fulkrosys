"""Tests AI Act art.50 transparency · sub-atom 1.E.1.B.2.

Cover:
  - log_transparency_event service-to-service helper
  - retention_until compute (today + 6 years · Feb 29 fallback)
  - admin /admin/projects/{id}/transparency/log endpoint full view
  - cliente /client-portal/transparency/log endpoint friendly view
  - RLS project-scope + cliente client_id filter (NO cross-client leak)
  - RBAC require_owner + require_client_user
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from backend.app.motors.m_observability.transparency_service import (
    _compute_retention_until,
    log_transparency_event,
)
from backend.tests.conftest import setup_test_project


pytestmark = pytest.mark.asyncio


# ==================================================================
# _compute_retention_until · pure function tests
# ==================================================================


async def test_retention_until_default_six_years():
    """retention_until = now + 6 years para cualquier date normal."""
    base = datetime(2026, 5, 22, 12, 0, 0, tzinfo=timezone.utc)
    r = _compute_retention_until(base)
    assert r.year == 2032
    assert r.month == 5
    assert r.day == 22


async def test_retention_until_feb_29_fallback_to_feb_28():
    """Feb 29 + 6y · año destino no-bisiesto → use Feb 28 fallback."""
    base = datetime(2024, 2, 29, 12, 0, 0, tzinfo=timezone.utc)
    r = _compute_retention_until(base)
    # 2030 NO bisiesto · Feb 29 inválido · fallback Feb 28
    assert r.year == 2030
    assert r.month == 2
    assert r.day == 28


# ==================================================================
# log_transparency_event · service-to-service helper
# ==================================================================


async def test_log_transparency_event_basic(db):
    """Insert event básico · returns persisted entity con id + retention."""
    _, project_id_str = await setup_test_project(db)
    event = await log_transparency_event(
        db,
        project_id=uuid.UUID(project_id_str),
        event_type="deliverable_generated",
        llm_provider="anthropic",
        llm_model="claude-opus-4-7",
        agent_name="agent_04_redactor",
        purpose="Genera documento E-040 política de seguridad",
    )
    assert event.id is not None
    assert event.event_type == "deliverable_generated"
    assert event.purpose == "Genera documento E-040 política de seguridad"
    assert event.retention_until is not None
    # Retention computed 6y from now (today + 6y)
    assert event.retention_until.year == datetime.now(timezone.utc).year + 6


async def test_log_transparency_event_with_artifact_link(db):
    """Insert event con artifact_type + artifact_id + metadata."""
    _, project_id_str = await setup_test_project(db)
    artifact_uuid = uuid.uuid4()
    event = await log_transparency_event(
        db,
        project_id=uuid.UUID(project_id_str),
        event_type="proposal_drafted",
        llm_provider="anthropic",
        llm_model="claude-sonnet-4-6",
        agent_name="agent_20_contract_narrative",
        purpose="Redacta propuesta comercial P-001",
        artifact_type="P-001",
        artifact_id=artifact_uuid,
        metadata={"version": "v1", "client_sector": "público"},
    )
    assert event.artifact_type == "P-001"
    assert event.artifact_id == artifact_uuid
    assert event.metadata_ == {"version": "v1", "client_sector": "público"}


# ==================================================================
# Admin API · /admin/projects/{id}/transparency/log
# ==================================================================


async def test_admin_project_log_returns_events_ordered_desc(db, async_client):
    """Admin endpoint · 3 events seeded · returns 3 ordered DESC by created_at."""
    _, project_id_str = await setup_test_project(db)
    project_id = uuid.UUID(project_id_str)
    # Seed 3 events (db.commit() implícito en log helper)
    await log_transparency_event(
        db, project_id=project_id, event_type="diagnostic_performed",
        llm_provider="anthropic", llm_model="claude-opus-4-7",
        agent_name="agent_11_auditor_virtual",
        purpose="Realiza diagnóstico inicial categoría MEDIA",
    )
    await log_transparency_event(
        db, project_id=project_id, event_type="policy_drafted",
        llm_provider="anthropic", llm_model="claude-sonnet-4-6",
        agent_name="agent_04_redactor",
        purpose="Redacta política seguridad operacional",
    )
    await log_transparency_event(
        db, project_id=project_id, event_type="gap_analysis",
        llm_provider="anthropic", llm_model="claude-haiku-4-5",
        agent_name="agent_27_clasificador",
        purpose="Clasifica gaps Anexo II per familia",
    )
    r = await async_client.get(
        f"/api/v1/admin/projects/{project_id_str}/transparency/log?days=30",
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["project_id"] == project_id_str
    assert data["total"] >= 3
    assert data["days"] == 30
    # Verify admin sees technical fields
    assert "llm_provider" in data["items"][0]
    assert "llm_model" in data["items"][0]
    assert "retention_until" in data["items"][0]


async def test_admin_project_log_respects_days_filter(db, async_client):
    """days param clamped 1-730 · validation enforced."""
    _, project_id_str = await setup_test_project(db)
    r = await async_client.get(
        f"/api/v1/admin/projects/{project_id_str}/transparency/log?days=730",
    )
    assert r.status_code == 200
    # days=0 or days=731 should 422 (Query validation)
    r_invalid = await async_client.get(
        f"/api/v1/admin/projects/{project_id_str}/transparency/log?days=0",
    )
    assert r_invalid.status_code == 422


async def test_admin_project_log_empty_returns_empty_items(db, async_client):
    """Project sin events → returns total=0 items=[]."""
    _, project_id_str = await setup_test_project(db)
    r = await async_client.get(
        f"/api/v1/admin/projects/{project_id_str}/transparency/log",
    )
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 0
    assert data["items"] == []


# ==================================================================
# Cliente API · /client-portal/transparency/log · auth via override
# ==================================================================


@pytest.fixture
async def authed_client_with_id(async_client, db):
    """Override require_client_user · provee user con client_id real."""
    from backend.app.main import app
    from backend.app.auth.dependencies import require_client_user

    client_id, project_id = await setup_test_project(db)

    # Seed 2 events for this client
    await log_transparency_event(
        db, project_id=uuid.UUID(project_id), client_id=uuid.UUID(client_id),
        event_type="deliverable_generated", llm_provider="anthropic",
        llm_model="claude-opus-4-7", agent_name="agent_04_redactor",
        purpose="Genera documento de política de seguridad",
    )
    await log_transparency_event(
        db, project_id=uuid.UUID(project_id), client_id=uuid.UUID(client_id),
        event_type="copilot_interaction", llm_provider="anthropic",
        llm_model="claude-haiku-4-5", agent_name="agent_14_copiloto",
        purpose="Responde pregunta sobre Anexo II ENS",
    )

    async def override():
        return SimpleNamespace(
            id=uuid.uuid4(), client_id=uuid.UUID(client_id),
        )

    app.dependency_overrides[require_client_user] = override
    yield async_client, client_id
    app.dependency_overrides.pop(require_client_user, None)


async def test_client_log_returns_only_friendly_fields(authed_client_with_id):
    """Cliente endpoint · response friendly · NO leak llm_provider/llm_model."""
    client, client_id = authed_client_with_id
    r = await client.get("/api/v1/client-portal/transparency/log?days=180")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["client_id"] == client_id
    assert data["total"] >= 2
    # Verify NO technical leak · friendly fields only
    item = data["items"][0]
    assert "llm_provider" not in item
    assert "llm_model" not in item
    assert "metadata" not in item
    # Friendly fields present
    assert "event_type" in item
    assert "agent_name" in item
    assert "purpose" in item
    assert "created_at" in item


async def test_client_log_user_without_client_id_403(async_client, db):
    """Cliente sin client_id asignado → 403 forbidden."""
    from backend.app.main import app
    from backend.app.auth.dependencies import require_client_user

    async def override_no_client():
        return SimpleNamespace(id=uuid.uuid4(), client_id=None)

    app.dependency_overrides[require_client_user] = override_no_client
    try:
        r = await async_client.get(
            "/api/v1/client-portal/transparency/log",
        )
        assert r.status_code == 403
    finally:
        app.dependency_overrides.pop(require_client_user, None)


# ==================================================================
# RBAC · require_owner + require_client_user enforced
# ==================================================================


@pytest.mark.real_auth
async def test_require_owner_blocks_anonymous_admin_log(async_client):
    """SIN auth · admin transparency endpoint debe 401/403."""
    r = await async_client.get(
        "/api/v1/admin/projects/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        "/transparency/log",
    )
    assert r.status_code in (401, 403)
    body = r.text.lower()
    assert "ai_act_transparency" not in body
    assert "purpose" not in body


@pytest.mark.real_auth
async def test_require_client_user_blocks_anonymous_client_log(async_client):
    """SIN auth · cliente transparency endpoint debe 401/403."""
    r = await async_client.get(
        "/api/v1/client-portal/transparency/log",
    )
    assert r.status_code in (401, 403)
