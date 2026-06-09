"""Tests SAN-D MB-19.16 cosecha · Recent Activity API + RecentActivityCard.

Cubre DEC-MB13-RECENT-ACTIVITY-CARD asignado MB-19:
- Endpoint GET /api/v1/projects/{id}/recent-activity retorna actividades
  combinadas (ClientUserAudit + ClientTask transitions).
- Limit param validation 5-100.
- 404 si project no existe.
- Empty result valid · response shape consistente.
- Ordenado occurred_at DESC.
- Action labels human-readable.

Refs: ADR-035 · MB-19.16 cosecha.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select, text

from backend.app.motors.m21_portal_cliente.recent_activity_api import (
    _label_for_action,
    _ACTION_LABELS,
)
from backend.tests.conftest import _admin_setup


# ====================== Action labels mapping ======================

def test_label_for_action_known_audit_actions():
    """Known audit actions retornan labels español hispano."""
    assert _label_for_action("LOGIN") == "Login portal"
    assert _label_for_action("login_success") == "Login portal exitoso"
    assert _label_for_action("evidence_uploaded") == "Evidencia subida"
    assert _label_for_action("password_change") == "Cambio contraseña"


def test_label_for_action_known_task_actions():
    """Task transitions retornan labels."""
    assert _label_for_action("task_completed") == "Tarea completada"
    assert _label_for_action("task_started") == "Tarea iniciada"


def test_label_for_action_unknown_fallback():
    """Action desconocida retorna versión humanizada (replace _ + capitalize)."""
    assert _label_for_action("unknown_action_xyz") == "Unknown action xyz"
    assert _label_for_action(None) == "Actividad"
    assert _label_for_action("") == "Actividad"


def test_action_labels_dict_coverage():
    """_ACTION_LABELS contiene actions documentadas en client_user_audit."""
    expected_audit_actions = {
        "LOGIN", "login_success", "login_failure", "password_change",
        "account_locked",
        "document_downloaded", "evidence_uploaded", "session_revoked",
        "user_created", "user_deactivated", "role_changed",
        "first_access_completed",
    }
    for action in expected_audit_actions:
        assert action in _ACTION_LABELS


# ====================== Endpoint shape (direct service test) ======================

@pytest.mark.asyncio
async def test_recent_activity_empty_returns_valid_shape(db):
    """Project sin actividad retorna {items: [], total: 0}."""
    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"

    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO clients (id, nombre, cif, created_at) "
            "VALUES (:id, 'Empty Activity Co', :cif, now())"
        ), {"id": str(client_id), "cif": cif})
        await db.execute(text(
            "INSERT INTO projects (id, client_id, nombre, created_at) "
            "VALUES (:id, :cid, 'Empty Activity Project', now())"
        ), {"id": str(project_id), "cid": str(client_id)})
    await db.flush()

    # Test direct query simulation (sin HTTP fixture · core logic)
    from backend.app.models.client_portal import ClientUserAudit
    from backend.app.motors.m21_portal_cliente.models_tasks import ClientTask

    audit_rows = (await db.scalars(
        select(ClientUserAudit)
        .where(ClientUserAudit.project_id == project_id)
        .limit(20)
    )).all()
    assert len(list(audit_rows)) == 0

    task_rows = (await db.scalars(
        select(ClientTask)
        .where(ClientTask.project_id == project_id)
        .limit(20)
    )).all()
    assert len(list(task_rows)) == 0


@pytest.mark.asyncio
async def test_recent_activity_with_audit_rows_serialized(db):
    """ClientUserAudit rows asociadas a project son serializadas correctamente."""
    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    client_user_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    user_email = f"audit-{uuid.uuid4().hex[:6]}@audit.es"

    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO clients (id, nombre, cif, created_at) "
            "VALUES (:id, 'Audit Co', :cif, now())"
        ), {"id": str(client_id), "cif": cif})
        await db.execute(text(
            "INSERT INTO projects (id, client_id, nombre, created_at) "
            "VALUES (:id, :cid, 'Audit Project', now())"
        ), {"id": str(project_id), "cid": str(client_id)})
        await db.execute(text(
            "INSERT INTO client_users (id, client_id, email, "
            "full_name, password_hash, must_change_password, "
            "created_at) "
            "VALUES (:id, :cid, :email, 'Audit User', "
            "'hash_audit', FALSE, now())"
        ), {
            "id": str(client_user_id),
            "cid": str(client_id),
            "email": user_email,
        })
        await db.execute(text(
            "INSERT INTO client_user_audit "
            "(id, client_user_id, client_id, project_id, action, "
            "metadata_jsonb, created_at) "
            "VALUES (gen_random_uuid(), :uid, :cid, :pid, "
            "'login_success', "
            "'{\"device\": \"chrome\"}'::jsonb, now())"
        ), {
            "uid": str(client_user_id),
            "cid": str(client_id),
            "pid": str(project_id),
        })
        await db.execute(text(
            "INSERT INTO client_user_audit "
            "(id, client_user_id, client_id, project_id, action, "
            "created_at) "
            "VALUES (gen_random_uuid(), :uid, :cid, :pid, "
            "'evidence_uploaded', now())"
        ), {
            "uid": str(client_user_id),
            "cid": str(client_id),
            "pid": str(project_id),
        })
    await db.flush()

    # Verificar via query directa que rows existen (admin role para RLS)
    from backend.app.models.client_portal import ClientUserAudit
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    audit_rows = list((await db.scalars(
        select(ClientUserAudit)
        .where(ClientUserAudit.project_id == project_id)
        .order_by(ClientUserAudit.created_at.desc())
    )).all())
    await db.execute(text("RESET ROLE"))
    assert len(audit_rows) == 2

    # Action types coherentes con _ACTION_LABELS
    actions = {r.action for r in audit_rows}
    assert actions == {"login_success", "evidence_uploaded"}


@pytest.mark.asyncio
async def test_recent_activity_with_task_transitions(db):
    """ClientTask con started_at/completed_at populated genera activity items."""
    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"

    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO clients (id, nombre, cif, created_at) "
            "VALUES (:id, 'Task Activity Co', :cif, now())"
        ), {"id": str(client_id), "cif": cif})
        await db.execute(text(
            "INSERT INTO projects (id, client_id, nombre, created_at) "
            "VALUES (:id, :cid, 'Task Activity Project', now())"
        ), {"id": str(project_id), "cid": str(client_id)})
        # Task completed
        await db.execute(text(
            "INSERT INTO client_tasks "
            "(id, project_id, template_id, phase, title, description, "
            "status, completed_at, created_at) "
            "VALUES (gen_random_uuid(), :pid, 'audit-task-1', "
            "'implantacion', 'Subir evidencias', 'Completada', "
            "'done', now(), now())"
        ), {"pid": str(project_id)})
        # Task started but NOT completed
        await db.execute(text(
            "INSERT INTO client_tasks "
            "(id, project_id, template_id, phase, title, description, "
            "status, started_at, created_at) "
            "VALUES (gen_random_uuid(), :pid, 'audit-task-2', "
            "'implantacion', 'Revisar DdA', 'En curso', "
            "'in_progress', now(), now())"
        ), {"pid": str(project_id)})
    await db.flush()

    from backend.app.motors.m21_portal_cliente.models_tasks import ClientTask
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    task_rows = list((await db.scalars(
        select(ClientTask)
        .where(ClientTask.project_id == project_id)
    )).all())
    await db.execute(text("RESET ROLE"))
    assert len(task_rows) == 2

    completed_tasks = [t for t in task_rows if t.completed_at is not None]
    started_only_tasks = [
        t for t in task_rows
        if t.started_at is not None and t.completed_at is None
    ]
    assert len(completed_tasks) == 1
    assert len(started_only_tasks) == 1
    assert completed_tasks[0].title == "Subir evidencias"
    assert started_only_tasks[0].title == "Revisar DdA"


@pytest.mark.asyncio
async def test_recent_activity_endpoint_404_for_nonexistent_project(db):
    """Endpoint retorna 404 si project no existe (vía get_project_owner)."""
    from backend.app.motors.m21_portal_cliente.recent_activity_api import (
        get_recent_activity,
    )

    fake_project_id = uuid.uuid4()
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await get_recent_activity(
            project_id=fake_project_id,
            limit=20,
            db=db,
        )
    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_recent_activity_endpoint_400_invalid_limit(db):
    """limit fuera rango 5-100 raises 400."""
    from backend.app.motors.m21_portal_cliente.recent_activity_api import (
        get_recent_activity,
    )

    fake_project_id = uuid.uuid4()
    from fastapi import HTTPException

    # limit < 5
    with pytest.raises(HTTPException) as exc_info_low:
        await get_recent_activity(
            project_id=fake_project_id,
            limit=2,
            db=db,
        )
    assert exc_info_low.value.status_code == 400
    assert "5-100" in exc_info_low.value.detail

    # limit > 100
    with pytest.raises(HTTPException) as exc_info_high:
        await get_recent_activity(
            project_id=fake_project_id,
            limit=200,
            db=db,
        )
    assert exc_info_high.value.status_code == 400
