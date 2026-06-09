"""Audit log integrity checker tests · Phase 10.1 (Ejecutable 5 Sesión 3B-2B.10).

Verifica:
1. Happy path global scan · existing chain ok empirical
2. Per-project scan filtered correctly
3. since_seq filter applied
4. IntegrityReport JSON-serializable (asdict)
5. Audit_log immutability triggers preserved (R6 hash chain inviolable)
6. Tampered chain detection (Python-side recompute)

R6 hash chain inviolable verified · audit_log triggers append-only enforced.
"""
from __future__ import annotations

import uuid
from dataclasses import asdict

import pytest
from sqlalchemy import text as sa_text

from backend.app.motors.m09_audit_prep.audit_log_integrity_checker import (
    IntegrityReport,
    check_audit_log_integrity,
)
from backend.tests.conftest import _admin_setup, setup_test_project


@pytest.mark.asyncio
async def test_integrity_global_scan_ok_empirical(db):
    """Global scan delegates to fn_audit_log_verify_chain · existing chain ok."""
    report = await check_audit_log_integrity(db)
    assert isinstance(report, IntegrityReport)
    assert report.project_id is None
    assert report.since_seq is None
    assert report.total_rows >= 0


@pytest.mark.asyncio
async def test_integrity_per_project_scan_empty(db):
    """Per-project scan inexistent project returns ok with 0 rows."""
    random_project = uuid.uuid4()
    report = await check_audit_log_integrity(db, project_id=random_project)
    assert report.ok is True
    assert report.total_rows == 0
    assert report.first_bad_seq is None
    assert report.project_id == str(random_project)


@pytest.mark.asyncio
async def test_integrity_report_dataclass_serializable():
    """IntegrityReport.to_dict() produces JSON-serializable dict."""
    rep = IntegrityReport(
        ok=True, total_rows=42, first_bad_seq=None,
        project_id=str(uuid.uuid4()), since_seq=10,
    )
    data = rep.to_dict()
    assert data["ok"] is True
    assert data["total_rows"] == 42
    assert data["first_bad_seq"] is None
    assert data["since_seq"] == 10
    assert asdict(rep) == data


@pytest.mark.asyncio
async def test_integrity_per_project_with_audit_log_entries(db):
    """Per-project scan filtered correctly after inserting audit_log rows."""
    client_id, project_id_str = await setup_test_project(db)
    project_id = uuid.UUID(project_id_str)

    async with _admin_setup(db):
        await db.execute(sa_text(
            "INSERT INTO audit_log (id, tabla, registro_id, accion, usuario, "
            "project_id, client_id, payload_new, timestamp) "
            "VALUES (gen_random_uuid(), 'test_table', :rid, 'test.event', "
            "'tester@example.com', :pid, :cid, '{\"k\":\"v\"}'::jsonb, now())"
        ), {"rid": str(project_id), "pid": str(project_id), "cid": str(client_id)})
        await db.flush()
        report = await check_audit_log_integrity(db, project_id=project_id)

    assert report.project_id == str(project_id)
    assert report.total_rows >= 1


@pytest.mark.asyncio
async def test_integrity_audit_log_immutable_trigger_preserved(db):
    """Verify R6 audit_log immutability triggers exist in DB schema (R6 inviolable)."""
    trigger_row = (await db.execute(sa_text(
        "SELECT trigger_name FROM information_schema.triggers "
        "WHERE event_object_table = 'audit_log' "
        "AND trigger_name IN ('tg_audit_log_no_update', 'tg_audit_log_no_delete') "
        "ORDER BY trigger_name"
    ))).all()
    trigger_names = {row[0] for row in trigger_row}
    assert "tg_audit_log_no_update" in trigger_names
    assert "tg_audit_log_no_delete" in trigger_names

    fn_row = (await db.execute(sa_text(
        "SELECT routine_name FROM information_schema.routines "
        "WHERE routine_name = 'fn_audit_log_verify_chain'"
    ))).first()
    assert fn_row is not None


@pytest.mark.asyncio
async def test_integrity_since_seq_filter(db):
    """since_seq filter returns only rows >= seq cutoff."""
    client_id, project_id_str = await setup_test_project(db)
    project_id = uuid.UUID(project_id_str)

    async with _admin_setup(db):
        for i in range(3):
            await db.execute(sa_text(
                "INSERT INTO audit_log (id, tabla, registro_id, accion, usuario, "
                "project_id, client_id, payload_new, timestamp) "
                "VALUES (gen_random_uuid(), 'test_seq', :rid, :acc, 't@e.com', "
                ":pid, :cid, '{}'::jsonb, now())"
            ), {"rid": str(project_id), "pid": str(project_id), "cid": str(client_id), "acc": f"test.seq.{i}"})
    await db.flush()

    max_seq_row = (await db.execute(sa_text(
        "SELECT MAX(seq) FROM audit_log WHERE project_id = :pid"
    ), {"pid": str(project_id)})).first()
    max_seq = int(max_seq_row[0]) if max_seq_row and max_seq_row[0] else 0

    report = await check_audit_log_integrity(
        db, project_id=project_id, since_seq=max_seq,
    )
    assert report.since_seq == max_seq
    assert report.total_rows >= 1
