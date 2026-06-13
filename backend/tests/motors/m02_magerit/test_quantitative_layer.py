"""Tests capa cuantitativa MAGERIT (ALE económico) · feat/fulkro-100 Ola D."""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import text

from backend.app.motors.m02_magerit.models import (
    MageritAnalysis,
    MageritAsset,
    MageritThreatAssessment,
)
from backend.app.motors.m02_magerit.quantitative_service import (
    QuantitativeError,
    compute_quantitative_risk,
    set_economic_value,
)


async def _set_rls(db, project_id: str) -> None:
    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": project_id},
    )


async def _make_analysis(db, project_id: str, name: str = "Análisis") -> MageritAnalysis:
    analysis = MageritAnalysis(project_id=uuid.UUID(project_id), name=name)
    db.add(analysis)
    await db.flush()
    return analysis


async def _make_asset(db, analysis_id, code="SRV-1") -> MageritAsset:
    asset = MageritAsset(
        analysis_id=analysis_id, code=code, name="Servidor BD",
        asset_type_code="HW",
    )
    db.add(asset)
    await db.flush()
    return asset


async def _make_threat(db, analysis_id, asset_id, probability, **degr) -> None:
    ta = MageritThreatAssessment(
        analysis_id=analysis_id, asset_id=asset_id,
        threat_code="E.1", probability=probability, **degr,
    )
    db.add(ta)
    await db.flush()


@pytest.mark.asyncio
async def test_ale_single_dimension(db):
    """SLE = VH×EF×(degr/100) · ARO(M)=1 · ALE = SLE×ARO."""
    from backend.tests.conftest import setup_test_project

    _, project_id = await setup_test_project(db)
    await _set_rls(db, project_id)
    analysis = await _make_analysis(db, project_id)
    asset = await _make_asset(db, analysis.id)
    await _make_threat(db, analysis.id, asset.id, "M", degradation_d=50)
    await set_economic_value(
        db, analysis_id=analysis.id, asset_id=asset.id,
        asset_value_eur=Decimal("100000"), exposure_factor=Decimal("1.0"),
    )
    await db.commit()

    report = await compute_quantitative_risk(db, analysis.id)
    assert report["has_quantitative_data"] is True
    # 100000 × 1.0 × 0.5 = 50000 ; ARO(M)=1 → 50000
    assert report["total_ale_annual"] == 50000.0
    assert report["by_dimension"]["D"] == 50000.0
    assert len(report["by_asset"]) == 1
    assert report["by_asset"][0]["total_ale"] == 50000.0


@pytest.mark.asyncio
async def test_ale_multi_dimension_and_aro(db):
    """ARO(A)=12 · 2 dimensiones suman."""
    from backend.tests.conftest import setup_test_project

    _, project_id = await setup_test_project(db)
    await _set_rls(db, project_id)
    analysis = await _make_analysis(db, project_id)
    asset = await _make_asset(db, analysis.id)
    await _make_threat(
        db, analysis.id, asset.id, "A", degradation_d=100, degradation_c=20,
    )
    await set_economic_value(
        db, analysis_id=analysis.id, asset_id=asset.id,
        asset_value_eur=Decimal("10000"), exposure_factor=Decimal("0.5"),
    )
    await db.commit()

    report = await compute_quantitative_risk(db, analysis.id)
    # SLE_d = 10000×0.5×1.0 = 5000 ; ALE_d = 5000×12 = 60000
    # SLE_c = 10000×0.5×0.2 = 1000 ; ALE_c = 1000×12 = 12000
    assert report["by_dimension"]["D"] == 60000.0
    assert report["by_dimension"]["C"] == 12000.0
    assert report["total_ale_annual"] == 72000.0


@pytest.mark.asyncio
async def test_backward_compat_no_economic(db):
    """Sin valor económico → has_quantitative_data False (solo cualitativo)."""
    from backend.tests.conftest import setup_test_project

    _, project_id = await setup_test_project(db)
    await _set_rls(db, project_id)
    analysis = await _make_analysis(db, project_id, name="Solo cualitativo")
    await db.commit()

    report = await compute_quantitative_risk(db, analysis.id)
    assert report["has_quantitative_data"] is False
    assert report["total_ale_annual"] == 0.0


@pytest.mark.asyncio
async def test_exposure_factor_out_of_range_raises(db):
    from backend.tests.conftest import setup_test_project

    _, project_id = await setup_test_project(db)
    await _set_rls(db, project_id)
    analysis = await _make_analysis(db, project_id)
    asset = await _make_asset(db, analysis.id)
    with pytest.raises(QuantitativeError):
        await set_economic_value(
            db, analysis_id=analysis.id, asset_id=asset.id,
            asset_value_eur=Decimal("1000"), exposure_factor=Decimal("1.5"),
        )


# ── API (require_owner) ──

pytestmark_api = pytest.mark.real_auth


@pytest.mark.real_auth
@pytest.mark.asyncio
async def test_report_requires_owner(async_client):
    res = await async_client.get(
        f"/api/v1/magerit/analysis/{uuid.uuid4()}/quantitative-report",
    )
    assert res.status_code in (401, 403), res.text


@pytest.mark.real_auth
@pytest.mark.asyncio
async def test_set_economic_values_endpoint(async_client, db):
    from backend.tests.conftest import setup_test_project

    _, project_id = await setup_test_project(db)
    await _set_rls(db, project_id)
    analysis = await _make_analysis(db, project_id)
    asset = await _make_asset(db, analysis.id)
    await _make_threat(db, analysis.id, asset.id, "M", degradation_d=50)
    await db.commit()

    res = await async_client.post("/api/v1/_dev/login-as-marcos")
    csrf = async_client.cookies.get("fulkro_csrf") or ""
    resp = await async_client.post(
        f"/api/v1/magerit/analysis/{analysis.id}/economic-values",
        json={"values": [{
            "asset_id": str(asset.id),
            "asset_value_eur": "100000",
            "exposure_factor": "1.0",
        }]},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["has_quantitative_data"] is True
    assert data["total_ale_annual"] == 50000.0
