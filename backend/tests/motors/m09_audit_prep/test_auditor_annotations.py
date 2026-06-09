"""CLUSTER 3 Phase C1 auditor annotations CRUD tests.

Verifica:
1. Auditor portal POST /annotations crea row + audit_log canonical event
2. Auditor portal GET /annotations lista sólo project bounded · NO leak
3. Auditor portal DELETE 24h window enforced + magic_link_id ownership
4. Admin GET /audit/annotations · filter status · cross-project legit
5. Admin PATCH respuesta + status change · emit admin.annotation.responded
6. RLS isolation: project A annotations NO leak hacia project B token
7. Backward-compat audit_log namespace (canonical helpers)
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text as sa_text

from backend.app.motors.m12_magic_link.purposes import MagicLinkPurpose
from backend.app.motors.m12_magic_link.schemas import MagicLinkGenerateRequest
from backend.app.motors.m12_magic_link.service import MagicLinkService
from backend.app.motors.m09_audit_prep.audit_events import (
    ADMIN_ANNOTATION_RESPONDED,
    AUDITOR_ANNOTATION_CREATED,
    AUDITOR_ANNOTATION_DELETED,
    AUDITOR_EVENT_TYPES,
    is_auditor_event,
)
from backend.tests.conftest import _admin_setup, setup_test_project


pytestmark = pytest.mark.asyncio


async def _create_link(db, *, project_id: str):
    req = MagicLinkGenerateRequest(
        project_id=uuid.UUID(project_id),
        purpose=MagicLinkPurpose.AUDITOR_PORTAL_ENAC,
        recipient_email="auditor-test@ejemplo.es",
    )
    svc = MagicLinkService(db)
    return await svc.generate_magic_link(req, base_url="http://test")


# ════════════════════════════════════════════════════════════════════════
# Constants
# ════════════════════════════════════════════════════════════════════════

def test_canonical_namespace_includes_annotation_events():
    assert is_auditor_event(AUDITOR_ANNOTATION_CREATED)
    assert is_auditor_event(AUDITOR_ANNOTATION_DELETED)
    assert is_auditor_event(ADMIN_ANNOTATION_RESPONDED)
    assert AUDITOR_ANNOTATION_CREATED in AUDITOR_EVENT_TYPES
    assert AUDITOR_ANNOTATION_DELETED in AUDITOR_EVENT_TYPES
    assert ADMIN_ANNOTATION_RESPONDED in AUDITOR_EVENT_TYPES


# ════════════════════════════════════════════════════════════════════════
# Auditor portal CRUD
# ════════════════════════════════════════════════════════════════════════

async def test_create_annotation_returns_201_and_persists(async_client, db):
    _, project_id = await setup_test_project(db)
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    target_id = str(uuid.uuid4())
    body = {
        "target_type": "evidence",
        "target_id": target_id,
        "annotation_text": "Falta evidencia documental adjunta",
        "flag_severity": "warning",
    }
    r = await async_client.post(
        f"/api/v1/public/auditor-portal/{resp.token}/annotations", json=body,
    )
    assert r.status_code == 201, r.text
    result = r.json()
    assert result["target_type"] == "evidence"
    assert result["flag_severity"] == "warning"
    assert result["status"] == "open"
    assert result["project_id"] == project_id


async def test_create_annotation_emits_canonical_event(async_client, db):
    _, project_id = await setup_test_project(db)
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    body = {
        "target_type": "medida",
        "target_id": str(uuid.uuid4()),
        "annotation_text": "Justificación insuficiente",
        "flag_severity": "concern",
    }
    await async_client.post(
        f"/api/v1/public/auditor-portal/{resp.token}/annotations", json=body,
    )

    async with _admin_setup(db):
        row = (await db.execute(sa_text(
            "SELECT accion, payload_new->>'target', payload_new->>'flag_severity' "
            "FROM audit_log "
            "WHERE tabla = 'auditor_portal' "
            "AND accion = :accion AND project_id = :pid "
            "ORDER BY timestamp DESC LIMIT 1"
        ), {"accion": AUDITOR_ANNOTATION_CREATED, "pid": project_id})).first()
    assert row is not None
    assert row[0] == AUDITOR_ANNOTATION_CREATED
    assert row[1] == "medida"
    assert row[2] == "concern"


async def test_create_annotation_invalid_target_type_400(async_client, db):
    _, project_id = await setup_test_project(db)
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    body = {
        "target_type": "INVALID_TYPE",
        "target_id": str(uuid.uuid4()),
        "annotation_text": "x",
        "flag_severity": "info",
    }
    r = await async_client.post(
        f"/api/v1/public/auditor-portal/{resp.token}/annotations", json=body,
    )
    assert r.status_code == 400
    assert "target_type inválido" in r.text


async def test_create_annotation_invalid_severity_400(async_client, db):
    _, project_id = await setup_test_project(db)
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    body = {
        "target_type": "evidence",
        "target_id": str(uuid.uuid4()),
        "annotation_text": "x",
        "flag_severity": "EXTREME",  # invalid
    }
    r = await async_client.post(
        f"/api/v1/public/auditor-portal/{resp.token}/annotations", json=body,
    )
    assert r.status_code == 400


async def test_list_annotations_only_returns_project_scoped(async_client, db):
    """Annotations created en project A · NO visible bound a token project B."""
    _, project_a_id = await setup_test_project(db)
    resp_a = await _create_link(db, project_id=project_a_id)
    await db.commit()

    # Create annotation in project A
    body = {
        "target_type": "evidence",
        "target_id": str(uuid.uuid4()),
        "annotation_text": "Project A anotación",
        "flag_severity": "info",
    }
    await async_client.post(
        f"/api/v1/public/auditor-portal/{resp_a.token}/annotations", json=body,
    )

    # Create project B + token + list its annotations
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
    # Set tenant context to project B to allow magic_link insert under fulkro_app RLS
    await db.execute(sa_text(
        "SELECT set_config('app.current_project_id', :pid, true)"
    ), {"pid": project_b_id})
    await db.execute(sa_text(
        "SELECT set_config('app.current_client_id', :cid, true)"
    ), {"cid": client_b_id})
    resp_b = await _create_link(db, project_id=project_b_id)
    await db.commit()

    r = await async_client.get(
        f"/api/v1/public/auditor-portal/{resp_b.token}/annotations",
    )
    body = r.json()
    assert body["total"] == 0
    for item in body["items"]:
        assert item["project_id"] == project_b_id


async def test_delete_annotation_within_24h_window(async_client, db):
    _, project_id = await setup_test_project(db)
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    body = {
        "target_type": "evidence",
        "target_id": str(uuid.uuid4()),
        "annotation_text": "delete me",
        "flag_severity": "info",
    }
    create_r = await async_client.post(
        f"/api/v1/public/auditor-portal/{resp.token}/annotations", json=body,
    )
    annotation_id = create_r.json()["id"]

    del_r = await async_client.delete(
        f"/api/v1/public/auditor-portal/{resp.token}/annotations/{annotation_id}",
    )
    assert del_r.status_code == 204

    # Subsequent GET returns 404 (soft-deleted)
    get_r = await async_client.get(
        f"/api/v1/public/auditor-portal/{resp.token}/annotations/{annotation_id}",
    )
    assert get_r.status_code == 404

    # audit_log emits AUDITOR_ANNOTATION_DELETED
    async with _admin_setup(db):
        row = (await db.execute(sa_text(
            "SELECT accion FROM audit_log "
            "WHERE accion = :accion AND project_id = :pid "
            "ORDER BY timestamp DESC LIMIT 1"
        ), {"accion": AUDITOR_ANNOTATION_DELETED, "pid": project_id})).first()
    assert row is not None
    assert row[0] == AUDITOR_ANNOTATION_DELETED


async def test_delete_annotation_invalid_token_403(async_client, db):
    """Auditor B NO puede borrar annotation creada por auditor A."""
    _, project_id = await setup_test_project(db)
    resp_a = await _create_link(db, project_id=project_id)
    await db.commit()

    body = {
        "target_type": "evidence",
        "target_id": str(uuid.uuid4()),
        "annotation_text": "Anotación A",
        "flag_severity": "info",
    }
    create_r = await async_client.post(
        f"/api/v1/public/auditor-portal/{resp_a.token}/annotations", json=body,
    )
    annotation_id = create_r.json()["id"]

    # Create a SECOND token (different magic_link_id · same project)
    resp_b = await _create_link(db, project_id=project_id)
    await db.commit()

    del_r = await async_client.delete(
        f"/api/v1/public/auditor-portal/{resp_b.token}/annotations/{annotation_id}",
    )
    assert del_r.status_code == 403
    assert "different auditor session" in del_r.text


# ════════════════════════════════════════════════════════════════════════
# Admin endpoints
# ════════════════════════════════════════════════════════════════════════

async def test_admin_list_annotations_returns_project_rows(async_client, db):
    """Admin GET annotations returns project rows · cross-project legit."""
    _, project_id = await setup_test_project(db)
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    await async_client.post(
        f"/api/v1/public/auditor-portal/{resp.token}/annotations",
        json={
            "target_type": "evidence",
            "target_id": str(uuid.uuid4()),
            "annotation_text": "Admin test",
            "flag_severity": "info",
        },
    )

    r = await async_client.get(
        f"/api/v1/admin/projects/{project_id}/audit/annotations",
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["flag_severity"] == "info"


async def test_admin_patch_response_emits_admin_event(async_client, db):
    """Admin PATCH response + emit admin.annotation.responded canonical event."""
    _, project_id = await setup_test_project(db)
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    create_r = await async_client.post(
        f"/api/v1/public/auditor-portal/{resp.token}/annotations",
        json={
            "target_type": "evidence",
            "target_id": str(uuid.uuid4()),
            "annotation_text": "Falta evidencia",
            "flag_severity": "concern",
        },
    )
    annotation_id = create_r.json()["id"]

    patch_r = await async_client.patch(
        f"/api/v1/admin/projects/{project_id}/audit/annotations/{annotation_id}",
        json={
            "admin_response": "Evidencia aportada vía email · subiendo ahora",
            "status": "admin_reviewed",
        },
    )
    assert patch_r.status_code == 200, patch_r.text
    body = patch_r.json()
    assert body["admin_response"].startswith("Evidencia aportada")
    assert body["status"] == "admin_reviewed"
    assert body["admin_responded_at"] is not None
    assert body["admin_responded_by"] is not None

    async with _admin_setup(db):
        row = (await db.execute(sa_text(
            "SELECT accion FROM audit_log "
            "WHERE accion = :accion AND project_id = :pid "
            "ORDER BY timestamp DESC LIMIT 1"
        ), {"accion": ADMIN_ANNOTATION_RESPONDED, "pid": project_id})).first()
    assert row is not None
    assert row[0] == ADMIN_ANNOTATION_RESPONDED


async def test_admin_patch_no_fields_returns_400(async_client, db):
    _, project_id = await setup_test_project(db)
    resp = await _create_link(db, project_id=project_id)
    await db.commit()
    create_r = await async_client.post(
        f"/api/v1/public/auditor-portal/{resp.token}/annotations",
        json={
            "target_type": "evidence",
            "target_id": str(uuid.uuid4()),
            "annotation_text": "x",
            "flag_severity": "info",
        },
    )
    annotation_id = create_r.json()["id"]

    r = await async_client.patch(
        f"/api/v1/admin/projects/{project_id}/audit/annotations/{annotation_id}",
        json={},
    )
    assert r.status_code == 400
    assert "at least one field" in r.text.lower()
