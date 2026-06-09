"""F-18-01b · m17 timeline cliente setea app.current_client_id (contexto RLS).

Mismo gap fail-closed que F-18-01 (copiloto m11), en otro motor: el runtime
conecta como ``fulkro_app`` (RLS activa) y NO hay middleware que setee
``app.current_client_id``. ``get_cliente_plan_timeline`` resolvía el proyecto
(``_resolve_project_id``, query ``WHERE client_id=:cid``) ANTES de setear el
contexto → en prod esa query era ciega → ``project_id=None`` → 404 al dueño
legítimo (fail-closed, NO fuga).

Estos tests son PROD-FIELES a propósito: NO usan ``setup_test_project`` (que
setea ``app.current_client_id`` en la sesión compartida → falso verde · es el
atajo que enmascaró el bug, igual que en F-18-01). Siembran vía ``_admin_setup``
(bypass RLS solo para el INSERT) dejando la sesión SIN contexto, replicando
producción. El fix (``_resolve_project_id_scoped``) setea client_id ANTES de
resolver.
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.planning import ProjectPlan, WbsTask
from backend.app.motors.m17_planning.portal_api import (
    _resolve_project_id,
    _resolve_project_id_scoped,
)
from backend.tests.conftest import _admin_setup


# ════════════════════════════════════════════════════════════════════
# Helpers · siembra SIN contexto (prod-fiel) sobre la sesión harness
# ════════════════════════════════════════════════════════════════════


async def _seed_client_project_no_ctx(
    db: AsyncSession,
) -> tuple[uuid.UUID, uuid.UUID]:
    """INSERT client + project vía _admin_setup (bypass RLS) · NO setea ctx.

    A diferencia de ``setup_test_project``, NO llama ``set_config`` de
    ``app.current_client_id`` → la sesión queda como en producción (ciega
    hasta que el SUT setee el contexto).
    """
    cid = uuid.uuid4()
    pid = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO clients (id, nombre, cif, created_at) "
                "VALUES (:id, 'F1801b Client', :cif, now())"
            ),
            {"id": str(cid), "cif": cif},
        )
        await db.execute(
            text(
                "INSERT INTO projects (id, client_id, nombre, fase, created_at) "
                "VALUES (:id, :cid, 'F1801b Project', 'implantacion', now())"
            ),
            {"id": str(pid), "cid": str(cid)},
        )
    return cid, pid


async def _seed_plan_with_tasks_no_ctx(
    db: AsyncSession, project_uuid: uuid.UUID,
) -> None:
    """ProjectPlan + 3 WbsTask bajo _admin_setup (bypass RLS) · NO setea ctx."""
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
            db.add(WbsTask(
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
            ))
        await db.flush()


@pytest.fixture
async def _stub_client_user(async_client: AsyncClient):
    """Override get_current_client_user · client_id seteado por el test."""
    from backend.app.main import app
    from backend.app.motors.m21_portal_cliente.api import get_current_client_user

    class _Stub:
        id = uuid.UUID("00000000-0000-0000-0000-0000000018b1")
        email = "f1801b@example.test"
        client_id: uuid.UUID | None = None

    stub = _Stub()

    async def _override():
        return stub

    app.dependency_overrides[get_current_client_user] = _override
    yield async_client, stub
    app.dependency_overrides.pop(get_current_client_user, None)


# ════════════════════════════════════════════════════════════════════
# 1 · A/B nivel-helper · réplica del contraste F-18-01 en m17
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_resolve_project_id_blind_without_ctx_sees_with_ctx(db: AsyncSession):
    """A (sin ctx) = ciego (None) · B (+set_tenant_context) = ve · datos idénticos.

    La ÚNICA diferencia A↔B es que ``_resolve_project_id_scoped`` setea
    ``app.current_client_id`` antes de resolver. No es ausencia de datos; es
    ausencia de contexto (RLS oculta projects sin él).
    """
    cid, pid = await _seed_client_project_no_ctx(db)

    # A · prod-réplica · lo que hacía el timeline (sin contexto)
    a_pid = await _resolve_project_id(db, cid)
    assert a_pid is None, "A debe ser ciego (RLS oculta projects sin ctx)"

    # B · el fix · _resolve_project_id_scoped setea ctx antes de resolver
    b_pid = await _resolve_project_id_scoped(db, cid)
    assert b_pid == pid, "B debe ver el proyecto del cliente"


# ════════════════════════════════════════════════════════════════════
# 2 · Endpoint prod-fiel · sin fix → 404 ciego · con fix → 200 que ve tasks
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_cliente_plan_prod_faithful_sees_tasks(
    _stub_client_user, db: AsyncSession,
):
    """PROD-FIEL: siembra sin ctx (NO setup_test_project). Sin el fix el
    endpoint sería 404 (resolución ciega); con el fix devuelve 200 y VE sus
    3 tasks · prueba de que el contexto se setea antes de resolver.
    """
    cli, stub = _stub_client_user
    cid, pid = await _seed_client_project_no_ctx(db)
    stub.client_id = cid
    await _seed_plan_with_tasks_no_ctx(db, pid)

    resp = await cli.get("/api/v1/client-portal/plan")

    assert resp.status_code == 200, resp.text  # sin fix sería 404 ciego
    body = resp.json()
    assert body["project_id"] == str(pid)
    assert body["plan_estado"] == "aprobado"
    assert len(body["tasks"]) == 3, body
    assert {t["responsible"] for t in body["tasks"]} == {"marcos", "cliente", "mixto"}
