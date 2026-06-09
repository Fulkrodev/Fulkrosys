"""Sesión 3B-2B.8 Phase 1E · M17 cliente portal plan READ-ONLY tests.

Cubre:
  - GET /api/v1/client-portal/plan happy path returns tasks + milestones
  - responsible field expuesto cliente (filter "Mis tareas" enabling)
  - audit_log emit cliente.plan.viewed con project_id + client_id Sub-atom 5.A
  - 404 si cliente sin proyecto activo
  - NO write endpoint cliente (PATCH/PUT/DELETE NOT allowed · ADR-014)
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.planning import ProjectPlan, WbsTask
from backend.tests.conftest import _admin_setup, setup_test_project


# ════════════════════════════════════════════════════════════════════
# Fixtures
# ════════════════════════════════════════════════════════════════════


@pytest.fixture
async def authed_client_user(async_client: AsyncClient, db: AsyncSession):
    from backend.app.motors.m21_portal_cliente.api import get_current_client_user
    from backend.app.main import app

    class _StubClienteUser:
        id = uuid.UUID("00000000-0000-0000-0000-000000000002")
        email = "cliente@example.test"
        client_id = None

    stub = _StubClienteUser()

    async def _override():
        return stub

    app.dependency_overrides[get_current_client_user] = _override
    yield async_client, stub
    app.dependency_overrides.pop(get_current_client_user, None)


# ════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════


async def _create_plan_with_tasks(
    db: AsyncSession,
    project_uuid: uuid.UUID,
) -> ProjectPlan:
    """Crea ProjectPlan + 3 WbsTask (2 cliente · 1 marcos) bajo admin context."""
    async with _admin_setup(db):
        plan = ProjectPlan(
            project_id=project_uuid,
            version=1,
            categoria="MEDIA",
            start_date=date.today(),
            end_date_estimated=date.today() + timedelta(weeks=12),
            estado="aprobado",
        )
        db.add(plan)
        await db.flush()

        for i, (code, name, responsible) in enumerate([
            ("WBS-001", "Reunión arranque", "marcos"),
            ("WBS-002", "Firmar DdA", "cliente"),
            ("WBS-003", "Revisar políticas", "mixto"),
        ]):
            task = WbsTask(
                project_plan_id=plan.id,
                project_id=project_uuid,
                task_code=code,
                task_name=name,
                phase=f"FASE_{i // 2}",
                start_date=date.today() + timedelta(days=i * 7),
                end_date=date.today() + timedelta(days=i * 7 + 3),
                responsible=responsible,
                status="pending",
                progress_pct=0,
                is_critical_path=(i == 0),
            )
            db.add(task)
        await db.flush()
    return plan


# ════════════════════════════════════════════════════════════════════
# GET /client-portal/plan
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_cliente_get_plan_returns_tasks_with_responsible(
    authed_client_user, db: AsyncSession,
) -> None:
    cli, stub = authed_client_user
    client_id_str, project_id_str = await setup_test_project(db)
    stub.client_id = uuid.UUID(client_id_str)
    project_uuid = uuid.UUID(project_id_str)

    await _create_plan_with_tasks(db, project_uuid)

    response = await cli.get("/api/v1/client-portal/plan")
    assert response.status_code == 200
    body = response.json()
    assert body["project_id"] == project_id_str
    assert body["plan_estado"] == "aprobado"
    assert len(body["tasks"]) == 3

    responsible_set = {t["responsible"] for t in body["tasks"]}
    assert {"marcos", "cliente", "mixto"} == responsible_set

    # is_critical_path preserved
    critical = [t for t in body["tasks"] if t["is_critical_path"]]
    assert len(critical) == 1


@pytest.mark.asyncio
async def test_cliente_get_plan_emits_audit_log(
    authed_client_user, db: AsyncSession,
) -> None:
    cli, stub = authed_client_user
    client_id_str, project_id_str = await setup_test_project(db)
    stub.client_id = uuid.UUID(client_id_str)
    project_uuid = uuid.UUID(project_id_str)

    await _create_plan_with_tasks(db, project_uuid)

    async with _admin_setup(db):
        pre = (
            await db.execute(
                text(
                    "SELECT COUNT(*) FROM audit_log "
                    "WHERE accion = 'cliente.plan.viewed' "
                    "AND project_id = :pid AND client_id = :cid"
                ),
                {"pid": project_id_str, "cid": client_id_str},
            )
        ).scalar()

    await cli.get("/api/v1/client-portal/plan")

    async with _admin_setup(db):
        post = (
            await db.execute(
                text(
                    "SELECT COUNT(*) FROM audit_log "
                    "WHERE accion = 'cliente.plan.viewed' "
                    "AND project_id = :pid AND client_id = :cid"
                ),
                {"pid": project_id_str, "cid": client_id_str},
            )
        ).scalar()
    assert post == pre + 1
    _ = project_uuid


@pytest.mark.asyncio
async def test_cliente_get_plan_404_no_project(
    authed_client_user, db: AsyncSession,
) -> None:
    cli, stub = authed_client_user
    stub.client_id = uuid.uuid4()  # no project asociado

    response = await cli.get("/api/v1/client-portal/plan")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_cliente_no_write_endpoints_exist(
    authed_client_user, db: AsyncSession,
) -> None:
    """ADR-014 sostained · cliente NO puede modificar plan."""
    cli, stub = authed_client_user
    client_id_str, project_id_str = await setup_test_project(db)
    stub.client_id = uuid.UUID(client_id_str)
    project_uuid = uuid.UUID(project_id_str)
    await _create_plan_with_tasks(db, project_uuid)

    # PATCH/PUT/DELETE on cliente plan endpoint must return 405
    r_patch = await cli.patch("/api/v1/client-portal/plan", json={})
    assert r_patch.status_code == 405, "PATCH should return 405 · ADR-014"
    r_put = await cli.put("/api/v1/client-portal/plan", json={})
    assert r_put.status_code == 405, "PUT should return 405 · ADR-014"
    r_delete = await cli.delete("/api/v1/client-portal/plan")
    assert r_delete.status_code == 405, "DELETE should return 405 · ADR-014"


@pytest.mark.asyncio
async def test_cliente_plan_empty_when_no_plan(
    authed_client_user, db: AsyncSession,
) -> None:
    """Project sin plan · returns 200 con empty tasks + milestones."""
    cli, stub = authed_client_user
    client_id_str, project_id_str = await setup_test_project(db)
    stub.client_id = uuid.UUID(client_id_str)

    response = await cli.get("/api/v1/client-portal/plan")
    assert response.status_code == 200
    body = response.json()
    assert body["tasks"] == []
    # Milestones may have kickoff/objetivo si project metadata · este
    # project no tiene fecha_kickoff por default · 0 milestones
    assert isinstance(body["milestones"], list)
