"""Sesión 3B-2B.8 Phase 1D · /copilot/hint endpoint tests admin + cliente.

Cubre:
  - Admin /copilot/hint?project_id=... happy path · phase pre_venta → contract action
  - Cliente /client-portal/copiloto/hint · IMPLANTACION → sign_dda urgent
  - audit_log emit copilot.hint.generated con project_id + client_id Sub-atom 5.A
  - No action edge case (RETAINER admin sin offer action → has_action=True for retainer offer)
  - Backward-compat fallback try/except (scanner raises → 200 OK has_action=False)
"""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.workflow_phase import WorkflowPhase
from backend.tests.conftest import _admin_setup, setup_test_project


# ════════════════════════════════════════════════════════════════════
# Fixtures
# ════════════════════════════════════════════════════════════════════


@pytest.fixture
async def authed_admin_client(async_client: AsyncClient, db: AsyncSession):
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


async def _set_project_phase(
    db: AsyncSession, project_uuid: uuid.UUID, phase: WorkflowPhase,
) -> None:
    """Bypass tg_projects_phase_changed trigger (pre-existing constraint bug)."""
    async with _admin_setup(db):
        await db.execute(text("SET LOCAL session_replication_role = 'replica'"))
        await db.execute(
            text("UPDATE projects SET fase = :p WHERE id = :pid"),
            {"p": phase.value, "pid": str(project_uuid)},
        )
        await db.execute(text("SET LOCAL session_replication_role = 'origin'"))


async def _ensure_client_user(
    db: AsyncSession, *, user_id: uuid.UUID, client_id: uuid.UUID, email: str
) -> None:
    async with _admin_setup(db):
        existing = (
            await db.execute(
                text("SELECT 1 FROM client_users WHERE id = :uid"),
                {"uid": str(user_id)},
            )
        ).fetchone()
        if existing:
            return
        await db.execute(
            text(
                "INSERT INTO client_users (id, client_id, email, password_hash, "
                "full_name, must_change_password, created_at) "
                "VALUES (:uid, :cid, :email, 'x', 'Test', false, now())"
            ),
            {"uid": str(user_id), "cid": str(client_id), "email": email},
        )


# ════════════════════════════════════════════════════════════════════
# Admin endpoint /copilot/hint
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_admin_hint_pre_venta_returns_governance_action(
    authed_admin_client: AsyncClient, db: AsyncSession,
) -> None:
    """CAMBIO Batch 2 (Opción A · cablear FASE 0 gobierno).

    Antes: el hint admin en PRE_VENTA devolvía la genérica
    (motor=m14 · action=prepare_contract). Ahora, con gobierno inyectado en
    fases tempranas mientras fase0_completa=False, un proyecto fresco SIN docs
    de gobierno devuelve el kickoff de gobierno (motor=m17 · action=
    fase0_kickoff · urgent) como top, vía top_action_for_role. prepare_contract
    sigue existiendo en next_admin_actions (secundaria · cubierto en
    test_workflow_state_scanner) pero ya no es el top del hint.
    """
    _, project_id_str = await setup_test_project(db)

    response = await authed_admin_client.get(
        "/api/v1/copilot/hint",
        params={"project_id": project_id_str},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["has_action"] is True
    assert body["motor"] == "m17"
    assert body["action"] == "fase0_kickoff"
    assert body["priority"] == "urgent"
    assert body["current_phase"] == "pre_venta"


@pytest.mark.asyncio
async def test_admin_hint_emits_audit_log(
    authed_admin_client: AsyncClient, db: AsyncSession,
) -> None:
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)

    async with _admin_setup(db):
        pre = (
            await db.execute(
                text(
                    "SELECT COUNT(*) FROM audit_log "
                    "WHERE accion = 'copilot.hint.generated' "
                    "AND project_id = :pid"
                ),
                {"pid": project_id_str},
            )
        ).scalar()

    await authed_admin_client.get(
        "/api/v1/copilot/hint",
        params={"project_id": project_id_str},
    )

    async with _admin_setup(db):
        post = (
            await db.execute(
                text(
                    "SELECT COUNT(*) FROM audit_log "
                    "WHERE accion = 'copilot.hint.generated' "
                    "AND project_id = :pid"
                ),
                {"pid": project_id_str},
            )
        ).scalar()
    assert post == pre + 1
    _ = project_uuid  # quiet lint


# ════════════════════════════════════════════════════════════════════
# Cliente endpoint /client-portal/copiloto/hint
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_cliente_hint_implantacion_returns_sign_dda_urgent(
    authed_client_user, db: AsyncSession,
) -> None:
    cli, stub = authed_client_user
    client_id_str, project_id_str = await setup_test_project(db)
    stub.client_id = uuid.UUID(client_id_str)
    project_uuid = uuid.UUID(project_id_str)
    await _ensure_client_user(
        db, user_id=stub.id, client_id=stub.client_id, email=stub.email,
    )
    await _set_project_phase(db, project_uuid, WorkflowPhase.IMPLANTACION)

    response = await cli.get("/api/v1/client-portal/copiloto/hint")
    assert response.status_code == 200
    body = response.json()
    assert body["has_action"] is True
    assert body["motor"] == "m03"
    assert body["action"] == "sign_dda"
    assert body["priority"] == "urgent"
    assert body["current_phase"] == "implantacion"
    # R29 sostained · friendly
    assert "DdA" in body["message"]


@pytest.mark.asyncio
async def test_cliente_hint_emits_audit_log_with_client_id(
    authed_client_user, db: AsyncSession,
) -> None:
    cli, stub = authed_client_user
    client_id_str, project_id_str = await setup_test_project(db)
    stub.client_id = uuid.UUID(client_id_str)
    project_uuid = uuid.UUID(project_id_str)
    await _ensure_client_user(
        db, user_id=stub.id, client_id=stub.client_id, email=stub.email,
    )
    # IMPLANTACION has cliente actions · ensures top_action_for_role NOT None
    await _set_project_phase(db, project_uuid, WorkflowPhase.IMPLANTACION)

    async with _admin_setup(db):
        pre = (
            await db.execute(
                text(
                    "SELECT COUNT(*) FROM audit_log "
                    "WHERE accion = 'copilot.hint.generated' "
                    "AND project_id = :pid AND client_id = :cid"
                ),
                {"pid": project_id_str, "cid": client_id_str},
            )
        ).scalar()

    await cli.get("/api/v1/client-portal/copiloto/hint")

    async with _admin_setup(db):
        post = (
            await db.execute(
                text(
                    "SELECT COUNT(*) FROM audit_log "
                    "WHERE accion = 'copilot.hint.generated' "
                    "AND project_id = :pid AND client_id = :cid"
                ),
                {"pid": project_id_str, "cid": client_id_str},
            )
        ).scalar()
    assert post == pre + 1


@pytest.mark.asyncio
async def test_cliente_hint_no_project_returns_friendly_empty(
    authed_client_user, db: AsyncSession,
) -> None:
    """Cliente sin proyecto activo → has_action=False · NO 404 (graceful R29)."""
    cli, stub = authed_client_user
    stub.client_id = uuid.uuid4()  # client_id sin project asociado

    response = await cli.get("/api/v1/client-portal/copiloto/hint")
    assert response.status_code == 200
    body = response.json()
    assert body["has_action"] is False
    assert "proyecto" in body["message"].lower()
