"""Tests M22 Discovery consolidation · sub-fase 1.D.J.B.M22 v3.12.

Verifica integrations layer additive:
- consolidate_discovery_with_cloud() helper deterministic R1
- Match logic case-insensitive trim · provenance manual/cloud/both
- Counts buckets: manual_only · cloud_only · both · total

Pattern K-light ADDITIVE sostener: NO motor M22 source-code modification ·
ADR-025 + ADR-039 + OPS-045 32ª aplicación consecutiva.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from backend.app.motors.m_cloud_connectors import (
    CloudConnectorProvider,
    CloudConnectorService,
)
from backend.app.motors.m_cloud_connectors.integrations import (
    consolidate_discovery_with_cloud,
)
from backend.tests.conftest import setup_test_project


async def _seed_m22_manual_asset(
    db,
    *,
    project_id: uuid.UUID,
    name: str,
    tipo_magerit: str = "[HW]",
    criticidad: str = "MEDIO",
) -> uuid.UUID:
    """Insert minimal DiscoveredAsset record via raw SQL (avoid PKG dependency)."""
    asset_id = uuid.uuid4()
    await db.execute(
        text(
            "INSERT INTO discovered_assets "
            "(id, project_id, fuente_conector, tipo_magerit, nombre, "
            "criticidad_propuesta) "
            "VALUES (:id, :pid, 'manual_input', :tipo, :name, :crit)"
        ),
        {
            "id": str(asset_id),
            "pid": str(project_id),
            "tipo": tipo_magerit,
            "name": name,
            "crit": criticidad,
        },
    )
    await db.flush()
    return asset_id


async def _seed_cloud_resource(
    db,
    *,
    project_id: uuid.UUID,
    connector_id: uuid.UUID,
    resource_type: str,
    resource_name: str,
    resource_external_id: str | None = None,
    attributes: str = '{"verified": true}',
) -> uuid.UUID:
    """Insert minimal CloudResource record."""
    resource_id = uuid.uuid4()
    await db.execute(
        text(
            "INSERT INTO cloud_resources "
            "(id, project_id, connector_id, resource_type, "
            "resource_external_id, resource_name, attributes) "
            "VALUES (:id, :pid, :cid, :rtype, :ext, :name, CAST(:attrs AS JSONB))"
        ),
        {
            "id": str(resource_id),
            "pid": str(project_id),
            "cid": str(connector_id),
            "rtype": resource_type,
            "ext": resource_external_id or f"ext_{resource_id.hex[:8]}",
            "name": resource_name,
            "attrs": attributes,
        },
    )
    await db.flush()
    return resource_id


# ============================================================
# Scenario 1 · Empty project (no manual + no cloud)
# ============================================================


@pytest.mark.asyncio
async def test_consolidate_empty_project_returns_zero_counts(db):
    """Project sin DiscoveredAsset ni CloudResource · counts todos 0."""
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)

    view = await consolidate_discovery_with_cloud(db, project_id=pid)

    assert view.project_id == pid
    assert view.assets == []
    assert view.counts == {
        "manual_only": 0,
        "cloud_only": 0,
        "both": 0,
        "total": 0,
    }


# ============================================================
# Scenario 2 · Manual only (M22 assets sin cloud_connectors)
# ============================================================


@pytest.mark.asyncio
async def test_consolidate_manual_only_when_no_cloud_resources(db):
    """3 DiscoveredAsset + 0 CloudResource · provenance=manual para todos."""
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)
    await _seed_m22_manual_asset(db, project_id=pid, name="Servidor App Web")
    await _seed_m22_manual_asset(db, project_id=pid, name="Base Datos PG")
    await _seed_m22_manual_asset(db, project_id=pid, name="Bucket Backups")

    view = await consolidate_discovery_with_cloud(db, project_id=pid)

    assert view.counts["manual_only"] == 3
    assert view.counts["cloud_only"] == 0
    assert view.counts["both"] == 0
    assert view.counts["total"] == 3
    assert all(a.provenance == "manual" for a in view.assets)
    assert all(a.provider is None for a in view.assets)
    assert all(a.cloud_resource_id is None for a in view.assets)
    assert all(a.manual_asset_id is not None for a in view.assets)
    # Sort orden por normalized name
    names = [a.name for a in view.assets]
    assert "Servidor App Web" in names
    assert "Base Datos PG" in names


# ============================================================
# Scenario 3 · Cloud only (cloud_connectors sin M22 manual)
# ============================================================


@pytest.mark.asyncio
async def test_consolidate_cloud_only_when_no_m22_assets(db):
    """0 DiscoveredAsset + 2 CloudResource · provenance=cloud para todos."""
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)
    svc = CloudConnectorService(db)
    connector = await svc.link_or_create_connector(
        project_id=pid, provider=CloudConnectorProvider.AWS,
    )
    await _seed_cloud_resource(
        db, project_id=pid, connector_id=connector.id,
        resource_type="asset.bucket", resource_name="prod-data-2026",
    )
    await _seed_cloud_resource(
        db, project_id=pid, connector_id=connector.id,
        resource_type="asset.vm", resource_name="app-server-eu-west",
    )

    view = await consolidate_discovery_with_cloud(db, project_id=pid)

    assert view.counts["manual_only"] == 0
    assert view.counts["cloud_only"] == 2
    assert view.counts["both"] == 0
    assert view.counts["total"] == 2
    assert all(a.provenance == "cloud" for a in view.assets)
    assert all(a.provider == "aws" for a in view.assets)
    assert all(a.cloud_resource_id is not None for a in view.assets)
    assert all(a.manual_asset_id is None for a in view.assets)
    assert all(a.cloud_attributes is not None for a in view.assets)


# ============================================================
# Scenario 4 · Match both manual + cloud
# ============================================================


@pytest.mark.asyncio
async def test_consolidate_both_when_name_match_case_insensitive(db):
    """Manual + cloud con mismo nombre normalizado · provenance=both."""
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)
    svc = CloudConnectorService(db)
    connector = await svc.link_or_create_connector(
        project_id=pid, provider=CloudConnectorProvider.MICROSOFT_365,
    )
    # Manual M22 con name "Servidor App Web"
    await _seed_m22_manual_asset(
        db, project_id=pid, name="Servidor App Web", criticidad="ALTO",
    )
    # Cloud con name "SERVIDOR APP WEB" (case mismatch · match esperado)
    await _seed_cloud_resource(
        db, project_id=pid, connector_id=connector.id,
        resource_type="asset.vm", resource_name="SERVIDOR APP WEB",
        attributes='{"region": "eu-west-1", "verified": true}',
    )
    # Manual only "Base Datos PG"
    await _seed_m22_manual_asset(db, project_id=pid, name="Base Datos PG")
    # Cloud only "prod-bucket"
    await _seed_cloud_resource(
        db, project_id=pid, connector_id=connector.id,
        resource_type="asset.bucket", resource_name="prod-bucket",
    )

    view = await consolidate_discovery_with_cloud(db, project_id=pid)

    assert view.counts["both"] == 1
    assert view.counts["manual_only"] == 1
    assert view.counts["cloud_only"] == 1
    assert view.counts["total"] == 3

    # Asset both verify
    both_assets = [a for a in view.assets if a.provenance == "both"]
    assert len(both_assets) == 1
    both = both_assets[0]
    assert both.criticidad == "ALTO"  # preserved from manual
    assert both.provider == "microsoft_365"
    assert both.manual_asset_id is not None
    assert both.cloud_resource_id is not None
    assert both.cloud_attributes == {"region": "eu-west-1", "verified": True}

    # Asset manual_only verify
    manual_only = [a for a in view.assets if a.provenance == "manual"]
    assert len(manual_only) == 1
    assert manual_only[0].name == "Base Datos PG"
    assert manual_only[0].provider is None

    # Asset cloud_only verify
    cloud_only = [a for a in view.assets if a.provenance == "cloud"]
    assert len(cloud_only) == 1
    assert cloud_only[0].name == "prod-bucket"
    assert cloud_only[0].provider == "microsoft_365"
