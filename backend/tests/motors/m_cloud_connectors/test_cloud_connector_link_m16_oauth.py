"""Tests m_cloud_connectors · link M16 ConnectorConfig OAuth (sub-atom 1.D.X.B v3.12).

Verifica el reuse no-duplicación de M16 OAuth (ADR-025 sostener firmísimo):
- Cuando se pasa m16_connector_config_id válido → status CONNECTED
- FK SET NULL si M16 config se borra (sin cascada destructiva)
- Re-link con M16 different id actualiza link
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from backend.app.motors.m_cloud_connectors import (
    CloudConnectorProvider,
    CloudConnectorService,
    CloudConnectorStatus,
)
from backend.tests.conftest import setup_test_project


async def _create_m16_connector_config(
    db, *, project_id: uuid.UUID, provider: str = "github",
) -> uuid.UUID:
    """Inserta ConnectorConfig dummy directamente · bypass OAuth flow para test."""
    config_id = uuid.uuid4()
    await db.execute(text(
        "INSERT INTO connector_configs "
        "(id, project_id, provider, encrypted_credentials, scopes, status) "
        "VALUES (:id, :pid, :prov, :creds, :scopes, 'configured')"
    ), {
        "id": str(config_id),
        "pid": str(project_id),
        "prov": provider,
        "creds": b"encrypted_dummy_bytes",
        "scopes": "test_scope",
    })
    await db.flush()
    return config_id


@pytest.mark.asyncio
async def test_link_with_m16_config_sets_connected_status(db):
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)

    m16_id = await _create_m16_connector_config(db, project_id=pid)

    svc = CloudConnectorService(db)
    connector = await svc.link_or_create_connector(
        project_id=pid,
        provider=CloudConnectorProvider.GITHUB,
        m16_connector_config_id=m16_id,
        scopes="repo,read:org",
    )

    assert connector.m16_connector_config_id == m16_id
    assert connector.status == CloudConnectorStatus.CONNECTED.value
    assert connector.scopes == "repo,read:org"


@pytest.mark.asyncio
async def test_relink_swap_m16_config_id_updates_link(db):
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)

    m16_a = await _create_m16_connector_config(db, project_id=pid)
    svc = CloudConnectorService(db)
    a = await svc.link_or_create_connector(
        project_id=pid,
        provider=CloudConnectorProvider.GITHUB,
        m16_connector_config_id=m16_a,
    )
    original_id = a.id

    # Borrar primer ConnectorConfig (simula re-oauth flow producing nuevo id)
    await db.execute(text(
        "DELETE FROM connector_configs WHERE id = :id"
    ), {"id": str(m16_a)})
    await db.flush()

    # FK ON DELETE SET NULL → connector.m16_connector_config_id pasa a NULL
    await db.refresh(a)
    assert a.m16_connector_config_id is None

    # Re-link con NUEVO m16 config (mismo provider · UPSERT mismo connector)
    m16_b = await _create_m16_connector_config(db, project_id=pid)
    b = await svc.link_or_create_connector(
        project_id=pid,
        provider=CloudConnectorProvider.GITHUB,
        m16_connector_config_id=m16_b,
    )

    assert b.id == original_id  # mismo connector (UPSERT)
    assert b.m16_connector_config_id == m16_b
    assert b.status == CloudConnectorStatus.CONNECTED.value


@pytest.mark.asyncio
async def test_unique_constraint_one_per_project_provider(db):
    """UNIQUE (project_id, provider) impide duplicados · UPSERT vía service."""
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)
    svc = CloudConnectorService(db)

    a = await svc.link_or_create_connector(
        project_id=pid, provider=CloudConnectorProvider.AWS,
    )
    b = await svc.link_or_create_connector(
        project_id=pid, provider=CloudConnectorProvider.AWS,
    )

    assert a.id == b.id
