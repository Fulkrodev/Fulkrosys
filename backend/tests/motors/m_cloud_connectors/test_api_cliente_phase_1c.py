"""Sesión 3B-2B.8 Phase 1C · Cloud connectors cliente API tests.

Cubre:
  - cliente.cloud_connector.viewed audit_log emit en GET list (Sub-atom 5.A pattern)
  - cliente.cloud_connector.connect_initiated audit_log emit en POST connect
  - request-disconnect endpoint chat-mediated (ADR-014 sostained · NO actual revoke)
  - audit_log row INSERT con project_id + client_id 3-way OR
  - ChatService thread creation + message post
  - 404 cross-project isolation
  - 422 validation empty justification
"""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m_cloud_connectors.models import (
    CloudConnector,
    CloudConnectorProvider,
    CloudConnectorStatus,
)
from backend.tests.conftest import _admin_setup, setup_test_project


# ════════════════════════════════════════════════════════════════════
# Fixtures auth bypass cliente
# ════════════════════════════════════════════════════════════════════


@pytest.fixture
async def authed_client_user(async_client: AsyncClient, db: AsyncSession):
    """Cliente auth bypass via require_client_user · pattern reuse."""
    from backend.app.auth.dependencies import require_client_user
    from backend.app.main import app

    class _StubClienteUser:
        id = uuid.UUID("00000000-0000-0000-0000-000000000002")
        email = "cliente@example.test"
        client_id = None  # Set per test

    stub = _StubClienteUser()

    async def _override_client():
        return stub

    app.dependency_overrides[require_client_user] = _override_client
    yield async_client, stub
    app.dependency_overrides.pop(require_client_user, None)


# ════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════


async def _create_connector(
    db: AsyncSession,
    project_uuid: uuid.UUID,
    *,
    provider: str = CloudConnectorProvider.MICROSOFT_365.value,
    status: str = CloudConnectorStatus.CONNECTED.value,
) -> CloudConnector:
    """Create connector under admin context (RLS bypass)."""
    async with _admin_setup(db):
        connector = CloudConnector(
            project_id=project_uuid,
            provider=provider,
            status=status,
        )
        db.add(connector)
        await db.flush()
    return connector


async def _count_audit_log(
    db: AsyncSession, *, accion: str, project_uuid: uuid.UUID
) -> int:
    """Count audit_log rows with given accion + project_id."""
    async with _admin_setup(db):
        row = (
            await db.execute(
                text(
                    "SELECT COUNT(*) FROM audit_log WHERE accion = :a "
                    "AND project_id = :pid"
                ),
                {"a": accion, "pid": str(project_uuid)},
            )
        ).fetchone()
    return int(row[0]) if row else 0


async def _ensure_client_user(
    db: AsyncSession, *, user_id: uuid.UUID, client_id: uuid.UUID, email: str
) -> None:
    """Insert client_users row matching stub user · FK satisfaction chat_threads."""
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
                "VALUES (:uid, :cid, :email, 'x', 'Test Cliente', false, now())"
            ),
            {"uid": str(user_id), "cid": str(client_id), "email": email},
        )


# ════════════════════════════════════════════════════════════════════
# GET list · emits cliente.cloud_connector.viewed
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_list_cloud_connectors_emits_viewed_audit_log(
    authed_client_user, db: AsyncSession,
) -> None:
    """Sub-atom 5.A pattern · audit_log con project_id + client_id."""
    cli, stub = authed_client_user
    client_id_str, project_id_str = await setup_test_project(db)
    stub.client_id = uuid.UUID(client_id_str)
    project_uuid = uuid.UUID(project_id_str)

    await _create_connector(db, project_uuid)

    pre_count = await _count_audit_log(
        db, accion="cliente.cloud_connector.viewed", project_uuid=project_uuid,
    )

    response = await cli.get("/api/v1/client-portal/cloud-connectors")
    assert response.status_code == 200

    post_count = await _count_audit_log(
        db, accion="cliente.cloud_connector.viewed", project_uuid=project_uuid,
    )
    assert post_count == pre_count + 1


# ════════════════════════════════════════════════════════════════════
# POST connect · emits cliente.cloud_connector.connect_initiated
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_init_connect_emits_connect_initiated_audit_log(
    authed_client_user, db: AsyncSession,
) -> None:
    """connect_initiated emit · payload incluye provider + connector_id."""
    cli, stub = authed_client_user
    client_id_str, project_id_str = await setup_test_project(db)
    stub.client_id = uuid.UUID(client_id_str)
    project_uuid = uuid.UUID(project_id_str)

    pre_count = await _count_audit_log(
        db, accion="cliente.cloud_connector.connect_initiated",
        project_uuid=project_uuid,
    )

    response = await cli.post(
        "/api/v1/client-portal/cloud-connectors/connect/microsoft_365",
    )
    assert response.status_code == 201
    body = response.json()
    assert body["provider"] == "microsoft_365"
    assert body["next_step"] == "oauth_redirect"

    post_count = await _count_audit_log(
        db, accion="cliente.cloud_connector.connect_initiated",
        project_uuid=project_uuid,
    )
    assert post_count == pre_count + 1


