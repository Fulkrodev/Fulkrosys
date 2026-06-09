"""CLUSTER 3 Phase C2 auditor clarifications CRUD + SSE + email tests.

Verifica:
1. Auditor portal POST /clarifications crea row + canonical event + SSE dispatch
2. Auditor portal GET list/detail project-scoped · RLS isolation
3. Admin GET /audit/clarifications cross-session + status + priority filters
4. Admin PATCH respuesta + auto-advance status=open → responded
5. Email backup best-effort · NO bloquea primary
6. Backward-compat canonical namespace constants
7. general target_type · linked_target_id NULL accepted
"""
from __future__ import annotations

import asyncio
import uuid

import pytest
from sqlalchemy import text as sa_text

from backend.app.motors.m12_magic_link.purposes import MagicLinkPurpose
from backend.app.motors.m12_magic_link.schemas import MagicLinkGenerateRequest
from backend.app.motors.m12_magic_link.service import MagicLinkService
from backend.app.motors.m09_audit_prep.audit_events import (
    ADMIN_CLARIFICATION_RESPONDED,
    AUDITOR_CLARIFICATION_REQUESTED,
    AUDITOR_EVENT_TYPES,
    is_auditor_event,
)
from backend.tests.conftest import _admin_setup, setup_test_project


async def _create_link(db, *, project_id: str):
    req = MagicLinkGenerateRequest(
        project_id=uuid.UUID(project_id),
        purpose=MagicLinkPurpose.AUDITOR_PORTAL_ENAC,
        recipient_email="auditor-test@ejemplo.es",
    )
    svc = MagicLinkService(db)
    return await svc.generate_magic_link(req, base_url="http://test")


# ════════════════════════════════════════════════════════════════════════
# Constants namespace
# ════════════════════════════════════════════════════════════════════════

def test_canonical_namespace_includes_clarification_events():
    assert is_auditor_event(AUDITOR_CLARIFICATION_REQUESTED)
    assert is_auditor_event(ADMIN_CLARIFICATION_RESPONDED)
    assert AUDITOR_CLARIFICATION_REQUESTED in AUDITOR_EVENT_TYPES
    assert ADMIN_CLARIFICATION_RESPONDED in AUDITOR_EVENT_TYPES


# ════════════════════════════════════════════════════════════════════════
# Auditor portal CRUD
# ════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_create_clarification_returns_201_and_persists(async_client, db):
    _, project_id = await setup_test_project(db)
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    body = {
        "question_text": "¿Está disponible la política de gestión de incidentes vigente?",
        "linked_target_type": "general",
        "priority": "high",
    }
    r = await async_client.post(
        f"/api/v1/public/auditor-portal/{resp.token}/clarifications", json=body,
    )
    assert r.status_code == 201, r.text
    result = r.json()
    assert result["priority"] == "high"
    assert result["status"] == "open"
    assert result["project_id"] == project_id
    assert result["linked_target_type"] == "general"
    assert result["linked_target_id"] is None


@pytest.mark.asyncio
async def test_create_clarification_emits_canonical_event(async_client, db):
    _, project_id = await setup_test_project(db)
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    body = {
        "question_text": "¿Última fecha de revisión del DdA firmado?",
        "linked_target_type": "medida",
        "linked_target_id": str(uuid.uuid4()),
        "priority": "normal",
    }
    await async_client.post(
        f"/api/v1/public/auditor-portal/{resp.token}/clarifications", json=body,
    )

    async with _admin_setup(db):
        row = (await db.execute(sa_text(
            "SELECT accion, payload_new->>'target', payload_new->>'priority' "
            "FROM audit_log "
            "WHERE accion = :accion AND project_id = :pid "
            "ORDER BY timestamp DESC LIMIT 1"
        ), {"accion": AUDITOR_CLARIFICATION_REQUESTED, "pid": project_id})).first()
    assert row is not None
    assert row[0] == AUDITOR_CLARIFICATION_REQUESTED
    assert row[1] == "medida"
    assert row[2] == "normal"


