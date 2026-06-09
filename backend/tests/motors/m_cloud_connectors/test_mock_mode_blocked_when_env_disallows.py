"""Tests · production-safety guard mock_mode requires CLOUD_MOCK_MODE_ALLOWED env.

Sub-atom 1.D.X.VERIFY commit 1 · blindaje production-safety.

Verifica:
- trigger_sync con m16_credentials=None + OAuth provider + env=False → raise
  MockModeNotAllowedError (NO crea CloudSyncJob · raise antes touch DB)
- trigger_sync con m16_credentials=None + OAuth provider + env=True → OK
- trigger_sync con MANUAL_IMPORT + m16_credentials=None + env=False → OK
  (MANUAL_IMPORT exento · diseñado para upload manual sin OAuth)
- trigger_sync con m16_credentials provistas → guard NO aplica (cualquier env)
"""
from __future__ import annotations

import uuid

import pytest

from backend.app.config import get_settings
from backend.app.motors.m_cloud_connectors import (
    CloudConnectorProvider,
    CloudConnectorService,
    MockModeNotAllowedError,
)
from backend.tests.conftest import setup_test_project


# ============================================================
# Guard ACTIVE (env=False default · production-safe)
# ============================================================


@pytest.mark.asyncio
async def test_raises_mock_mode_not_allowed_when_env_disallows(
    db, monkeypatch,
):
    """env=False + OAuth provider + sin credenciales → MockModeNotAllowedError."""
    monkeypatch.setattr(
        get_settings(), "cloud_mock_mode_allowed", False,
    )
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)
    svc = CloudConnectorService(db)

    connector = await svc.link_or_create_connector(
        project_id=pid, provider=CloudConnectorProvider.MICROSOFT_365,
    )

    with pytest.raises(MockModeNotAllowedError) as exc_info:
        await svc.trigger_sync(
            project_id=pid, connector_id=connector.id,
            m16_credentials=None,
        )

    assert "CLOUD_MOCK_MODE_ALLOWED" in str(exc_info.value)
    assert "NEVER enable in production" in str(exc_info.value)


@pytest.mark.asyncio
async def test_raises_mock_mode_for_aws_provider_when_env_disallows(
    db, monkeypatch,
):
    """AWS provider (NO MANUAL_IMPORT) también está sujeto al guard."""
    monkeypatch.setattr(
        get_settings(), "cloud_mock_mode_allowed", False,
    )
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)
    svc = CloudConnectorService(db)

    connector = await svc.link_or_create_connector(
        project_id=pid, provider=CloudConnectorProvider.AWS,
    )

    with pytest.raises(MockModeNotAllowedError):
        await svc.trigger_sync(
            project_id=pid, connector_id=connector.id,
            m16_credentials=None,
        )


@pytest.mark.asyncio
async def test_no_cloud_sync_job_created_when_guard_blocks(
    db, monkeypatch,
):
    """Guard raise debe ocurrir ANTES de crear CloudSyncJob (NO touch DB)."""
    from sqlalchemy import select
    from backend.app.motors.m_cloud_connectors.models import CloudSyncJob

    monkeypatch.setattr(
        get_settings(), "cloud_mock_mode_allowed", False,
    )
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)
    svc = CloudConnectorService(db)

    connector = await svc.link_or_create_connector(
        project_id=pid, provider=CloudConnectorProvider.GITHUB,
    )

    with pytest.raises(MockModeNotAllowedError):
        await svc.trigger_sync(
            project_id=pid, connector_id=connector.id,
            m16_credentials=None,
        )

    # Verify 0 sync jobs creados para este connector
    res = await db.execute(
        select(CloudSyncJob).where(
            CloudSyncJob.connector_id == connector.id,
        )
    )
    jobs = list(res.scalars().all())
    assert len(jobs) == 0


# ============================================================
# Guard NOT applicable (uso legítimo · NO raise)
# ============================================================


@pytest.mark.asyncio
async def test_allowed_when_env_true(db, monkeypatch):
    """env=True → mock_mode permitido (dev/test/piloto demo)."""
    monkeypatch.setattr(
        get_settings(), "cloud_mock_mode_allowed", True,
    )
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)
    svc = CloudConnectorService(db)

    connector = await svc.link_or_create_connector(
        project_id=pid, provider=CloudConnectorProvider.MICROSOFT_365,
    )

    # NO debe raise · sync completa en mock mode (0 resources)
    job = await svc.trigger_sync(
        project_id=pid, connector_id=connector.id,
        m16_credentials=None,
    )
    assert job.status == "completed"
    assert job.resources_count == 0


@pytest.mark.asyncio
async def test_manual_import_exempt_from_guard_when_env_false(
    db, monkeypatch,
):
    """MANUAL_IMPORT exento del guard · uso legítimo sin credenciales."""
    monkeypatch.setattr(
        get_settings(), "cloud_mock_mode_allowed", False,
    )
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)
    svc = CloudConnectorService(db)

    connector = await svc.link_or_create_connector(
        project_id=pid, provider=CloudConnectorProvider.MANUAL_IMPORT,
    )

    # NO debe raise · MANUAL_IMPORT diseñado para upload Excel/CSV
    # via m24_idms · sin OAuth credentials por diseño.
    job = await svc.trigger_sync(
        project_id=pid, connector_id=connector.id,
        m16_credentials=None,
    )
    assert job.status == "completed"


@pytest.mark.asyncio
async def test_no_guard_when_credentials_provided(db, monkeypatch):
    """m16_credentials presentes → guard NO aplica (real sync · cualquier env)."""
    from unittest.mock import patch

    from backend.app.motors.m_cloud_connectors.base_connector import (
        DiscoveryResult,
    )

    monkeypatch.setattr(
        get_settings(), "cloud_mock_mode_allowed", False,
    )
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)
    svc = CloudConnectorService(db)

    connector = await svc.link_or_create_connector(
        project_id=pid, provider=CloudConnectorProvider.GITHUB,
    )

    class _FakeAdapter:
        def __init__(self, credentials): pass
        async def run_full_discovery(self):
            return DiscoveryResult(
                provider="github", success=True, assets=[], identities=[],
                errors=[], duration_seconds=0.0,
            )

    with patch(
        "backend.app.motors.m_cloud_connectors.service.get_m16_connector_class",
        return_value=_FakeAdapter,
    ):
        # NO raise · credentials presentes · real sync path
        job = await svc.trigger_sync(
            project_id=pid, connector_id=connector.id,
            m16_credentials={"access_token": "real_token"},
        )
    assert job.status == "completed"


# ============================================================
# Default safety verification
# ============================================================


def test_default_settings_disallow_mock_mode():
    """Sanity: default Settings field es False · production-safe out of box."""
    from backend.app.config import Settings

    s = Settings()
    assert s.cloud_mock_mode_allowed is False, (
        "Default cloud_mock_mode_allowed DEBE ser False · production-safe"
    )
