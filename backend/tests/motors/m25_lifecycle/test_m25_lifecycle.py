"""Tests M25 Project Lifecycle & Archival.

Cubre:
- State machine con VALID_TRANSITIONS estrictas
- Lifecycle full path DRAFT → ARCHIVED
- Archive package con SHA-256 + firma Ed25519
- Purge solo si retention_until <= hoy
- Dashboard global (bypass RLS)
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest

from backend.app.database import set_tenant_context
from backend.app.motors.m25_lifecycle.lifecycle_service import (
    ALL_STATES,
    VALID_TRANSITIONS,
    LifecycleError,
    LifecycleService,
)
from backend.tests.conftest import setup_test_project


BASE = "/api/v1/lifecycle"


async def _setup_tenant(db):
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(
        db,
        client_id=uuid.UUID(client_id),
        project_id=uuid.UUID(project_id),
    )
    return client_id, project_id


# ─────────── Catálogo ───────────

def test_all_states_count():
    assert len(ALL_STATES) == 10
    expected = {"DRAFT", "NEGOTIATING", "SIGNED", "ACTIVE", "CERTIFIED",
                "RETAINER", "ENDED_RENEWAL_OK", "ENDED_CHURN", "ARCHIVED", "PURGED"}
    assert set(ALL_STATES) == expected


def test_valid_transitions_graph():
    assert VALID_TRANSITIONS["DRAFT"] == ["NEGOTIATING"]
    assert VALID_TRANSITIONS["PURGED"] == []  # terminal
    assert "ARCHIVED" in VALID_TRANSITIONS["ENDED_RENEWAL_OK"]
    assert "ARCHIVED" in VALID_TRANSITIONS["ENDED_CHURN"]


# ─────────── State machine ───────────

@pytest.mark.asyncio
async def test_initial_state_is_draft(db):
    _, project_id = await _setup_tenant(db)
    current = await LifecycleService().get_current_state(db, uuid.UUID(project_id))
    assert current == "DRAFT"


@pytest.mark.asyncio
async def test_transition_draft_to_negotiating(db):
    _, project_id = await _setup_tenant(db)
    event = await LifecycleService().transition(
        db, project_id=uuid.UUID(project_id),
        to_state="NEGOTIATING", reason="Lead calificado",
    )
    assert event.previous_state == "DRAFT"
    assert event.state == "NEGOTIATING"
    current = await LifecycleService().get_current_state(db, uuid.UUID(project_id))
    assert current == "NEGOTIATING"


@pytest.mark.asyncio
async def test_invalid_transition_raises(db):
    _, project_id = await _setup_tenant(db)
    with pytest.raises(LifecycleError):
        await LifecycleService().transition(
            db, project_id=uuid.UUID(project_id),
            to_state="ARCHIVED",
        )


@pytest.mark.asyncio
async def test_invalid_state_raises(db):
    _, project_id = await _setup_tenant(db)
    with pytest.raises(LifecycleError):
        await LifecycleService().transition(
            db, project_id=uuid.UUID(project_id),
            to_state="INVALID_STATE",
        )


@pytest.mark.asyncio
async def test_available_transitions_from_draft(db):
    _, project_id = await _setup_tenant(db)
    allowed = await LifecycleService().get_available_transitions(
        db, uuid.UUID(project_id),
    )
    assert allowed == ["NEGOTIATING"]


@pytest.mark.asyncio
async def test_full_lifecycle_draft_to_archived(db):
    _, project_id = await _setup_tenant(db)
    svc = LifecycleService()
    pid = uuid.UUID(project_id)
    path = [
        "NEGOTIATING", "SIGNED", "ACTIVE",
        "CERTIFIED", "RETAINER", "ENDED_RENEWAL_OK",
    ]
    for state in path:
        await svc.transition(db, pid, to_state=state)
    current = await svc.get_current_state(db, pid)
    assert current == "ENDED_RENEWAL_OK"

    # Archive → transiciona a ARCHIVED
    await svc.archive_project(db, pid)
    current = await svc.get_current_state(db, pid)
    assert current == "ARCHIVED"


@pytest.mark.asyncio
async def test_history_records_all_transitions(db):
    _, project_id = await _setup_tenant(db)
    svc = LifecycleService()
    pid = uuid.UUID(project_id)
    await svc.transition(db, pid, to_state="NEGOTIATING")
    await svc.transition(db, pid, to_state="SIGNED")
    await svc.transition(db, pid, to_state="ACTIVE")
    history = await svc.get_history(db, pid)
    assert len(history) == 3
    states = [h.state for h in history]
    assert states == ["NEGOTIATING", "SIGNED", "ACTIVE"]


@pytest.mark.asyncio
async def test_negotiating_can_revert_to_draft(db):
    _, project_id = await _setup_tenant(db)
    svc = LifecycleService()
    pid = uuid.UUID(project_id)
    await svc.transition(db, pid, to_state="NEGOTIATING")
    await svc.transition(db, pid, to_state="DRAFT", reason="Cliente pausa")
    current = await svc.get_current_state(db, pid)
    assert current == "DRAFT"


@pytest.mark.asyncio
async def test_active_to_ended_churn(db):
    _, project_id = await _setup_tenant(db)
    svc = LifecycleService()
    pid = uuid.UUID(project_id)
    for state in ["NEGOTIATING", "SIGNED", "ACTIVE", "ENDED_CHURN"]:
        await svc.transition(db, pid, to_state=state)
    current = await svc.get_current_state(db, pid)
    assert current == "ENDED_CHURN"


# ─────────── Archive ───────────

@pytest.mark.asyncio
async def test_archive_requires_ended_state(db):
    _, project_id = await _setup_tenant(db)
    svc = LifecycleService()
    pid = uuid.UUID(project_id)
    with pytest.raises(LifecycleError):
        await svc.archive_project(db, pid)


@pytest.mark.asyncio
async def test_archive_creates_zip_with_hash(db):
    _, project_id = await _setup_tenant(db)
    svc = LifecycleService()
    pid = uuid.UUID(project_id)
    # Path completo
    for state in ["NEGOTIATING", "SIGNED", "ACTIVE", "ENDED_CHURN"]:
        await svc.transition(db, pid, to_state=state)
    archive = await svc.archive_project(db, pid, retention_years=6)
    assert archive.archive_zip_hash_sha256 is not None
    assert len(archive.archive_zip_hash_sha256) == 64
    assert archive.archive_zip_size_bytes > 0
    assert archive.retention_years == 6
    assert archive.estado == "created"
    assert archive.retention_until > date.today()


@pytest.mark.asyncio
async def test_archive_has_signature(db):
    _, project_id = await _setup_tenant(db)
    svc = LifecycleService()
    pid = uuid.UUID(project_id)
    for state in ["NEGOTIATING", "SIGNED", "ACTIVE", "ENDED_CHURN"]:
        await svc.transition(db, pid, to_state=state)
    archive = await svc.archive_project(db, pid)
    assert archive.signature_ed25519 is not None


@pytest.mark.asyncio
async def test_archive_includes_documents_count(db):
    _, project_id = await _setup_tenant(db)
    svc = LifecycleService()
    pid = uuid.UUID(project_id)
    # Crear documento
    from backend.app.motors.m24_idms.idms_service import IDMSService
    idms = IDMSService()
    await idms.initialize_standard_folders(db, pid)
    await idms.intake_document(
        db, project_id=pid, nombre="test.pdf", contenido=b"doc content",
    )
    # Transicionar y archivar
    for state in ["NEGOTIATING", "SIGNED", "ACTIVE", "ENDED_CHURN"]:
        await svc.transition(db, pid, to_state=state)
    archive = await svc.archive_project(db, pid)
    assert archive.documents_count == 1


# ─────────── Purge ───────────

@pytest.mark.asyncio
async def test_purge_before_retention_raises(db):
    _, project_id = await _setup_tenant(db)
    svc = LifecycleService()
    pid = uuid.UUID(project_id)
    for state in ["NEGOTIATING", "SIGNED", "ACTIVE", "ENDED_CHURN"]:
        await svc.transition(db, pid, to_state=state)
    await svc.archive_project(db, pid, retention_years=6)
    with pytest.raises(LifecycleError):
        await svc.purge_project(db, pid)


@pytest.mark.asyncio
async def test_purge_when_retention_expired(db):
    _, project_id = await _setup_tenant(db)
    svc = LifecycleService()
    pid = uuid.UUID(project_id)
    for state in ["NEGOTIATING", "SIGNED", "ACTIVE", "ENDED_CHURN"]:
        await svc.transition(db, pid, to_state=state)
    archive = await svc.archive_project(db, pid)
    # Forzar retention_until al pasado
    archive.retention_until = date.today() - timedelta(days=1)
    await db.flush()

    purged = await svc.purge_project(db, pid)
    assert purged.estado == "purged"
    assert purged.purged_at is not None
    assert purged.archive_zip_path is None

    current = await svc.get_current_state(db, pid)
    assert current == "PURGED"


# ─────────── Dashboard ───────────

@pytest.mark.asyncio
async def test_lifecycle_summary_counts_by_state(db):
    _, project_id = await _setup_tenant(db)
    svc = LifecycleService()
    pid = uuid.UUID(project_id)
    await svc.transition(db, pid, to_state="NEGOTIATING")
    summary = await svc.get_lifecycle_summary(db)
    assert "by_state" in summary
    assert summary["by_state"].get("NEGOTIATING", 0) >= 1


# ─────────── API ───────────

@pytest.mark.asyncio
async def test_api_list_states(async_client):
    r = await async_client.get(f"{BASE}/states")
    assert r.status_code == 200
    assert r.json()["count"] == 10


@pytest.mark.asyncio
async def test_api_state_transitions(async_client):
    r = await async_client.get(f"{BASE}/states/DRAFT/transitions")
    assert r.status_code == 200
    assert r.json()["allowed_transitions"] == ["NEGOTIATING"]


@pytest.mark.asyncio
async def test_api_transition(async_client, db):
    _, project_id = await setup_test_project(db)
    r = await async_client.post(
        f"{BASE}/projects/{project_id}/lifecycle/transition",
        json={"to_state": "NEGOTIATING", "reason": "Test"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["state"] == "NEGOTIATING"


@pytest.mark.asyncio
async def test_api_get_state(async_client, db):
    _, project_id = await setup_test_project(db)
    r = await async_client.get(
        f"{BASE}/projects/{project_id}/lifecycle/state"
    )
    assert r.status_code == 200
    assert r.json()["current_state"] == "DRAFT"
    assert r.json()["available_transitions"] == ["NEGOTIATING"]


@pytest.mark.asyncio
async def test_api_archive(async_client, db):
    _, project_id = await setup_test_project(db)
    for state in ["NEGOTIATING", "SIGNED", "ACTIVE", "ENDED_CHURN"]:
        await async_client.post(
            f"{BASE}/projects/{project_id}/lifecycle/transition",
            json={"to_state": state},
        )
    r = await async_client.post(
        f"{BASE}/projects/{project_id}/lifecycle/archive",
        json={"retention_years": 6},
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["documents_count"] == 0
    assert data["retention_years"] == 6


@pytest.mark.asyncio
async def test_api_summary(async_client):
    r = await async_client.get(f"{BASE}/summary")
    assert r.status_code == 200
    data = r.json()
    assert "by_state" in data
    assert "total" in data
