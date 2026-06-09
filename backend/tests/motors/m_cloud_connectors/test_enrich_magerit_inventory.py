"""Tests M02 MAGERIT asset inventory cloud enrichment · sub-fase 1.D.J.B.M02.

Verifica integrations layer additive:
- enrich_asset_inventory_with_cloud() helper deterministic R1
- Match logic case-insensitive trim (consistente con M22 consolidation)
- Counts buckets: total · cloud_verified · manual_only

Pattern K-light ADDITIVE sostener: NO motor M02 source-code modification ·
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
    enrich_asset_inventory_with_cloud,
)
from backend.tests.conftest import setup_test_project


async def _create_magerit_analysis(
    db,
    *,
    project_id: uuid.UUID,
    name: str = "Test MAGERIT",
) -> uuid.UUID:
    """Insert minimal MageritAnalysis row · returns analysis_id."""
    analysis_id = uuid.uuid4()
    await db.execute(
        text(
            "INSERT INTO magerit_analysis (id, project_id, name, version, "
            "status, calculation_mode, methodology_version, created_at) "
            "VALUES (:id, :pid, :name, 1, 'draft', 'qualitative', "
            "'MAGERIT v3', now())"
        ),
        {"id": str(analysis_id), "pid": str(project_id), "name": name},
    )
    await db.flush()
    return analysis_id


async def _seed_magerit_asset(
    db,
    *,
    analysis_id: uuid.UUID,
    code: str,
    name: str,
    asset_type_code: str = "HW",
    value_d: int | None = 7,
) -> uuid.UUID:
    """Insert minimal MageritAsset row · returns asset_id."""
    asset_id = uuid.uuid4()
    await db.execute(
        text(
            "INSERT INTO magerit_assets "
            "(id, analysis_id, code, name, asset_type_code, value_d, created_at) "
            "VALUES (:id, :anid, :code, :name, :type, :vd, now())"
        ),
        {
            "id": str(asset_id),
            "anid": str(analysis_id),
            "code": code,
            "name": name,
            "type": asset_type_code,
            "vd": value_d,
        },
    )
    await db.flush()
    return asset_id


async def _seed_cloud_resource(
    db,
    *,
    project_id: uuid.UUID,
    connector_id: uuid.UUID,
    resource_name: str,
    resource_type: str = "asset.vm",
    attributes: str = '{"verified": true, "region": "eu-west-1"}',
) -> uuid.UUID:
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
            "ext": f"ext_{resource_id.hex[:8]}",
            "name": resource_name,
            "attrs": attributes,
        },
    )
    await db.flush()
    return resource_id


# ============================================================
# Scenario 1 · Project sin cloud connectors · all manual_only
# ============================================================


@pytest.mark.asyncio
async def test_enrich_without_cloud_returns_all_manual_only(db):
    """3 MAGERIT assets + 0 CloudResource · cloud_verified=False para todos."""
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)
    analysis_id = await _create_magerit_analysis(db, project_id=pid)
    await _seed_magerit_asset(db, analysis_id=analysis_id, code="A1", name="Server App Web")
    await _seed_magerit_asset(db, analysis_id=analysis_id, code="A2", name="DB PG")
    await _seed_magerit_asset(db, analysis_id=analysis_id, code="A3", name="Bucket Backups")

    view = await enrich_asset_inventory_with_cloud(db, project_id=pid)

    assert view.project_id == pid
    assert view.counts["total"] == 3
    assert view.counts["cloud_verified"] == 0
    assert view.counts["manual_only"] == 3
    assert all(a.cloud_verified is False for a in view.assets)
    assert all(a.cloud_provider is None for a in view.assets)
    assert all(a.cloud_resource_id is None for a in view.assets)
    # Preserve manual asset data (code · name · value_d)
    codes = sorted(a.code for a in view.assets)
    assert codes == ["A1", "A2", "A3"]
    assert all(a.value_d == 7 for a in view.assets)


# ============================================================
# Scenario 2 · Match cloud-verified case-insensitive trim
# ============================================================


@pytest.mark.asyncio
async def test_enrich_marks_cloud_verified_when_name_matches_case_insensitive(db):
    """MAGERIT asset 'Server App Web' + cloud 'SERVER APP WEB' → cloud_verified=True."""
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)
    analysis_id = await _create_magerit_analysis(db, project_id=pid)

    svc = CloudConnectorService(db)
    connector = await svc.link_or_create_connector(
        project_id=pid, provider=CloudConnectorProvider.MICROSOFT_365,
    )

    # MAGERIT asset · name "Server App Web"
    await _seed_magerit_asset(
        db, analysis_id=analysis_id, code="A1", name="Server App Web",
    )
    # Cloud resource · name "SERVER APP WEB" (case mismatch · match esperado)
    await _seed_cloud_resource(
        db, project_id=pid, connector_id=connector.id,
        resource_name="SERVER APP WEB",
        attributes='{"region": "eu-west-1", "verified": true}',
    )
    # MAGERIT-only asset (sin match cloud)
    await _seed_magerit_asset(
        db, analysis_id=analysis_id, code="A2", name="DB PG",
    )
    # Cloud-only resource (sin match MAGERIT) · NO cuenta in M02 view
    await _seed_cloud_resource(
        db, project_id=pid, connector_id=connector.id,
        resource_name="orphan-cloud-bucket",
    )

    view = await enrich_asset_inventory_with_cloud(db, project_id=pid)

    assert view.counts["total"] == 2  # solo MAGERIT assets · NO cloud-only
    assert view.counts["cloud_verified"] == 1
    assert view.counts["manual_only"] == 1

    verified = [a for a in view.assets if a.cloud_verified]
    assert len(verified) == 1
    v = verified[0]
    assert v.name == "Server App Web"  # preserves MAGERIT name
    assert v.cloud_provider == "microsoft_365"
    assert v.cloud_resource_id is not None
    assert v.cloud_attributes == {"region": "eu-west-1", "verified": True}

    manual = [a for a in view.assets if not a.cloud_verified]
    assert len(manual) == 1
    assert manual[0].name == "DB PG"
    assert manual[0].cloud_resource_id is None


# ============================================================
# Scenario 3 · analysis_id filter constrains scope
# ============================================================


@pytest.mark.asyncio
async def test_enrich_filters_by_analysis_id_when_provided(db):
    """analysis_id query param restringe assets a 1 análisis específico."""
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)
    analysis_a = await _create_magerit_analysis(
        db, project_id=pid, name="Analysis A",
    )
    analysis_b = await _create_magerit_analysis(
        db, project_id=pid, name="Analysis B",
    )
    await _seed_magerit_asset(db, analysis_id=analysis_a, code="A1", name="Asset A1")
    await _seed_magerit_asset(db, analysis_id=analysis_a, code="A2", name="Asset A2")
    await _seed_magerit_asset(db, analysis_id=analysis_b, code="B1", name="Asset B1")

    # Without filter · all 3 assets
    view_all = await enrich_asset_inventory_with_cloud(db, project_id=pid)
    assert view_all.counts["total"] == 3

    # With filter analysis_a · only 2 assets
    view_a = await enrich_asset_inventory_with_cloud(
        db, project_id=pid, analysis_id=analysis_a,
    )
    assert view_a.counts["total"] == 2
    codes = sorted(a.code for a in view_a.assets)
    assert codes == ["A1", "A2"]

    # With filter analysis_b · only 1 asset
    view_b = await enrich_asset_inventory_with_cloud(
        db, project_id=pid, analysis_id=analysis_b,
    )
    assert view_b.counts["total"] == 1
    assert view_b.assets[0].code == "B1"
