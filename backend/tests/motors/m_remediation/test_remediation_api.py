"""Integration tests · m_remediation API (ADR-055).

Admin: catálogo · crear · listar · autorizar · 400 acción desconocida.
Cliente: listar (R29 friendly) · autorizar GUARDED · aislamiento RLS por proyecto.
"""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m_cloud_connectors.models import (
    CloudConnector,
    CloudConnectorProvider,
    CloudConnectorStatus,
)
from backend.tests.conftest import _admin_setup, setup_test_project


@pytest.fixture(autouse=True)
def _global_on(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("FULKRO_REMEDIATION_ENABLED", "true")


@pytest.fixture
async def authed_admin_client(client: AsyncClient, db: AsyncSession):
    from backend.app.auth.dependencies import require_owner
    from backend.app.main import app

    class _StubUser:
        id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        email = "marcos@fulkro.test"
        is_owner = True

    async def _override_owner():
        return _StubUser()

    app.dependency_overrides[require_owner] = _override_owner
    yield client
    app.dependency_overrides.pop(require_owner, None)


@pytest.fixture
async def authed_client_user(client: AsyncClient, db: AsyncSession):
    from backend.app.auth.dependencies import require_client_user
    from backend.app.main import app

    class _StubClienteUser:
        id = uuid.UUID("00000000-0000-0000-0000-000000000002")
        email = "cliente@example.test"
        client_id = None

    stub = _StubClienteUser()

    async def _override_client():
        return stub

    app.dependency_overrides[require_client_user] = _override_client
    yield client, stub
    app.dependency_overrides.pop(require_client_user, None)


async def _create_connector(
    db: AsyncSession, project_uuid: uuid.UUID, *, policy: str = "full",
) -> CloudConnector:
    async with _admin_setup(db):
        connector = CloudConnector(
            project_id=project_uuid,
            provider=CloudConnectorProvider.AWS.value,
            status=CloudConnectorStatus.CONNECTED.value,
            remediation_enabled=True,
            auto_remediation_policy=policy,
        )
        db.add(connector)
        await db.flush()
    return connector


# ── admin ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_catalog(authed_admin_client: AsyncClient, db: AsyncSession) -> None:
    _, pid = await setup_test_project(db)
    r = await authed_admin_client.get(f"/api/v1/admin/projects/{pid}/remediation/catalog")
    assert r.status_code == 200
    actions = r.json()["actions"]
    assert len(actions) >= 10
    keys = {a["action_type"] for a in actions}
    assert "enable_bucket_encryption" in keys
    assert all("cliente_blurb" in a and "tier" in a for a in actions)


@pytest.mark.asyncio
async def test_admin_create_and_list_safe_auto(
    authed_admin_client: AsyncClient, db: AsyncSession,
) -> None:
    _, pid = await setup_test_project(db)
    project_uuid = uuid.UUID(pid)
    connector = await _create_connector(db, project_uuid)

    r = await authed_admin_client.post(
        f"/api/v1/admin/projects/{pid}/remediation/jobs",
        json={
            "action_type": "enable_bucket_encryption",
            "source_kind": "cloud_gap",
            "connector_id": str(connector.id),
            "target_ref": "arn:aws:s3:::demo",
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["tier"] == "safe_auto"
    assert body["status"] == "queued"
    assert body["title"]

    r2 = await authed_admin_client.get(
        f"/api/v1/admin/projects/{pid}/remediation/jobs",
    )
    assert r2.status_code == 200
    assert len(r2.json()["jobs"]) == 1


@pytest.mark.asyncio
async def test_admin_create_guarded_awaits_authorization(
    authed_admin_client: AsyncClient, db: AsyncSession,
) -> None:
    _, pid = await setup_test_project(db)
    project_uuid = uuid.UUID(pid)
    connector = await _create_connector(db, project_uuid)
    r = await authed_admin_client.post(
        f"/api/v1/admin/projects/{pid}/remediation/jobs",
        json={
            "action_type": "require_mfa_enforce",
            "connector_id": str(connector.id),
            "target_ref": "tenant-1",
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["tier"] == "guarded"
    assert body["status"] == "awaiting_authorization"

    # autorizar admin → queued
    jid = body["id"]
    r3 = await authed_admin_client.post(
        f"/api/v1/admin/projects/{pid}/remediation/jobs/{jid}/authorize",
    )
    assert r3.status_code == 200
    assert r3.json()["status"] == "queued"
    assert r3.json()["authorized_at"] is not None


@pytest.mark.asyncio
async def test_admin_create_unknown_action_400(
    authed_admin_client: AsyncClient, db: AsyncSession,
) -> None:
    _, pid = await setup_test_project(db)
    r = await authed_admin_client.post(
        f"/api/v1/admin/projects/{pid}/remediation/jobs",
        json={"action_type": "does_not_exist"},
    )
    assert r.status_code == 400


# ── cliente ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cliente_list_and_authorize(
    authed_client_user, db: AsyncSession,
) -> None:
    client, stub = authed_client_user
    client_id, pid = await setup_test_project(db)
    project_uuid = uuid.UUID(pid)
    stub.client_id = uuid.UUID(client_id)
    connector = await _create_connector(db, project_uuid)

    # Crear un job GUARDED directamente (vía servicio) para que el cliente lo autorice.
    from backend.app.motors.m_remediation.service import RemediationService
    svc = RemediationService(db)
    job = await svc.create_job(
        project_id=project_uuid, action_type="require_mfa_enforce",
        source_kind="cloud_gap", connector_id=connector.id, target_ref="tenant-1",
    )
    await db.flush()

    # Cliente lista (vista friendly).
    r = await client.get("/api/v1/client-portal/remediation/jobs")
    assert r.status_code == 200
    jobs = r.json()["jobs"]
    assert len(jobs) == 1
    assert jobs[0]["necesita_autorizacion"] is True
    assert jobs[0]["explicacion"]  # R29 blurb friendly
    assert "estado" in jobs[0]

    # Cliente autoriza.
    r2 = await client.post(
        f"/api/v1/client-portal/remediation/jobs/{job.id}/authorize",
    )
    assert r2.status_code == 200


@pytest.mark.asyncio
async def test_cliente_rls_isolation_other_project(
    authed_client_user, db: AsyncSession,
) -> None:
    client, stub = authed_client_user
    # Proyecto A (del cliente) + proyecto B (ajeno · job creado allí).
    client_id_a, pid_a = await setup_test_project(db)
    stub.client_id = uuid.UUID(client_id_a)
    _, pid_b = await setup_test_project(db)  # esto deja el contexto en B
    project_b = uuid.UUID(pid_b)
    connector_b = await _create_connector(db, project_b)
    from backend.app.motors.m_remediation.service import RemediationService
    svc = RemediationService(db)
    job_b = await svc.create_job(
        project_id=project_b, action_type="require_mfa_enforce",
        source_kind="cloud_gap", connector_id=connector_b.id, target_ref="t-b",
    )
    await db.flush()

    # El cliente A intenta autorizar un job del proyecto B → RLS lo oculta (404).
    r = await client.post(
        f"/api/v1/client-portal/remediation/jobs/{job_b.id}/authorize",
    )
    assert r.status_code == 404