# ════════════════════════════════════════════════════════════════════
# POST request-disconnect · chat-mediated (ADR-014 sostained)
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_request_disconnect_emits_audit_log_and_creates_chat(
    authed_client_user, db: AsyncSession,
) -> None:
    """ADR-014 sostained · NO revoke · audit_log + chat thread + SSE dispatch."""
    cli, stub = authed_client_user
    client_id_str, project_id_str = await setup_test_project(db)
    stub.client_id = uuid.UUID(client_id_str)
    project_uuid = uuid.UUID(project_id_str)
    await _ensure_client_user(
        db, user_id=stub.id, client_id=stub.client_id, email=stub.email,
    )

    connector = await _create_connector(db, project_uuid)

    response = await cli.post(
        f"/api/v1/client-portal/cloud-connectors/{connector.id}/request-disconnect",
        json={"justification": "Cambiamos a otro proveedor de identidad."},
    )
    assert response.status_code == 202
    body = response.json()
    assert body["provider"] == CloudConnectorProvider.MICROSOFT_365.value
    assert body["connector_id"] == str(connector.id)
    assert "thread_id" in body
    assert "Marcos" in body["friendly_message"]

    # 1) audit_log emit
    audit_count = await _count_audit_log(
        db, accion="cliente.cloud_connector.disconnect_requested",
        project_uuid=project_uuid,
    )
    assert audit_count == 1

    # 2) ADR-014 sostained · connector status NO cambia (NO revoke ejecutado)
    async with _admin_setup(db):
        row = (
            await db.execute(
                text("SELECT status FROM cloud_connectors WHERE id = :cid"),
                {"cid": str(connector.id)},
            )
        ).fetchone()
    assert row[0] == CloudConnectorStatus.CONNECTED.value

    # 3) Chat thread + message persisted
    async with _admin_setup(db):
        thread_row = (
            await db.execute(
                text(
                    "SELECT id, subject FROM chat_threads "
                    "WHERE project_id = :pid"
                ),
                {"pid": str(project_uuid)},
            )
        ).fetchone()
        msg_row = (
            await db.execute(
                text(
                    "SELECT content FROM chat_messages "
                    "WHERE thread_id = :tid AND sender_type = 'client'"
                ),
                {"tid": str(thread_row[0])},
            )
        ).fetchone()
    assert thread_row is not None
    assert "Microsoft 365" in thread_row[1]
    assert msg_row is not None
    assert "Solicito desconectar" in msg_row[0]
    assert "Cambiamos a otro proveedor" in msg_row[0]


@pytest.mark.asyncio
async def test_request_disconnect_404_if_connector_not_in_project(
    authed_client_user, db: AsyncSession,
) -> None:
    """Cross-project isolation · connector de OTRO project devuelve 404."""
    cli, stub = authed_client_user
    client_id_str, project_id_str = await setup_test_project(db)
    stub.client_id = uuid.UUID(client_id_str)

    # Create connector under DIFFERENT project (other client)
    other_client_str, other_project_str = await setup_test_project(db)
    other_project_uuid = uuid.UUID(other_project_str)
    other_connector = await _create_connector(db, other_project_uuid)

    response = await cli.post(
        f"/api/v1/client-portal/cloud-connectors/{other_connector.id}/request-disconnect",
        json={"justification": "Attempted cross-project access"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_request_disconnect_validation_empty_justification(
    authed_client_user, db: AsyncSession,
) -> None:
    """Justification min_length=1 · empty string → 422 validation error."""
    cli, stub = authed_client_user
    client_id_str, project_id_str = await setup_test_project(db)
    stub.client_id = uuid.UUID(client_id_str)
    project_uuid = uuid.UUID(project_id_str)

    connector = await _create_connector(db, project_uuid)

    response = await cli.post(
        f"/api/v1/client-portal/cloud-connectors/{connector.id}/request-disconnect",
        json={"justification": ""},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_request_disconnect_reuses_existing_open_thread(
    authed_client_user, db: AsyncSession,
) -> None:
    """ChatService.get_or_create_thread idempotente · re-uses open thread."""
    cli, stub = authed_client_user
    client_id_str, project_id_str = await setup_test_project(db)
    stub.client_id = uuid.UUID(client_id_str)
    project_uuid = uuid.UUID(project_id_str)
    await _ensure_client_user(
        db, user_id=stub.id, client_id=stub.client_id, email=stub.email,
    )

    connector_a = await _create_connector(db, project_uuid)
    connector_b = await _create_connector(
        db, project_uuid, provider=CloudConnectorProvider.GITHUB.value,
    )

    # 1st request → creates thread
    r1 = await cli.post(
        f"/api/v1/client-portal/cloud-connectors/{connector_a.id}/request-disconnect",
        json={"justification": "Razón A"},
    )
    assert r1.status_code == 202
    thread_a = r1.json()["thread_id"]

    # 2nd request (different connector) → re-uses open thread
    r2 = await cli.post(
        f"/api/v1/client-portal/cloud-connectors/{connector_b.id}/request-disconnect",
        json={"justification": "Razón B"},
    )
    assert r2.status_code == 202
    thread_b = r2.json()["thread_id"]

    assert thread_a == thread_b, "Should reuse same open thread"

    # 2 audit_log rows expected
    audit_count = await _count_audit_log(
        db, accion="cliente.cloud_connector.disconnect_requested",
        project_uuid=project_uuid,
    )
    assert audit_count == 2
