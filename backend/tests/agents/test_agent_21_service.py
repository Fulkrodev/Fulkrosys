"""Tests A21 DiscrepancyDetectorService (MB-8.A.2).

Cobertura:
- scan_project con proyecto vacío completa sin discrepancias
- scan_project con riesgos críticos pero 0 DdA aplicables → discrepancia critical
- list_scan_runs limit + order
- list_discrepancies filtrado por status/severity
- resolve_discrepancy workflow
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from backend.app.agents.agent_21_service import DiscrepancyDetectorService
from backend.app.models.a21_discrepancies import A21Discrepancy
from backend.tests.conftest import _admin_setup, setup_test_project


@pytest.mark.asyncio
async def test_scan_project_empty_completes_no_discrepancies(db):
    """Proyecto sin riesgos ni DdA · scan completa con 0 discrepancias."""
    _, project_id = await setup_test_project(db)
    pid = uuid.UUID(project_id)

    svc = DiscrepancyDetectorService()
    run = await svc.scan_project(db, pid)

    assert run.run_status == "completed"
    assert run.discrepancies_found == 0
    assert run.completed_at is not None
    assert "m02" in run.motors_scanned
    assert "m03" in run.motors_scanned


@pytest.mark.asyncio
async def test_scan_detects_magerit_critical_without_dda(db):
    """Proyecto con riesgos críticos MAGERIT y 0 DdA aplicables · NC critical."""
    _, project_id = await setup_test_project(db)
    pid = uuid.UUID(project_id)

    # Insertar magerit_analysis + 1 magerit_asset + 1 magerit_risk_calculation
    # con risk_level=MC vía admin role (RLS bypass)
    async with _admin_setup(db):
        analysis_id = uuid.uuid4()
        asset_id = uuid.uuid4()
        await db.execute(text(
            "INSERT INTO magerit_analysis (id, project_id, name, version, "
            "status, methodology_version, calculation_mode, created_at) "
            "VALUES (:aid, :pid, 'Test', 1, 'draft', 'v3.0', "
            "'qualitative', now())",
        ), {"aid": str(analysis_id), "pid": str(pid)})
        await db.execute(text(
            "INSERT INTO magerit_assets (id, analysis_id, code, name, "
            "asset_type_code, created_at) "
            "VALUES (:aid, :anid, 'A001', 'Test asset', 'SW', now())",
        ), {"aid": str(asset_id), "anid": str(analysis_id)})
        await db.execute(text(
            "INSERT INTO magerit_risk_calculation (analysis_id, asset_id, "
            "threat_code, dimension, risk_level) "
            "VALUES (:anid, :aid, 'A.5', 'D', 'MC')",
        ), {"anid": str(analysis_id), "aid": str(asset_id)})

    svc = DiscrepancyDetectorService()
    run = await svc.scan_project(db, pid)

    assert run.run_status == "completed"
    assert run.discrepancies_found >= 1

    discrepancies = await svc.list_discrepancies(db, pid)
    types = {d.discrepancy_type for d in discrepancies}
    assert "magerit_vs_dda" in types
    critical = [d for d in discrepancies if d.severity == "critical"]
    assert len(critical) >= 1


@pytest.mark.asyncio
async def test_resolve_discrepancy_workflow(db):
    """Discrepancia open → acknowledged → resolved."""
    _, project_id = await setup_test_project(db)
    pid = uuid.UUID(project_id)

    svc = DiscrepancyDetectorService()
    run = await svc.scan_project(db, pid)

    # Crear discrepancia manualmente para test workflow
    disc = A21Discrepancy(
        scan_run_id=run.id,
        project_id=pid,
        discrepancy_type="magerit_vs_dda",
        severity="medium",
        motor_a="m02",
        motor_b="m03",
        description="Test discrepancy for workflow",
    )
    db.add(disc)
    await db.flush()

    # Acknowledge
    updated = await svc.resolve_discrepancy(
        db, pid, disc.id,
        new_status="acknowledged",
        notes="Marcos vio · revisamos próxima reunión",
    )
    assert updated.resolution_status == "acknowledged"
    assert updated.resolved_at is None
    assert "Marcos" in (updated.resolution_notes or "")

    # Resolve
    updated = await svc.resolve_discrepancy(
        db, pid, disc.id,
        new_status="resolved",
        notes="Solucionado tras meeting",
    )
    assert updated.resolution_status == "resolved"
    assert updated.resolved_at is not None


@pytest.mark.asyncio
async def test_list_discrepancies_filter_by_severity(db):
    """list_discrepancies aplica filtro severity correctamente."""
    _, project_id = await setup_test_project(db)
    pid = uuid.UUID(project_id)

    svc = DiscrepancyDetectorService()
    run = await svc.scan_project(db, pid)

    # Crear 3 discrepancias con distintas severidades
    for sev in ("critical", "high", "medium"):
        db.add(A21Discrepancy(
            scan_run_id=run.id,
            project_id=pid,
            discrepancy_type="magerit_vs_dda",
            severity=sev,
            motor_a="m02",
            motor_b="m03",
            description=f"Test {sev}",
        ))
    await db.flush()

    high_only = await svc.list_discrepancies(db, pid, severity="high")
    assert all(d.severity == "high" for d in high_only)
    assert len(high_only) >= 1

    open_only = await svc.list_discrepancies(db, pid, resolution_status="open")
    assert all(d.resolution_status == "open" for d in open_only)


@pytest.mark.asyncio
async def test_resolve_discrepancy_invalid_status_raises(db):
    """new_status fuera del enum levanta ValueError."""
    _, project_id = await setup_test_project(db)
    pid = uuid.UUID(project_id)

    svc = DiscrepancyDetectorService()
    run = await svc.scan_project(db, pid)
    disc = A21Discrepancy(
        scan_run_id=run.id,
        project_id=pid,
        discrepancy_type="magerit_vs_dda",
        severity="low",
        motor_a="m02",
        motor_b="m03",
        description="x",
    )
    db.add(disc)
    await db.flush()

    with pytest.raises(ValueError):
        await svc.resolve_discrepancy(
            db, pid, disc.id, new_status="invalid_status",
        )


# ════════════════════════════════════════════════════════════════════
# 1.D.A v3.10 · Detectores diferidos ENS-only (sostiene R1 inviolable)
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_detect_magerit_vs_findings_critical_without_tracking(db):
    """Riesgos críticos MAGERIT con 0 findings → NC tracking remediación."""
    _, project_id = await setup_test_project(db)
    pid = uuid.UUID(project_id)

    async with _admin_setup(db):
        analysis_id = uuid.uuid4()
        asset_id = uuid.uuid4()
        await db.execute(text(
            "INSERT INTO magerit_analysis (id, project_id, name, version, "
            "status, methodology_version, calculation_mode, created_at) "
            "VALUES (:aid, :pid, 'Test', 1, 'draft', 'v3.0', "
            "'qualitative', now())",
        ), {"aid": str(analysis_id), "pid": str(pid)})
        await db.execute(text(
            "INSERT INTO magerit_assets (id, analysis_id, code, name, "
            "asset_type_code, created_at) "
            "VALUES (:aid, :anid, 'A001', 'Test asset', 'SW', now())",
        ), {"aid": str(asset_id), "anid": str(analysis_id)})
        await db.execute(text(
            "INSERT INTO magerit_risk_calculation (analysis_id, asset_id, "
            "threat_code, dimension, risk_level) "
            "VALUES (:anid, :aid, 'A.5', 'D', 'C')",
        ), {"anid": str(analysis_id), "aid": str(asset_id)})

    svc = DiscrepancyDetectorService()
    run = await svc.scan_project(db, pid)

    assert run.run_status == "completed"
    discrepancies = await svc.list_discrepancies(db, pid)
    types = {d.discrepancy_type for d in discrepancies}
    assert "magerit_vs_findings" in types
    mvf = [d for d in discrepancies if d.discrepancy_type == "magerit_vs_findings"]
    assert mvf[0].severity == "high"
    assert mvf[0].motor_a == "m02"
    assert mvf[0].motor_b == "m04"


@pytest.mark.asyncio
async def test_detect_dda_vs_documents_aplicable_without_approved_docs(db):
    """Medidas DdA aplicables con 0 documentos approved → NC documental."""
    _, project_id = await setup_test_project(db)
    pid = uuid.UUID(project_id)

    async with _admin_setup(db):
        # Lookup any ens_measure existing (seed canónico ya cargado)
        measure_row = (await db.execute(text(
            "SELECT id FROM ens_measures LIMIT 1",
        ))).first()
        assert measure_row is not None, "ens_measures seed required"
        measure_id = measure_row[0]
        await db.execute(text(
            "INSERT INTO dda_entries (id, project_id, measure_id, "
            "aplicabilidad, created_at) "
            "VALUES (:eid, :pid, :mid, 'aplicable', now())",
        ), {
            "eid": str(uuid.uuid4()),
            "pid": str(pid),
            "mid": str(measure_id),
        })

    svc = DiscrepancyDetectorService()
    run = await svc.scan_project(db, pid)

    assert run.run_status == "completed"
    discrepancies = await svc.list_discrepancies(db, pid)
    types = {d.discrepancy_type for d in discrepancies}
    assert "dda_vs_documents" in types
    dvd = [d for d in discrepancies if d.discrepancy_type == "dda_vs_documents"]
    assert dvd[0].severity == "high"
    assert dvd[0].motor_a == "m03"
    assert dvd[0].motor_b == "m06"


@pytest.mark.asyncio
async def test_detect_findings_vs_remediation_critical_unplanned(db):
    """Findings críticos abiertos sin remediation_plan → NC critical."""
    _, project_id = await setup_test_project(db)
    pid = uuid.UUID(project_id)

    finding_id = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO findings (id, project_id, severidad, estado, "
            "descripcion, created_at) "
            "VALUES (:fid, :pid, 'critica', 'abierto', 'test finding', now())",
        ), {"fid": str(finding_id), "pid": str(pid)})

    svc = DiscrepancyDetectorService()
    run = await svc.scan_project(db, pid)

    assert run.run_status == "completed"
    discrepancies = await svc.list_discrepancies(db, pid)
    types = {d.discrepancy_type for d in discrepancies}
    assert "findings_vs_remediation" in types
    fvr = [d for d in discrepancies if d.discrepancy_type == "findings_vs_remediation"]
    assert fvr[0].severity == "critical"
    assert fvr[0].motor_a == "m04"
    assert fvr[0].motor_b == "m19"


@pytest.mark.asyncio
async def test_detect_findings_vs_remediation_high_with_plan_no_discrepancy(db):
    """Findings altos con remediation_plan asignado → NO discrepancia."""
    _, project_id = await setup_test_project(db)
    pid = uuid.UUID(project_id)

    finding_id = uuid.uuid4()
    plan_id = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO findings (id, project_id, severidad, estado, "
            "descripcion, created_at) "
            "VALUES (:fid, :pid, 'alta', 'en_curso', 'test', now())",
        ), {"fid": str(finding_id), "pid": str(pid)})
        await db.execute(text(
            "INSERT INTO remediation_plans (id, finding_id, accion, "
            "estado, created_at) "
            "VALUES (:rid, :fid, 'mitigar', 'planificado', now())",
        ), {"rid": str(plan_id), "fid": str(finding_id)})

    svc = DiscrepancyDetectorService()
    run = await svc.scan_project(db, pid)

    assert run.run_status == "completed"
    discrepancies = await svc.list_discrepancies(db, pid)
    fvr = [d for d in discrepancies if d.discrepancy_type == "findings_vs_remediation"]
    # Sin findings sin remediation · 0 NC fvr
    assert len(fvr) == 0


@pytest.mark.asyncio
async def test_scan_motors_scanned_includes_new_motors(db):
    """scan_project motors_scanned incluye m02 m03 m04 m06 m07 m19."""
    _, project_id = await setup_test_project(db)
    pid = uuid.UUID(project_id)

    svc = DiscrepancyDetectorService()
    run = await svc.scan_project(db, pid)

    motors = set(run.motors_scanned)
    assert {"m02", "m03", "m04", "m06", "m07", "m19"}.issubset(motors)
