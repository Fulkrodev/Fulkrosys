"""Tests de SIMULADOR HTTP (respx) para los writers M365 / Azure / Google.

A diferencia de un mock de métodos, esto intercepta la capa httpx con un backend
EN MEMORIA CON ESTADO: ejercita el código REAL del writer (adquisición de token,
construcción de URL, cabeceras, serialización del payload, parsing de la respuesta)
y comprueba que un GET posterior refleja el PATCH/POST previo. Es el mismo nivel de
fidelidad que moto para AWS, sin tenant real.
"""
from __future__ import annotations

import json
import uuid

import httpx
import pytest
import respx
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


# ── simuladores HTTP con estado ──────────────────────────────────────────────


def _register_graph(router: respx.Router, state: dict) -> None:
    router.post(
        url__regex=r"https://login\.microsoftonline\.com/.+/oauth2/v2\.0/token",
    ).mock(return_value=httpx.Response(200, json={"access_token": "tok", "expires_in": 3600}))

    router.get(
        url__regex=r"https://graph\.microsoft\.com/v1\.0/identity/conditionalAccess/policies$",
    ).mock(side_effect=lambda req: httpx.Response(200, json={"value": state["policies"]}))

    def _create(req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content)
        state["n"] += 1
        body["id"] = f"pol-{state['n']}"
        state["policies"].append(body)
        return httpx.Response(201, json=body)

    router.post(
        url__regex=r"https://graph\.microsoft\.com/v1\.0/identity/conditionalAccess/policies$",
    ).mock(side_effect=_create)

    def _patch(req: httpx.Request) -> httpx.Response:
        pid = req.url.path.rstrip("/").split("/")[-1]
        body = json.loads(req.content)
        for p in state["policies"]:
            if p.get("id") == pid:
                p.update(body)
        return httpx.Response(204)

    router.patch(url__regex=r".+/conditionalAccess/policies/[^/]+$").mock(side_effect=_patch)

    def _delete(req: httpx.Request) -> httpx.Response:
        pid = req.url.path.rstrip("/").split("/")[-1]
        state["policies"][:] = [p for p in state["policies"] if p.get("id") != pid]
        return httpx.Response(204)

    router.delete(url__regex=r".+/conditionalAccess/policies/[^/]+$").mock(side_effect=_delete)


def _register_arm(router: respx.Router, state: dict) -> None:
    router.post(
        url__regex=r"https://login\.microsoftonline\.com/.+/oauth2/v2\.0/token",
    ).mock(return_value=httpx.Response(200, json={"access_token": "tok", "expires_in": 3600}))

    router.get(url__regex=r"https://management\.azure\.com/.+").mock(
        side_effect=lambda req: httpx.Response(200, json={"properties": state["properties"]}),
    )

    def _patch(req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content)
        state["properties"].update(body.get("properties", {}))
        return httpx.Response(200, json={"properties": state["properties"]})

    router.patch(url__regex=r"https://management\.azure\.com/.+").mock(side_effect=_patch)


def _register_drive(router: respx.Router, state: dict) -> None:
    router.get(url__regex=r"https://www\.googleapis\.com/drive/v3/drives/[^/?]+").mock(
        side_effect=lambda req: httpx.Response(
            200, json={"id": "d1", "restrictions": state["restrictions"]},
        ),
    )

    def _patch(req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content)
        state["restrictions"].update(body.get("restrictions", {}))
        return httpx.Response(200, json={"id": "d1", "restrictions": state["restrictions"]})

    router.patch(url__regex=r"https://www\.googleapis\.com/drive/v3/drives/[^/?]+").mock(
        side_effect=_patch,
    )


# ── M365 (Graph · simulador) ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_m365_simulator_full_flow(db: AsyncSession) -> None:
    _, pid = await setup_test_project(db)
    project_uuid = uuid.UUID(pid)
    connector = await _connector(db, project_uuid, "microsoft_365")
    state = {"policies": [], "n": 0}
    with respx.mock(assert_all_called=False) as router:
        _register_graph(router, state)
        w = Microsoft365RemediationWriter(
            {"tenant_id": "t", "client_id": "c", "client_secret": "s"},
        )
        svc = RemediationService(db)
        job = await svc.create_job(
            project_id=project_uuid, action_type="require_mfa_conditional_access",
            source_kind="cloud_gap", connector_id=connector.id, target_ref="tenant",
        )
        job = await svc.execute_job(job.id, writer=w)
        assert job.status == "succeeded"
        assert len(state["policies"]) == 1
        assert state["policies"][0]["state"] == "enabledForReportingButNotEnforced"
        assert state["policies"][0]["grantControls"]["builtInControls"] == ["mfa"]


