"""Tests · digest manual trigger admin (sub-atom 1.D.X.VERIFY 2a).

Verifica:
- generate_monthly_digest_for_project persiste snapshot + audit_log entry
- compute_compliance_score deterministic (pure function · sin DB)
- triggered_by="admin_manual" registra user_id en snapshot + audit_log
- Idempotente: 2 generations seguidas crean 2 snapshots distintos (NO mismo id)
- get_latest_digest_for_project devuelve último por generated_at DESC
- Project no existente raises DigestProjectNotFoundError
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select, text

from backend.app.models.audit_log import AuditLog
from backend.app.motors.m_cloud_connectors import (
    DigestProjectNotFoundError,
    generate_monthly_digest_for_project,
    get_latest_digest_for_project,
)
from backend.app.motors.m_cloud_connectors.digest_service import (
    _compute_compliance_score,
)
from backend.tests.conftest import setup_test_project


# ============================================================
# Pure function: compliance score formula
# ============================================================


def test_compliance_score_formula_no_gaps_perfect():
    assert _compute_compliance_score({}) == 100


def test_compliance_score_formula_with_gaps():
    """100 - 1*10 - 1*5 - 2*2 - 0*1 = 81."""
    counts = {"critical": 1, "high": 1, "medium": 2}
    assert _compute_compliance_score(counts) == 81


def test_compliance_score_formula_clamped_to_zero():
    """Floor 0 · NO scores negativos aunque haya muchos críticos."""
    counts = {"critical": 50, "high": 50, "medium": 50, "low": 50}
    assert _compute_compliance_score(counts) == 0


# ============================================================
# Service generate + persistence + audit
# ============================================================


async def _insert_gap(
    db, *, project_id: uuid.UUID, severity: str, code: str,
) -> uuid.UUID:
    gap_id = uuid.uuid4()
    await db.execute(text(
        "INSERT INTO cloud_gaps (id, project_id, gap_type, severity, "
        "ens_measure_code, title, suggested_action) "
        "VALUES (:id, :pid, 'structural', :sev, :code, 'T', 'A')"
    ), {
        "id": str(gap_id), "pid": str(project_id), "sev": severity, "code": code,
    })
    await db.flush()
    return gap_id


@pytest.mark.asyncio
async def test_admin_trigger_persists_snapshot_with_user_id(db):
    """admin_manual triggered_by registra user_id en snapshot + audit_log."""
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)
    await _insert_gap(db, project_id=pid, severity="critical", code="op.acc.6")
    await _insert_gap(db, project_id=pid, severity="medium", code="org.1")

    admin_user_id = uuid.uuid4()
    snapshot = await generate_monthly_digest_for_project(
        db,
        project_id=pid,
        triggered_by="admin_manual",
        triggered_by_user_id=admin_user_id,
    )

    assert snapshot.id is not None
    assert snapshot.project_id == pid
    assert snapshot.triggered_by == "admin_manual"
    assert snapshot.triggered_by_user_id == admin_user_id
    # 100 - 1*10 - 0*5 - 1*2 - 0*1 = 88
    assert snapshot.compliance_score == 88
    assert snapshot.open_gaps_total == 2
    assert snapshot.open_gaps_by_severity["critical"] == 1
    assert snapshot.open_gaps_by_severity["medium"] == 1


@pytest.mark.asyncio
async def test_audit_log_entry_created_for_admin_manual(db):
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)

    admin_user_id = uuid.uuid4()
    snapshot = await generate_monthly_digest_for_project(
        db,
        project_id=pid,
        triggered_by="admin_manual",
        triggered_by_user_id=admin_user_id,
    )

    res = await db.execute(
        select(AuditLog).where(
            AuditLog.registro_id == snapshot.id,
        )
    )
    entries = list(res.scalars().all())
    assert len(entries) == 1
    entry = entries[0]
    assert entry.accion == "digest_manual_adm"
    assert entry.tabla == "cloud_digest_snapshots"
    assert entry.usuario == str(admin_user_id)
    assert entry.payload_new["triggered_by"] == "admin_manual"
    assert entry.payload_new["compliance_score"] == 100  # no gaps en test


@pytest.mark.asyncio
async def test_celery_triggered_by_uses_different_accion(db):
    """triggered_by='celery_monthly' usa accion 'celery_digest_generated'."""
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)

    snapshot = await generate_monthly_digest_for_project(
        db, project_id=pid, triggered_by="celery_monthly",
    )

    res = await db.execute(
        select(AuditLog).where(AuditLog.registro_id == snapshot.id)
    )
    entry = res.scalar_one()
    assert entry.accion == "digest_celery"
    assert entry.usuario == "system"


@pytest.mark.asyncio
async def test_generate_idempotent_creates_distinct_snapshots(db):
    """Doble click admin trigger crea 2 snapshots distintos · historial preserved."""
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)

    s1 = await generate_monthly_digest_for_project(
        db, project_id=pid, triggered_by="admin_manual",
    )
    s2 = await generate_monthly_digest_for_project(
        db, project_id=pid, triggered_by="admin_manual",
    )

    assert s1.id != s2.id
    # generated_at de s2 >= s1 (mismo segundo OK · pero NO antes)
    assert s2.generated_at >= s1.generated_at


@pytest.mark.asyncio
async def test_get_latest_returns_most_recent_snapshot(db):
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)

    s1 = await generate_monthly_digest_for_project(
        db, project_id=pid, triggered_by="celery_monthly",
    )
    s2 = await generate_monthly_digest_for_project(
        db, project_id=pid, triggered_by="admin_manual",
    )

    latest = await get_latest_digest_for_project(db, pid)
    assert latest is not None
    assert latest.id == s2.id
    assert latest.triggered_by == "admin_manual"


@pytest.mark.asyncio
async def test_get_latest_returns_none_when_no_snapshot(db):
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)

    latest = await get_latest_digest_for_project(db, pid)
    assert latest is None


@pytest.mark.asyncio
async def test_project_not_found_raises(db):
    with pytest.raises(DigestProjectNotFoundError):
        await generate_monthly_digest_for_project(
            db, project_id=uuid.uuid4(), triggered_by="admin_manual",
        )