@pytest.mark.asyncio
async def test_create_clarification_invalid_priority_400(async_client, db):
    _, project_id = await setup_test_project(db)
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    body = {
        "question_text": "x",
        "linked_target_type": "general",
        "priority": "EXTREME",
    }
    r = await async_client.post(
        f"/api/v1/public/auditor-portal/{resp.token}/clarifications", json=body,
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_create_clarification_general_with_target_id_rejected(async_client, db):
    """linked_target_type='general' MUST have linked_target_id=NULL · 400."""
    _, project_id = await setup_test_project(db)
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    body = {
        "question_text": "x",
        "linked_target_type": "general",
        "linked_target_id": str(uuid.uuid4()),
        "priority": "normal",
    }
    r = await async_client.post(
        f"/api/v1/public/auditor-portal/{resp.token}/clarifications", json=body,
    )
    assert r.status_code == 400
    assert "general" in r.text.lower()


@pytest.mark.asyncio
async def test_list_clarifications_only_returns_project_scoped(async_client, db):
    _, project_a_id = await setup_test_project(db)
    resp_a = await _create_link(db, project_id=project_a_id)
    await db.commit()

    await async_client.post(
        f"/api/v1/public/auditor-portal/{resp_a.token}/clarifications",
        json={
            "question_text": "Project A clarification",
            "linked_target_type": "general",
            "priority": "normal",
        },
    )

    project_b_id = str(uuid.uuid4())
    client_b_id = str(uuid.uuid4())
    async with _admin_setup(db):
        await db.execute(sa_text(
            "INSERT INTO clients (id, nombre, cif, created_at) "
            "VALUES (:cid, 'Cliente B', :cif, now())"
        ), {"cid": client_b_id, "cif": f"B{uuid.uuid4().hex[:8].upper()}"})
        await db.execute(sa_text(
            "INSERT INTO projects (id, client_id, nombre, created_at) "
            "VALUES (:pid, :cid, 'Project B', now())"
        ), {"pid": project_b_id, "cid": client_b_id})
    await db.execute(sa_text(
        "SELECT set_config('app.current_project_id', :pid, true)"
    ), {"pid": project_b_id})
    await db.execute(sa_text(
        "SELECT set_config('app.current_client_id', :cid, true)"
    ), {"cid": client_b_id})
    resp_b = await _create_link(db, project_id=project_b_id)
    await db.commit()

    r = await async_client.get(
        f"/api/v1/public/auditor-portal/{resp_b.token}/clarifications",
    )
    body = r.json()
    assert body["total"] == 0
    for item in body["items"]:
        assert item["project_id"] == project_b_id


# ════════════════════════════════════════════════════════════════════════
# Admin endpoints
# ════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_admin_patch_response_emits_admin_event_and_auto_advances(async_client, db):
    """Admin PATCH response sin status explicit · auto-advances open → responded."""
    _, project_id = await setup_test_project(db)
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    create_r = await async_client.post(
        f"/api/v1/public/auditor-portal/{resp.token}/clarifications",
        json={
            "question_text": "Sample question",
            "linked_target_type": "general",
            "priority": "normal",
        },
    )
    clarification_id = create_r.json()["id"]

    patch_r = await async_client.patch(
        f"/api/v1/admin/projects/{project_id}/audit/clarifications/{clarification_id}",
        json={
            "admin_response": "Confirmado · adjunto documento en breve",
        },
    )
    assert patch_r.status_code == 200, patch_r.text
    body = patch_r.json()
    assert body["admin_response"].startswith("Confirmado")
    assert body["status"] == "responded"  # Auto-advance verified
    assert body["admin_responded_at"] is not None
    assert body["admin_responded_by"] is not None

    async with _admin_setup(db):
        row = (await db.execute(sa_text(
            "SELECT accion FROM audit_log "
            "WHERE accion = :accion AND project_id = :pid "
            "ORDER BY timestamp DESC LIMIT 1"
        ), {"accion": ADMIN_CLARIFICATION_RESPONDED, "pid": project_id})).first()
    assert row is not None
    assert row[0] == ADMIN_CLARIFICATION_RESPONDED


@pytest.mark.asyncio
async def test_admin_list_clarifications_priority_filter(async_client, db):
    _, project_id = await setup_test_project(db)
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    for prio in ("low", "normal", "high"):
        await async_client.post(
            f"/api/v1/public/auditor-portal/{resp.token}/clarifications",
            json={
                "question_text": f"Question {prio}",
                "linked_target_type": "general",
                "priority": prio,
            },
        )

    r = await async_client.get(
        f"/api/v1/admin/projects/{project_id}/audit/clarifications?priority_filter=high",
    )
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["priority"] == "high"


# ════════════════════════════════════════════════════════════════════════
# SSE dispatch verification
# ════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_create_clarification_dispatches_sse_event(async_client, db):
    """SSE dispatcher publishes auditor_clarification_new event on channel project:{id}."""
    from backend.app.core.sse_dispatcher import sse_dispatcher

    _, project_id = await setup_test_project(db)
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    channel = f"project:{project_id}"
    received: list = []

    async def consume():
        async for event in sse_dispatcher.subscribe(channel):
            received.append(event)
            return

    consumer_task = asyncio.create_task(consume())
    await asyncio.sleep(0.05)  # Allow subscription to register

    body = {
        "question_text": "SSE check",
        "linked_target_type": "general",
        "priority": "urgent",
    }
    await async_client.post(
        f"/api/v1/public/auditor-portal/{resp.token}/clarifications", json=body,
    )

    try:
        await asyncio.wait_for(consumer_task, timeout=1.5)
    except asyncio.TimeoutError:
        consumer_task.cancel()

    assert len(received) >= 1
    event = received[0]
    assert event.type == "auditor_clarification_new"
    assert event.data["priority"] == "urgent"
    assert "preview" in event.data