@pytest.mark.asyncio
async def test_m365_simulator_idempotent(db: AsyncSession) -> None:
    _, pid = await setup_test_project(db)
    project_uuid = uuid.UUID(pid)
    connector = await _connector(db, project_uuid, "microsoft_365")
    # Política ya presente con el estado deseado → SKIPPED_COMPLIANT.
    state = {
        "policies": [
            {
                "id": "pol-x",
                # FIX: displayName de la variante report-only (require_mfa_
                # conditional_access) ahora distinto del enforce para no cruzar
                # estados entre las dos acciones.
                "displayName": "FULKRO-Require-MFA-Report",
                "state": "enabledForReportingButNotEnforced",
            },
        ],
        "n": 1,
    }
    with respx.mock(assert_all_called=False) as router:
        _register_graph(router, state)
        w = Microsoft365RemediationWriter(
            {"tenant_id": "t", "client_id": "c", "client_secret": "s"},
        )
        svc = RemediationService(db)
        job = await svc.create_job(
            project_id=project_uuid, action_type="require_mfa_conditional_access",
            source_kind="cloud_gap", connector_id=connector.id, target_ref="tenant",
        )
        job = await svc.execute_job(job.id, writer=w)
        assert job.status == "skipped_compliant"
        assert len(state["policies"]) == 1  # no creó otra


# ── Azure (ARM · simulador) ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_azure_simulator_disable_public_blob(db: AsyncSession) -> None:
    _, pid = await setup_test_project(db)
    project_uuid = uuid.UUID(pid)
    connector = await _connector(db, project_uuid, "azure")
    state = {"properties": {"allowBlobPublicAccess": True}}
    with respx.mock(assert_all_called=False) as router:
        _register_arm(router, state)
        w = AzureRemediationWriter(
            {"tenant_id": "t", "client_id": "c", "client_secret": "s"},
        )
        svc = RemediationService(db)
        job = await svc.create_job(
            project_id=project_uuid, action_type="azure_storage_disable_public_blob",
            source_kind="cloud_gap", connector_id=connector.id,
            target_ref="/subscriptions/x/resourceGroups/y/providers/Microsoft.Storage/storageAccounts/z",
        )
        job = await svc.execute_job(job.id, writer=w)
        assert job.status == "succeeded"
        assert state["properties"]["allowBlobPublicAccess"] is False


# ── Google (Drive · simulador · GUARDED) ──────────────────────────────────────


@pytest.mark.asyncio
async def test_google_simulator_restrict_external_guarded(db: AsyncSession) -> None:
    _, pid = await setup_test_project(db)
    project_uuid = uuid.UUID(pid)
    connector = await _connector(db, project_uuid, "google_workspace")
    state = {"restrictions": {"domainUsersOnly": False}}
    with respx.mock(assert_all_called=False) as router:
        _register_drive(router, state)
        w = GoogleWorkspaceRemediationWriter(
            {"service_account_info": {"x": 1}, "admin_email": "admin@x.com"},
        )

        async def _tok():
            return "tok"

        w._get_token = _tok  # type: ignore[assignment]  # token via google-auth (no httpx)

        svc = RemediationService(db)
        job = await svc.create_job(
            project_id=project_uuid, action_type="google_drive_restrict_external",
            source_kind="cloud_gap", connector_id=connector.id, target_ref="d1",
        )
        assert job.status == "awaiting_authorization"  # GUARDED
        await svc.authorize_job(job.id, user_id=uuid.uuid4())
        job = await svc.get_job(job.id)
        job = await svc.execute_job(job.id, writer=w)
        assert job.status == "succeeded"
        assert state["restrictions"]["domainUsersOnly"] is True
