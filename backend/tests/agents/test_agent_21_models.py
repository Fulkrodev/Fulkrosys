"""Tests A21 models (MB-8.A.1).

Cobertura mínima:
- Insert A21ScanRun + A21Discrepancy con project context (RLS aware)
- Workflow status transitions (open → resolved)
- CHECK constraints rechazan severity/status inválidos
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from backend.app.models.a21_discrepancies import A21Discrepancy, A21ScanRun
from backend.tests.conftest import setup_test_project


@pytest.mark.asyncio
async def test_a21_scan_run_insert_and_status_transition(db):
    """Crea scan_run pending → running → completed."""
    _, project_id = await setup_test_project(db)

    run = A21ScanRun(
        project_id=uuid.UUID(project_id),
        run_status="pending",
        started_at=datetime.now(timezone.utc),
        motors_scanned=[],
        discrepancies_found=0,
    )
    db.add(run)
    await db.flush()

    assert run.id is not None
    assert run.run_status == "pending"

    run.run_status = "running"
    run.motors_scanned = ["m02", "m03"]
    await db.flush()
    assert run.run_status == "running"

    run.run_status = "completed"
    run.completed_at = datetime.now(timezone.utc)
    run.discrepancies_found = 3
    await db.flush()
    assert run.completed_at is not None


@pytest.mark.asyncio
async def test_a21_discrepancy_insert_and_resolve(db):
    """Crea discrepancia open → acknowledged → resolved."""
    _, project_id = await setup_test_project(db)
    pid = uuid.UUID(project_id)

    run = A21ScanRun(
        project_id=pid,
        run_status="completed",
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        motors_scanned=["m02", "m03"],
        discrepancies_found=1,
    )
    db.add(run)
    await db.flush()

    disc = A21Discrepancy(
        scan_run_id=run.id,
        project_id=pid,
        discrepancy_type="magerit_vs_dda",
        severity="high",
        motor_a="m02",
        motor_b="m03",
        description="Riesgo crítico R-001 sin medida correspondiente en DdA",
        evidence_a={"risk_id": str(uuid.uuid4()), "risk_level": "C"},
        evidence_b={"missing_measure": "op.acc.5"},
    )
    db.add(disc)
    await db.flush()

    assert disc.resolution_status == "open"
    assert disc.resolved_at is None

    disc.resolution_status = "acknowledged"
    disc.resolution_notes = "Marcos vio · revisaremos en próxima reunión"
    await db.flush()
    assert disc.resolution_status == "acknowledged"

    disc.resolution_status = "resolved"
    disc.resolved_at = datetime.now(timezone.utc)
    await db.flush()
    assert disc.resolved_at is not None


@pytest.mark.asyncio
async def test_a21_discrepancy_severity_check_constraint(db):
    """CHECK constraint rechaza severity inválido."""
    _, project_id = await setup_test_project(db)
    pid = uuid.UUID(project_id)

    run = A21ScanRun(
        project_id=pid,
        run_status="completed",
        started_at=datetime.now(timezone.utc),
        motors_scanned=["m02"],
    )
    db.add(run)
    await db.flush()

    bad = A21Discrepancy(
        scan_run_id=run.id,
        project_id=pid,
        discrepancy_type="magerit_vs_dda",
        severity="urgent",  # invalid · solo critical/high/medium/low
        motor_a="m02",
        motor_b="m03",
        description="x",
    )
    db.add(bad)
    with pytest.raises(IntegrityError):
        await db.flush()


@pytest.mark.asyncio
async def test_a21_discrepancy_resolution_check_constraint(db):
    """CHECK constraint rechaza resolution_status inválido."""
    _, project_id = await setup_test_project(db)
    pid = uuid.UUID(project_id)

    run = A21ScanRun(
        project_id=pid,
        run_status="completed",
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    await db.flush()

    bad = A21Discrepancy(
        scan_run_id=run.id,
        project_id=pid,
        discrepancy_type="dda_vs_evidence",
        severity="medium",
        motor_a="m03",
        motor_b="m07",
        description="x",
        resolution_status="closed",  # invalid · open/acknowledged/resolved/dismissed
    )
    db.add(bad)
    with pytest.raises(IntegrityError):
        await db.flush()
