"""Tests m_cloud_connectors · RLS cross-project isolation (sub-atom 1.D.X.B v3.12).

Verifica policy ``cloud_connectors_project_isolation`` enforced bajo fulkro_app:
- project A NO ve conectores de project B (incluso si mismo client)
- Mismo provider distinto project NO viola UNIQUE (constraint scoped a project_id)
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from backend.app.motors.m_cloud_connectors import (
    CloudConnectorProvider,
    CloudConnectorService,
)
from backend.tests.conftest import setup_test_project


@pytest.mark.asyncio
async def test_same_provider_different_projects_no_conflict(db):
    """UNIQUE (project_id, provider) permite mismo provider en projects distintos."""
    _, project_a_str = await setup_test_project(db)
    _, project_b_str = await setup_test_project(db)
    pa = uuid.UUID(project_a_str)
    pb = uuid.UUID(project_b_str)

    svc = CloudConnectorService(db)

    # set context A
    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": str(pa)},
    )
    ca = await svc.link_or_create_connector(
        project_id=pa, provider=CloudConnectorProvider.GITHUB,
    )

    # set context B + crear mismo provider
    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": str(pb)},
    )
    cb = await svc.link_or_create_connector(
        project_id=pb, provider=CloudConnectorProvider.GITHUB,
    )

    assert ca.id != cb.id
    assert ca.project_id == pa
    assert cb.project_id == pb


@pytest.mark.asyncio
async def test_rls_blocks_cross_project_listing(db):
    """Con tenant context = project_a · listar NO devuelve conectores project_b."""
    _, project_a_str = await setup_test_project(db)
    _, project_b_str = await setup_test_project(db)
    pa = uuid.UUID(project_a_str)
    pb = uuid.UUID(project_b_str)

    svc = CloudConnectorService(db)

    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": str(pa)},
    )
    await svc.link_or_create_connector(
        project_id=pa, provider=CloudConnectorProvider.AWS,
    )

    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": str(pb)},
    )
    await svc.link_or_create_connector(
        project_id=pb, provider=CloudConnectorProvider.AZURE,
    )

    # Context A: SOLO debe ver AWS de A · NO AZURE de B
    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": str(pa)},
    )
    items_a = await svc.list_connectors(project_id=pa)
    providers_a = {i.provider for i in items_a}
    assert providers_a == {"aws"}

    # Context B: SOLO debe ver AZURE de B
    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": str(pb)},
    )
    items_b = await svc.list_connectors(project_id=pb)
    providers_b = {i.provider for i in items_b}
    assert providers_b == {"azure"}


@pytest.mark.asyncio
async def test_rls_cloud_resources_scoped_to_project(db):
    """Resources insertados en project_a NO visibles desde project_b."""
    _, project_a_str = await setup_test_project(db)
    _, project_b_str = await setup_test_project(db)
    pa = uuid.UUID(project_a_str)
    pb = uuid.UUID(project_b_str)

    svc = CloudConnectorService(db)

    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": str(pa)},
    )
    ca = await svc.link_or_create_connector(
        project_id=pa, provider=CloudConnectorProvider.MANUAL_IMPORT,
    )
    # Sync mock para crear sync_job en A (NO resources)
    await svc.trigger_sync(project_id=pa, connector_id=ca.id)

    # Context B: list_sync_jobs project_a debe fallar (connector no encontrado)
    from backend.app.motors.m_cloud_connectors import (
        CloudConnectorNotFoundError,
    )

    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": str(pb)},
    )
    with pytest.raises(CloudConnectorNotFoundError):
        await svc.list_sync_jobs(project_id=pb, connector_id=ca.id)
