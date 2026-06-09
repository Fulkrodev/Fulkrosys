"""Tests m_cloud_connectors · sync orchestration + resource persistence.

Cubre:
- trigger_sync mock_mode (sin M16 credentials · job COMPLETED + 0 resources)
- trigger_sync con DiscoveryResult dummy persiste resources
- UPSERT idempotente resources (re-sync mismo external_id actualiza · NO duplica)
- list_resources filtros + paginación
- list_sync_jobs ordenado
- trigger_sync sobre revoked → CloudConnectorRevokedError
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import patch

import pytest

from backend.app.motors.m_cloud_connectors import (
    CloudConnectorProvider,
    CloudConnectorRevokedError,
    CloudConnectorService,
)
from backend.app.motors.m_cloud_connectors.base_connector import (
    DiscoveredAssetDTO,
    DiscoveredIdentityDTO,
    DiscoveryResult,
)
from backend.tests.conftest import setup_test_project


# ============================================================
# Mock mode (sub-fase B baseline · no requiere real OAuth)
# ============================================================


@pytest.mark.asyncio
async def test_trigger_sync_mock_mode_completes_zero_resources(db):
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)
    svc = CloudConnectorService(db)

    connector = await svc.link_or_create_connector(
        project_id=pid, provider=CloudConnectorProvider.MANUAL_IMPORT,
    )
    job = await svc.trigger_sync(
        project_id=pid, connector_id=connector.id,
    )

    assert job.status == "completed"
    assert job.resources_count == 0
    assert job.completed_at is not None


@pytest.mark.asyncio
async def test_trigger_sync_updates_connector_last_sync(db):
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)
    svc = CloudConnectorService(db)

    connector = await svc.link_or_create_connector(
        project_id=pid, provider=CloudConnectorProvider.MANUAL_IMPORT,
    )
    assert connector.last_sync_at is None

    await svc.trigger_sync(project_id=pid, connector_id=connector.id)

    refreshed = await svc.get_connector(
        project_id=pid, connector_id=connector.id,
    )
    assert refreshed.last_sync_at is not None
    assert refreshed.status == "connected"


@pytest.mark.asyncio
async def test_trigger_sync_on_revoked_raises(db):
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)
    svc = CloudConnectorService(db)

    c = await svc.link_or_create_connector(
        project_id=pid, provider=CloudConnectorProvider.MANUAL_IMPORT,
    )
    await svc.revoke_connector(project_id=pid, connector_id=c.id)

    with pytest.raises(CloudConnectorRevokedError):
        await svc.trigger_sync(project_id=pid, connector_id=c.id)


# ============================================================
# Real adapter flow (con DiscoveryResult mock injected)
# ============================================================


def _make_dummy_discovery_result() -> DiscoveryResult:
    return DiscoveryResult(
        provider="github",
        success=True,
        assets=[
            DiscoveredAssetDTO(
                external_id="repo_001",
                name="acme/website",
                asset_type="repo",
                provider="github",
                raw_data={"private": True, "default_branch": "main"},
            ),
            DiscoveredAssetDTO(
                external_id="repo_002",
                name="acme/internal-api",
                asset_type="repo",
                provider="github",
                raw_data={"private": True, "default_branch": "main"},
            ),
        ],
        identities=[
            DiscoveredIdentityDTO(
                external_id="user_001",
                email="alice@acme.io",
                display_name="Alice Admin",
                identity_type="user",
                provider="github",
                mfa_enabled=False,
                is_privileged=True,
            ),
        ],
        errors=[],
        duration_seconds=0.5,
    )


@pytest.mark.asyncio
async def test_trigger_sync_with_credentials_persists_resources(db):
    """Cuando m16_credentials provistas + adapter dummy → resources persistidos."""
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)
    svc = CloudConnectorService(db)

    connector = await svc.link_or_create_connector(
        project_id=pid, provider=CloudConnectorProvider.GITHUB,
    )

    # Patch del adapter M16 via registry para evitar HTTP real
    class _FakeAdapter:
        def __init__(self, credentials):
            self.credentials = credentials

        async def run_full_discovery(self):
            return _make_dummy_discovery_result()

    with patch(
        "backend.app.motors.m_cloud_connectors.service.get_m16_connector_class",
        return_value=_FakeAdapter,
    ):
        job = await svc.trigger_sync(
            project_id=pid,
            connector_id=connector.id,
            m16_credentials={"access_token": "dummy"},
        )

    assert job.status == "completed"
    assert job.resources_count == 3  # 2 repos + 1 identity

    resources, total = await svc.list_resources(
        project_id=pid, connector_id=connector.id,
    )
    assert total == 3
    types = {r.resource_type for r in resources}
    assert "asset.repo" in types
    assert "identity.user" in types


@pytest.mark.asyncio
async def test_sync_upsert_idempotent_no_duplicates(db):
    """Re-sync mismo (external_id, type) actualiza · NO crea duplicado."""
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)
    svc = CloudConnectorService(db)

    connector = await svc.link_or_create_connector(
        project_id=pid, provider=CloudConnectorProvider.GITHUB,
    )

    class _FakeAdapter:
        def __init__(self, credentials):
            pass

        async def run_full_discovery(self):
            return _make_dummy_discovery_result()

    with patch(
        "backend.app.motors.m_cloud_connectors.service.get_m16_connector_class",
        return_value=_FakeAdapter,
    ):
        await svc.trigger_sync(
            project_id=pid, connector_id=connector.id,
            m16_credentials={"access_token": "dummy"},
        )
        await svc.trigger_sync(
            project_id=pid, connector_id=connector.id,
            m16_credentials={"access_token": "dummy"},
        )

    _, total = await svc.list_resources(
        project_id=pid, connector_id=connector.id,
    )
    assert total == 3  # NO duplicados


@pytest.mark.asyncio
async def test_list_resources_filter_by_type(db):
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)
    svc = CloudConnectorService(db)
    connector = await svc.link_or_create_connector(
        project_id=pid, provider=CloudConnectorProvider.GITHUB,
    )

    class _FakeAdapter:
        def __init__(self, credentials): pass
        async def run_full_discovery(self):
            return _make_dummy_discovery_result()

    with patch(
        "backend.app.motors.m_cloud_connectors.service.get_m16_connector_class",
        return_value=_FakeAdapter,
    ):
        await svc.trigger_sync(
            project_id=pid, connector_id=connector.id,
            m16_credentials={"access_token": "dummy"},
        )

    repos, total_repos = await svc.list_resources(
        project_id=pid, connector_id=connector.id, resource_type="asset.repo",
    )
    assert total_repos == 2
    assert all(r.resource_type == "asset.repo" for r in repos)


@pytest.mark.asyncio
async def test_list_sync_jobs_ordered_desc(db):
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)
    svc = CloudConnectorService(db)
    connector = await svc.link_or_create_connector(
        project_id=pid, provider=CloudConnectorProvider.MANUAL_IMPORT,
    )

    j1 = await svc.trigger_sync(project_id=pid, connector_id=connector.id)
    j2 = await svc.trigger_sync(project_id=pid, connector_id=connector.id)
    j3 = await svc.trigger_sync(project_id=pid, connector_id=connector.id)

    jobs = await svc.list_sync_jobs(project_id=pid, connector_id=connector.id)
    assert len(jobs) >= 3
    # Más recientes primero
    assert jobs[0].started_at >= jobs[1].started_at >= jobs[2].started_at


# ============================================================
# #18 · Resolución de credenciales reales desde M16 ConnectorConfig
# ============================================================


@pytest.mark.asyncio
async def test_trigger_sync_resolves_credentials_from_m16_config(db):
    """#18 · connector enlazado a una M16 ConnectorConfig → trigger_sync SIN
    credenciales explícitas descifra el OAuth real y ejecuta discovery (no el
    mock de 0 recursos). Es el 'Hecho cuando' del punto: el cliente conecta su
    cloud y el sync descubre recursos reales."""
    from backend.app.models.onboarding import ConnectorConfig
    from backend.app.motors.m16_onboarding.token_encryption import (
        encrypt_credentials,
    )

    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)
    svc = CloudConnectorService(db)

    # M16 OAuth config con token cifrado real
    config = ConnectorConfig(
        project_id=pid,
        provider="github",
        encrypted_credentials=encrypt_credentials(
            {"access_token": "real-oauth-token"},
        ),
        status="validated",
    )
    db.add(config)
    await db.flush()

    connector = await svc.link_or_create_connector(
        project_id=pid, provider=CloudConnectorProvider.GITHUB,
    )
    connector.m16_connector_config_id = config.id
    await db.flush()

    captured: dict[str, Any] = {}

    class _FakeAdapter:
        def __init__(self, credentials):
            captured["creds"] = credentials

        async def run_full_discovery(self):
            return _make_dummy_discovery_result()

    # NO se pasan m16_credentials → deben resolverse desde la config enlazada
    with patch(
        "backend.app.motors.m_cloud_connectors.service.get_m16_connector_class",
        return_value=_FakeAdapter,
    ):
        job = await svc.trigger_sync(
            project_id=pid, connector_id=connector.id,
        )

    # Discovery real ejecutado (no mock 0)
    assert job.status == "completed"
    assert job.resources_count == 3  # 2 repos + 1 identity
    # Anti-falso-verde: el adapter recibió las credenciales DESCIFRADAS reales
    assert captured["creds"] == {"access_token": "real-oauth-token"}

    resources, total = await svc.list_resources(
        project_id=pid, connector_id=connector.id,
    )
    assert total == 3
