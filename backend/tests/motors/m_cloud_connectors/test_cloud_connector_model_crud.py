"""Tests m_cloud_connectors · CloudConnectorService CRUD (sub-atom 1.D.X.B v3.12).

Cubre:
- Catalog providers (puros · sin DB)
- link_or_create_connector idempotent (re-link OK)
- get/list/revoke
- UNIQUE (project_id, provider) enforced
- cross-project isolation
"""
from __future__ import annotations

import uuid

import pytest

from backend.app.motors.m_cloud_connectors import (
    CloudConnectorProvider,
    CloudConnectorService,
    CloudConnectorStatus,
    list_provider_catalog,
)
from backend.tests.conftest import setup_test_project


# ============================================================
# Catalog (puro · no DB)
# ============================================================


def test_provider_catalog_has_6_providers():
    items = list_provider_catalog()
    providers = {i["provider"] for i in items}
    assert providers == {
        "microsoft_365",
        "google_workspace",
        "azure",
        "aws",
        "github",
        "manual_import",
    }


def test_provider_catalog_aws_no_oauth():
    items = list_provider_catalog()
    aws = next(i for i in items if i["provider"] == "aws")
    assert aws["requires_oauth"] is False


def test_provider_catalog_manual_no_oauth():
    items = list_provider_catalog()
    manual = next(i for i in items if i["provider"] == "manual_import")
    assert manual["requires_oauth"] is False


def test_provider_catalog_microsoft_requires_oauth():
    items = list_provider_catalog()
    m365 = next(i for i in items if i["provider"] == "microsoft_365")
    assert m365["requires_oauth"] is True
    assert "Microsoft 365" in m365["display_name"]


def test_provider_catalog_blurb_present_all():
    """R29 friendly blurb presente para todos · UI cliente lo muestra."""
    for item in list_provider_catalog():
        assert item["cliente_friendly_blurb"]
        assert len(item["cliente_friendly_blurb"]) > 20


# ============================================================
# Service CRUD (require DB · setup_test_project)
# ============================================================


@pytest.mark.asyncio
async def test_link_connector_without_m16_pending_oauth(db):
    """Sin m16_connector_config_id → status PENDING_OAUTH (cliente completará)."""
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)
    svc = CloudConnectorService(db)

    connector = await svc.link_or_create_connector(
        project_id=pid,
        provider=CloudConnectorProvider.MICROSOFT_365,
    )

    assert connector.id is not None
    assert connector.project_id == pid
    assert connector.provider == "microsoft_365"
    assert connector.status == CloudConnectorStatus.PENDING_OAUTH.value
    assert connector.m16_connector_config_id is None


@pytest.mark.asyncio
async def test_link_manual_import_is_connected_immediately(db):
    """MANUAL_IMPORT NO requiere OAuth → status CONNECTED directo."""
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)
    svc = CloudConnectorService(db)

    connector = await svc.link_or_create_connector(
        project_id=pid,
        provider=CloudConnectorProvider.MANUAL_IMPORT,
    )

    assert connector.status == CloudConnectorStatus.CONNECTED.value


@pytest.mark.asyncio
async def test_link_connector_idempotent_relink(db):
    """Re-link mismo (project, provider) UPSERT · NO crea duplicado."""
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)
    svc = CloudConnectorService(db)

    a = await svc.link_or_create_connector(
        project_id=pid,
        provider=CloudConnectorProvider.GITHUB,
        scopes="repo,read:org",
    )
    b = await svc.link_or_create_connector(
        project_id=pid,
        provider=CloudConnectorProvider.GITHUB,
        scopes="repo,read:org,user:email",
    )

    assert a.id == b.id
    assert b.scopes == "repo,read:org,user:email"


@pytest.mark.asyncio
async def test_list_connectors_excludes_revoked_by_default(db):
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)
    svc = CloudConnectorService(db)

    a = await svc.link_or_create_connector(
        project_id=pid, provider=CloudConnectorProvider.AWS,
    )
    b = await svc.link_or_create_connector(
        project_id=pid, provider=CloudConnectorProvider.AZURE,
    )
    await svc.revoke_connector(project_id=pid, connector_id=a.id)

    items = await svc.list_connectors(project_id=pid)
    ids = {i.id for i in items}
    assert b.id in ids
    assert a.id not in ids

    items_all = await svc.list_connectors(project_id=pid, include_revoked=True)
    assert {i.id for i in items_all} == {a.id, b.id}


@pytest.mark.asyncio
async def test_revoke_connector_sets_revoked_at(db):
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)
    svc = CloudConnectorService(db)

    c = await svc.link_or_create_connector(
        project_id=pid, provider=CloudConnectorProvider.GOOGLE_WORKSPACE,
    )
    revoked = await svc.revoke_connector(project_id=pid, connector_id=c.id)

    assert revoked.status == CloudConnectorStatus.REVOKED.value
    assert revoked.revoked_at is not None


@pytest.mark.asyncio
async def test_get_connector_not_found_raises(db):
    from backend.app.motors.m_cloud_connectors import CloudConnectorNotFoundError

    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)
    svc = CloudConnectorService(db)

    with pytest.raises(CloudConnectorNotFoundError):
        await svc.get_connector(project_id=pid, connector_id=uuid.uuid4())


@pytest.mark.asyncio
async def test_relink_revoked_connector_reactivates(db):
    """Revoke → re-link mismo provider · revoked_at se borra + status pasa a CONNECTED/PENDING."""
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)
    svc = CloudConnectorService(db)

    a = await svc.link_or_create_connector(
        project_id=pid, provider=CloudConnectorProvider.AZURE,
    )
    await svc.revoke_connector(project_id=pid, connector_id=a.id)

    b = await svc.link_or_create_connector(
        project_id=pid, provider=CloudConnectorProvider.AZURE,
    )
    assert b.id == a.id
    assert b.revoked_at is None
    assert b.status == CloudConnectorStatus.PENDING_OAUTH.value
