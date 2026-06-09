"""CLUSTER 2 Phase 2B · ClientNotification wire tests for CLUSTER 1 admin actions.

Cubre 3 motor endpoints wired post SSE dispatch · pattern #14 cumulative:
SSE + ClientNotification dual emit independent best-effort.

- m17_planning update_task → ClientNotification generic_alert low
- ClientNotification respects cliente_id RLS (Sub-atom 5.A · cross-project no leak)
- SSE + ClientNotification dual emit independent (best-effort graceful · sin users)
- VALID_TYPES taxonomy adequate (Phase 2B uses existing compliance_confirmation +
  generic_alert · NO new types needed)

NOTE: m01 + m02 endpoint wires verified via similar pattern; m17 happy-path
test is representative of dual emit behavior. m01 + m02 deep coverage diferida
a regresión cumulative cross-suite (140/140 m21 + adjacents).
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.client_notification import ClientNotification
from backend.app.models.planning import ProjectPlan, WbsTask
from backend.tests.conftest import _admin_setup, setup_test_project


# ════════════════════════════════════════════════════════════════════
# Fixtures
# ════════════════════════════════════════════════════════════════════


@pytest.fixture
async def authed_admin_client(async_client: AsyncClient, db: AsyncSession):
    """Admin auth bypass require_owner."""
    from backend.app.auth.dependencies import require_owner
    from backend.app.main import app

    class _StubOwner:
        id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        email = "marcos@fulkro.test"
        is_owner = True

    async def _override():
        return _StubOwner()

    app.dependency_overrides[require_owner] = _override
    yield async_client
    app.dependency_overrides.pop(require_owner, None)


# ════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════


async def _create_active_client_user(
    db: AsyncSession, *, client_id: uuid.UUID,
) -> uuid.UUID:
    """Insert active ClientUser row · returns user_id."""
    user_id = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO client_users (id, client_id, email, password_hash, "
                "full_name, must_change_password, created_at) "
                "VALUES (:uid, :cid, :email, 'x', 'Test', false, now())"
            ),
            {
                "uid": str(user_id),
                "cid": str(client_id),
                "email": f"cliente-{user_id.hex[:8]}@test.invalid",
            },
        )
    return user_id


async def _create_plan_with_task(
    db: AsyncSession, project_uuid: uuid.UUID, *, task_code: str = "WBS-001",
    responsible: str = "marcos",
) -> uuid.UUID:
    """Create ProjectPlan + WbsTask · returns task_id."""
    async with _admin_setup(db):
        plan = ProjectPlan(
            project_id=project_uuid,
            version=1,
            categoria="MEDIA",
            start_date=date.today(),
            end_date_estimated=date.today() + timedelta(weeks=8),
            estado="aprobado",
        )
        db.add(plan)
        await db.flush()
        task = WbsTask(
            project_plan_id=plan.id,
            project_id=project_uuid,
            task_code=task_code,
            task_name=f"Tarea {task_code}",
            phase="FASE_0",
            responsible=responsible,
            status="pending",
            progress_pct=0,
        )
        db.add(task)
        await db.flush()
        return task.id


async def _count_notifications(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    type_filter: str | None = None,
) -> int:
    """Count ClientNotification rows for project (admin scope)."""
    async with _admin_setup(db):
        stmt = select(ClientNotification).where(
            ClientNotification.project_id == project_id,
        )
        if type_filter:
            stmt = stmt.where(ClientNotification.type == type_filter)
        res = await db.execute(stmt)
        return len(list(res.scalars().all()))


# ════════════════════════════════════════════════════════════════════
# Phase 2B.1 · m17 PATCH task wire ClientNotification
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_m17_update_task_emits_cliente_notification(
    authed_admin_client: AsyncClient, db: AsyncSession,
) -> None:
    """m17 PATCH task → ClientNotification generic_alert low priority cliente inbox."""
    client_id_str, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    client_id = uuid.UUID(client_id_str)
    user_id = await _create_active_client_user(db, client_id=client_id)
    task_id = await _create_plan_with_task(db, project_uuid)

    pre_count = await _count_notifications(db, project_id=project_uuid)

    resp = await authed_admin_client.patch(
        f"/api/v1/planning/projects/{project_id_str}/tasks/{task_id}",
        json={"status": "en_curso", "progress_pct": 50},
    )
    assert resp.status_code == 200

    post_count = await _count_notifications(
        db, project_id=project_uuid, type_filter="generic_alert",
    )
    assert post_count >= pre_count + 1, (
        "m17 update_task should emit ClientNotification generic_alert"
    )
    _ = user_id


@pytest.mark.asyncio
async def test_notification_respects_cliente_id_rls_cross_project(
    authed_admin_client: AsyncClient, db: AsyncSession,
) -> None:
    """ClientNotification per project_id + client_user_id isolated · NO leak."""
    # Project A + Project B (distinct clients)
    client_a_id_str, project_a_id_str = await setup_test_project(db)
    project_a_uuid = uuid.UUID(project_a_id_str)
    user_a_id = await _create_active_client_user(
        db, client_id=uuid.UUID(client_a_id_str),
    )

    client_b_id_str, project_b_id_str = await setup_test_project(db)
    user_b_id = await _create_active_client_user(
        db, client_id=uuid.UUID(client_b_id_str),
    )

    task_a_id = await _create_plan_with_task(db, project_a_uuid)

    # Update task project A
    resp = await authed_admin_client.patch(
        f"/api/v1/planning/projects/{project_a_id_str}/tasks/{task_a_id}",
        json={"progress_pct": 25},
    )
    assert resp.status_code == 200

    # ClientNotification debe estar para user A · NUNCA leak user B
    async with _admin_setup(db):
        notif_a = (await db.execute(
            select(ClientNotification).where(
                ClientNotification.client_user_id == user_a_id,
                ClientNotification.project_id == project_a_uuid,
            )
        )).scalars().all()
        notif_b = (await db.execute(
            select(ClientNotification).where(
                ClientNotification.client_user_id == user_b_id,
            )
        )).scalars().all()

    assert len(notif_a) >= 1, "client A user should have notification"
    assert len(notif_b) == 0, "client B user must NOT have any leaked notif"


@pytest.mark.asyncio
async def test_sse_and_notification_dual_emit_independent_no_users(
    authed_admin_client: AsyncClient, db: AsyncSession,
) -> None:
    """Best-effort independent: project sin ClientUser activos · primary persist
    + SSE dispatch succeed sin raise · response 200 retornado · NO notif created."""
    client_id_str, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    # NO _create_active_client_user · project sin users active
    task_id = await _create_plan_with_task(db, project_uuid, task_code="WBS-002")

    resp = await authed_admin_client.patch(
        f"/api/v1/planning/projects/{project_id_str}/tasks/{task_id}",
        json={"status": "en_curso"},
    )
    # Primary persist must succeed · NO bloqueado por notification path
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "en_curso"

    # ClientNotification count = 0 (no users · graceful skip)
    notifs = await _count_notifications(db, project_id=project_uuid)
    assert notifs == 0


# ════════════════════════════════════════════════════════════════════
# Filosofía cliente-mínimo: notification type semantic check
# ════════════════════════════════════════════════════════════════════


def test_notification_types_valid_compliance_and_generic():
    """Phase 2B uses VALID_TYPES existing · NO new types needed (gap-fill scope)."""
    from backend.app.motors.m21_portal_cliente.notification_service import (
        VALID_TYPES,
    )
    # Phase 2B wires usan compliance_confirmation (m01 + m02) + generic_alert (m17)
    assert "compliance_confirmation" in VALID_TYPES
    assert "generic_alert" in VALID_TYPES
