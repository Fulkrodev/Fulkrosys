"""Tests de orquestación de los writers M365 / Azure / Google (sin tenant real).

Mockean los helpers HTTP (Graph/ARM/Drive) con un estado en memoria de alta
fidelidad y ejecutan el ciclo completo del motor (read→apply→verify) comprobando
que el writer construye los payloads correctos y deja el estado deseado. La
validación contra un tenant vivo se hace en el alta del cliente.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m_cloud_connectors.models import (
    CloudConnector,
    CloudConnectorStatus,
)
from backend.app.motors.m_remediation.cloud_writers.azure import AzureRemediationWriter
from backend.app.motors.m_remediation.cloud_writers.google_workspace import (
    GoogleWorkspaceRemediationWriter,
)
from backend.app.motors.m_remediation.cloud_writers.microsoft365 import (
    Microsoft365RemediationWriter,
)
from backend.app.motors.m_remediation.service import RemediationService
from backend.tests.conftest import _admin_setup, setup_test_project


@pytest.fixture(autouse=True)
def _global_on(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("FULKRO_REMEDIATION_ENABLED", "true")


async def _connector(
    db: AsyncSession, project_uuid: uuid.UUID, provider: str,
) -> CloudConnector:
    async with _admin_setup(db):
        c = CloudConnector(
            project_id=project_uuid,
            provider=provider,
            status=CloudConnectorStatus.CONNECTED.value,
            remediation_enabled=True,
            auto_remediation_policy="full",
        )
        db.add(c)
        await db.flush()
    return c


# ── M365 (Graph Conditional Access) ────────────────────────────────────────


@pytest.mark.asyncio
async def test_m365_require_mfa_conditional_access(db: AsyncSession) -> None:
    _, pid = await setup_test_project(db)
    project_uuid = uuid.UUID(pid)
    connector = await _connector(db, project_uuid, "microsoft_365")

    policies: list[dict] = []
    counter = {"n": 0}

    w = Microsoft365RemediationWriter(
        {"tenant_id": "t", "client_id": "c", "client_secret": "s"},
    )

    async def _tok():
        return "tok"

    async def _list():
        return list(policies)

    async def _create(body):
        counter["n"] += 1
        p = {"id": f"p{counter['n']}", **body}
        policies.append(p)
        return p

    async def _update(pid_, body):
        for p in policies:
            if p["id"] == pid_:
                p.update(body)
        return {}

    async def _delete(pid_):
        policies[:] = [p for p in policies if p["id"] != pid_]
        return {}

    w._get_token = _tok  # type: ignore[assignment]
    w._list_policies = _list  # type: ignore[assignment]
    w._create_policy = _create  # type: ignore[assignment]
    w._update_policy = _update  # type: ignore[assignment]
    w._delete_policy = _delete  # type: ignore[assignment]

    svc = RemediationService(db)
    job = await svc.create_job(
        project_id=project_uuid, action_type="require_mfa_conditional_access",
        source_kind="cloud_gap", connector_id=connector.id, target_ref="tenant",
    )
    job = await svc.execute_job(job.id, writer=w)
    assert job.status == "succeeded"
    assert len(policies) == 1
    assert policies[0]["state"] == "enabledForReportingButNotEnforced"
    assert policies[0]["grantControls"]["builtInControls"] == ["mfa"]


# ── Azure (ARM storage) ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_azure_disable_public_blob(db: AsyncSession) -> None:
    _, pid = await setup_test_project(db)
    project_uuid = uuid.UUID(pid)
    connector = await _connector(db, project_uuid, "azure")

    state = {"properties": {"allowBlobPublicAccess": True}}
    w = AzureRemediationWriter({"tenant_id": "t", "client_id": "c", "client_secret": "s"})

    async def _tok():
        return "tok"

    async def _get(rid):
        return state

    async def _patch(rid, body):
        state["properties"].update(body["properties"])
        return {}

    w._get_token = _tok  # type: ignore[assignment]
    w._arm_get = _get  # type: ignore[assignment]
    w._arm_patch = _patch  # type: ignore[assignment]

    svc = RemediationService(db)
    job = await svc.create_job(
        project_id=project_uuid, action_type="azure_storage_disable_public_blob",
        source_kind="cloud_gap", connector_id=connector.id,
        target_ref="/subscriptions/x/resourceGroups/y/providers/Microsoft.Storage/storageAccounts/z",
    )
    job = await svc.execute_job(job.id, writer=w)
    assert job.status == "succeeded"
    assert state["properties"]["allowBlobPublicAccess"] is False


# ── Google (Drive) · GUARDED → autorización previa ──────────────────────────


@pytest.mark.asyncio
async def test_google_drive_restrict_external_guarded(db: AsyncSession) -> None:
    _, pid = await setup_test_project(db)
    project_uuid = uuid.UUID(pid)
    connector = await _connector(db, project_uuid, "google_workspace")

    drive = {"id": "d1", "restrictions": {"domainUsersOnly": False}}
    w = GoogleWorkspaceRemediationWriter(
        {"service_account_info": {"x": 1}, "admin_email": "admin@x.com"},
    )

    async def _tok():
        return "tok"

    async def _get(did):
        return drive

    async def _patch(did, body):
        drive["restrictions"].update(body["restrictions"])
        return {}

    w._get_token = _tok  # type: ignore[assignment]
    w._drive_get = _get  # type: ignore[assignment]
    w._drive_patch = _patch  # type: ignore[assignment]

    svc = RemediationService(db)
    job = await svc.create_job(
        project_id=project_uuid, action_type="google_drive_restrict_external",
        source_kind="cloud_gap", connector_id=connector.id, target_ref="d1",
    )
    # GUARDED → requiere autorización previa.
    assert job.status == "awaiting_authorization"
    await svc.authorize_job(job.id, user_id=uuid.uuid4())
    job = await svc.get_job(job.id)
    job = await svc.execute_job(job.id, writer=w)
    assert job.status == "succeeded"
    assert drive["restrictions"]["domainUsersOnly"] is True
