"""Tests ISO 27001 → ENS coverage · SAN-C.MB-10.7."""
from __future__ import annotations

import os

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m21_diagnosis.iso27001_coverage import (
    calculate_iso27001_coverage,
)


@pytest.fixture(scope="module", autouse=True)
def _seed_iso_mapping_once():
    """Seed canonical CCN-STIC 825 mapping una vez para el módulo."""
    os.environ.setdefault(
        "DATABASE_URL_SYNC",
        "postgresql://fulkro_app:fulkro_app_dev_password@localhost:5433/fulkro",
    )
    from backend.scripts import seed_ens_iso27001_mapping

    seed_ens_iso27001_mapping.main()


@pytest.mark.asyncio
async def test_iso_coverage_empty_set_zero_coverage(db: AsyncSession):
    """Sin controles ISO implementados · cobertura = 0%."""
    result = await calculate_iso27001_coverage(db, [])
    assert result.coverage_percent == 0.0
    assert len(result.ens_measures_covered) == 0
    assert result.ens_measures_total > 0


@pytest.mark.asyncio
async def test_iso_coverage_single_control_covers_subset(db: AsyncSession):
    """Un control ISO típico cubre 1+ medidas ENS mapeadas."""
    result = await calculate_iso27001_coverage(db, ["A.5.1"])
    assert result.coverage_percent > 0.0
    assert "org.1" in result.ens_measures_covered


@pytest.mark.asyncio
async def test_iso_coverage_multiple_controls_aggregate(db: AsyncSession):
    """Múltiples controles ISO acumulan cobertura sin duplicar."""
    result = await calculate_iso27001_coverage(
        db,
        ["A.5.1", "A.5.2", "A.8.5", "A.5.16", "A.5.18", "A.7.1", "A.7.2"],
    )
    assert result.coverage_percent > 0.0
    # Los covered son únicos
    assert len(result.ens_measures_covered) == len(set(result.ens_measures_covered))


@pytest.mark.asyncio
async def test_iso_coverage_per_family_structure(db: AsyncSession):
    """coverage_per_family agrega per familia ENS."""
    result = await calculate_iso27001_coverage(db, ["A.5.1"])
    assert isinstance(result.coverage_per_family, dict)
    # Debe haber al menos la familia "org" presente
    assert any("org" in k for k in result.coverage_per_family)


@pytest.mark.asyncio
async def test_iso_coverage_effort_saved_proportional(db: AsyncSession):
    """effort_hours_saved_estimate proporcional a covered."""
    r1 = await calculate_iso27001_coverage(db, ["A.5.1"])
    r2 = await calculate_iso27001_coverage(
        db, ["A.5.1", "A.8.5", "A.5.16", "A.5.18"]
    )
    assert r2.effort_hours_saved_estimate >= r1.effort_hours_saved_estimate
