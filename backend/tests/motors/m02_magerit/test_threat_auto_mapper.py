"""Tests ThreatAutoMapper service (ADR-037 SAN-D MB-15.2)."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select, text

from backend.app.motors.m02_magerit.models import (
    MageritAnalysis,
    MageritThreatAssessment,
)
from backend.app.motors.m02_magerit.threat_auto_mapper import (
    ThreatAutoMapper,
)
from backend.tests.conftest import _admin_setup


async def _create_project_with_analysis(db, *, num_assets: int = 2):
    """Setup: client + project + magerit_analysis + N assets."""
    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    analysis_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"

    asset_ids = [uuid.uuid4() for _ in range(num_assets)]

    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO clients (id, nombre, cif, created_at) "
                "VALUES (:id, 'Test', :cif, now())"
            ),
            {"id": str(client_id), "cif": cif},
        )
        await db.execute(
            text(
                "INSERT INTO projects (id, client_id, nombre, "
                "categoria_objetivo, created_at) "
                "VALUES (:id, :cid, 'TestProj', 'MEDIA', now())"
            ),
            {"id": str(project_id), "cid": str(client_id)},
        )
        await db.execute(
            text(
                "INSERT INTO magerit_analysis (id, project_id, name, version, "
                "status, calculation_mode, methodology_version, created_at) "
                "VALUES (:id, :pid, 'Test', 1, 'draft', 'qualitative', "
                "'MAGERIT v3', now())"
            ),
            {"id": str(analysis_id), "pid": str(project_id)},
        )
        for i, aid in enumerate(asset_ids):
            await db.execute(
                text(
                    "INSERT INTO magerit_assets (id, analysis_id, code, name, "
                    "asset_type_code, created_at) "
                    "VALUES (:id, :anid, :code, :name, :type, now())"
                ),
                {
                    "id": str(aid),
                    "anid": str(analysis_id),
                    "code": f"A{i}",
                    "name": f"Asset {i}",
                    "type": "HW",
                },
            )

    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": str(project_id)},
    )
    await db.execute(
        text("SELECT set_config('app.current_client_id', :cid, true)"),
        {"cid": str(client_id)},
    )
    await db.flush()

    return project_id, analysis_id, asset_ids


@pytest.mark.asyncio
async def test_auto_map_creates_assessments_for_assets(db):
    """Auto-mapper crea N assessments per asset matching catalog threats."""
    project_id, analysis_id, asset_ids = await _create_project_with_analysis(
        db, num_assets=2,
    )

    service = ThreatAutoMapper(db)
    result = await service.auto_map_threats_for_project(
        project_id=project_id, analysis_id=analysis_id,
    )

    assert result["created"] > 0
    assert result["skipped"] == 0
    assert result["assets_processed"] == 2

    # Verify rows
    rows = (
        await db.execute(
            select(MageritThreatAssessment)
            .where(MageritThreatAssessment.analysis_id == analysis_id)
        )
    ).scalars().all()
    rows = list(rows)
    assert len(rows) == result["created"]


@pytest.mark.asyncio
async def test_auto_map_idempotent_skips_existing(db):
    """Re-execute auto-map · skip already created assessments."""
    project_id, analysis_id, _ = await _create_project_with_analysis(
        db, num_assets=1,
    )

    service = ThreatAutoMapper(db)
    first = await service.auto_map_threats_for_project(
        project_id=project_id, analysis_id=analysis_id,
    )
    second = await service.auto_map_threats_for_project(
        project_id=project_id, analysis_id=analysis_id,
    )

    assert first["created"] > 0
    assert second["created"] == 0
    assert second["skipped"] >= first["created"]


@pytest.mark.asyncio
async def test_auto_map_creates_lightweight_analysis_when_none(db):
    """Si no hay análisis existente · crea uno lightweight auto-generado."""
    # Setup project SIN análisis
    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO clients (id, nombre, cif, created_at) "
                "VALUES (:id, 'Test', :cif, now())"
            ),
            {"id": str(client_id), "cif": cif},
        )
        await db.execute(
            text(
                "INSERT INTO projects (id, client_id, nombre, created_at) "
                "VALUES (:id, :cid, 'P', now())"
            ),
            {"id": str(project_id), "cid": str(client_id)},
        )
    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": str(project_id)},
    )
    await db.execute(
        text("SELECT set_config('app.current_client_id', :cid, true)"),
        {"cid": str(client_id)},
    )
    await db.flush()

    service = ThreatAutoMapper(db)
    result = await service.auto_map_threats_for_project(project_id=project_id)

    # Sin assets · 0 assessments creadas pero análisis lightweight creado
    assert result["assets_processed"] == 0
    assert result["created"] == 0
    assert result["analysis_id"] is not None

    # Verify analysis exists
    analysis = await db.get(MageritAnalysis, result["analysis_id"])
    assert analysis is not None
    assert "auto-generado" in analysis.name.lower()


@pytest.mark.asyncio
async def test_auto_map_project_not_found(db):
    """Project_id inexistente · retorna error marker."""
    service = ThreatAutoMapper(db)
    result = await service.auto_map_threats_for_project(
        project_id=uuid.uuid4(),
    )
    assert result["error"] == "project_not_found"
    assert result["created"] == 0
