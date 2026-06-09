"""Auditor portal Phase 5 Cluster B views · Plan + Evidence + E-041.

Verifica para cada endpoint:
1. 200 OK + payload shape (read-only data fetched)
2. audit_log row emitted con accion auditor_portal.view target payload
3. Empty-state graceful (project sin plan / evidences / declarations)
4. Token gate respected (bogus → 403)

Architecture mirror Cluster A test_auditor_portal_views_cluster_a.py.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text as sa_text

from backend.app.motors.m12_magic_link.purposes import MagicLinkPurpose
from backend.app.motors.m12_magic_link.schemas import MagicLinkGenerateRequest
from backend.app.motors.m12_magic_link.service import MagicLinkService
from backend.tests.conftest import _admin_setup, setup_test_project


pytestmark = pytest.mark.asyncio


async def _create_link(db, *, project_id: str):
    req = MagicLinkGenerateRequest(
        project_id=uuid.UUID(project_id),
        purpose=MagicLinkPurpose.AUDITOR_PORTAL_ENAC,
        recipient_email="auditor-test@ejemplo.es",
    )
    svc = MagicLinkService(db)
    return await svc.generate_magic_link(req, base_url="http://test")


# ══════════════════════════════════════════════════════════════════════
# Plan view
# ══════════════════════════════════════════════════════════════════════

async def test_plan_view_returns_empty_when_no_plan(async_client, db):
    """Sin plan registrado · returns plan=null + tasks=[]."""
    _, project_id = await setup_test_project(db)
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    r = await async_client.get(
        f"/api/v1/public/auditor-portal/{resp.token}/plan",
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["project_id"] == project_id
    assert body["plan"] is None
    assert body["tasks"] == []


async def test_plan_view_emits_audit_log_target_plan(async_client, db):
    _, project_id = await setup_test_project(db)
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    await async_client.get(
        f"/api/v1/public/auditor-portal/{resp.token}/plan",
    )

    async with _admin_setup(db):
        row = (await db.execute(sa_text(
            "SELECT accion, payload_new->>'target' FROM audit_log "
            "WHERE tabla = 'auditor_portal' "
            "AND payload_new->>'target' = 'plan' "
            "AND project_id = :pid ORDER BY timestamp DESC LIMIT 1"
        ), {"pid": project_id})).first()
    assert row is not None
    assert row[1] == "plan"


async def test_plan_view_with_data_returns_plan_and_tasks(async_client, db):
    """Plan + tasks insertados retornan estructura completa."""
    _, project_id = await setup_test_project(db)
    plan_id = uuid.uuid4()
    task_id = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(sa_text(
            "INSERT INTO project_plans (id, project_id, version, categoria, "
            "estado, start_date, end_date_estimated, "
            "total_effort_marcos_hours, total_duration_weeks) "
            "VALUES (:id, :pid, 1, 'MEDIA', 'aprobado', "
            "'2026-01-01'::date, '2026-03-01'::date, 80.0, 8)"
        ), {"id": str(plan_id), "pid": project_id})
        await db.execute(sa_text(
            "INSERT INTO wbs_tasks (id, project_plan_id, project_id, "
            "task_code, task_name, phase, responsible, status, "
            "is_critical_path, progress_pct) "
            "VALUES (:id, :ppid, :pid, 'T01', 'Categorización', "
            "'F1', 'Marcos', 'in_progress', true, 30)"
        ), {
            "id": str(task_id), "ppid": str(plan_id), "pid": project_id,
        })
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    r = await async_client.get(
        f"/api/v1/public/auditor-portal/{resp.token}/plan",
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["plan"] is not None
    assert body["plan"]["version"] == 1
    assert body["plan"]["categoria"] == "MEDIA"
    assert body["plan"]["estado"] == "aprobado"
    assert len(body["tasks"]) == 1
    assert body["tasks"][0]["task_code"] == "T01"
    assert body["tasks"][0]["is_critical_path"] is True
    assert body["tasks"][0]["progress_pct"] == 30


# ══════════════════════════════════════════════════════════════════════
# Evidence view
# ══════════════════════════════════════════════════════════════════════

async def test_evidence_view_empty_state(async_client, db):
    """Sin evidencias registradas · total_items=0 + items=[]."""
    _, project_id = await setup_test_project(db)
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    r = await async_client.get(
        f"/api/v1/public/auditor-portal/{resp.token}/evidence",
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total_items"] == 0
    assert body["items"] == []
    assert body["grouped_by_measure"] == []


async def test_evidence_view_measure_filter_applied(async_client, db):
    _, project_id = await setup_test_project(db)
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    r = await async_client.get(
        f"/api/v1/public/auditor-portal/{resp.token}/evidence?measure_code=org.1",
    )
    assert r.status_code == 200
    assert r.json()["filter_measure_code"] == "org.1"


async def test_evidence_view_emits_audit_log_target_evidence(async_client, db):
    _, project_id = await setup_test_project(db)
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    await async_client.get(
        f"/api/v1/public/auditor-portal/{resp.token}/evidence",
    )

    async with _admin_setup(db):
        row = (await db.execute(sa_text(
            "SELECT accion, payload_new->>'target' FROM audit_log "
            "WHERE tabla = 'auditor_portal' "
            "AND payload_new->>'target' = 'evidence' "
            "AND project_id = :pid ORDER BY timestamp DESC LIMIT 1"
        ), {"pid": project_id})).first()
    assert row is not None
    assert row[1] == "evidence"


# ══════════════════════════════════════════════════════════════════════
# E-041 view
# ══════════════════════════════════════════════════════════════════════

async def test_e041_view_empty_state(async_client, db):
    """Sin declaraciones · total=0 + declarations=[]."""
    _, project_id = await setup_test_project(db)
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    r = await async_client.get(
        f"/api/v1/public/auditor-portal/{resp.token}/e041",
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 0
    assert body["declarations"] == []


async def test_e041_view_emits_audit_log_target_e041(async_client, db):
    _, project_id = await setup_test_project(db)
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    await async_client.get(
        f"/api/v1/public/auditor-portal/{resp.token}/e041",
    )

    async with _admin_setup(db):
        row = (await db.execute(sa_text(
            "SELECT accion, payload_new->>'target' FROM audit_log "
            "WHERE tabla = 'auditor_portal' "
            "AND payload_new->>'target' = 'e041' "
            "AND project_id = :pid ORDER BY timestamp DESC LIMIT 1"
        ), {"pid": project_id})).first()
    assert row is not None
    assert row[1] == "e041"


async def test_e041_view_with_signed_declaration_shows_is_signed_true(async_client, db):
    """basic_declarations row con signed_at + signed_hash → is_signed=True."""
    _, project_id = await setup_test_project(db)
    decl_id = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(sa_text(
            "INSERT INTO basic_declarations (id, project_id, declaration_type, "
            "status, responsible_person_name, responsible_person_email, "
            "signed_at, signed_hash) "
            "VALUES (:id, :pid, 'initial', 'signed', "
            "'Cliente Test', 'cliente@ejemplo.es', "
            "now(), 'abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789')"
        ), {"id": str(decl_id), "pid": project_id})
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    r = await async_client.get(
        f"/api/v1/public/auditor-portal/{resp.token}/e041",
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["declarations"][0]["declaration_type"] == "initial"
    assert body["declarations"][0]["is_signed"] is True
    assert body["declarations"][0]["signed_hash"].startswith("abcdef")


# ══════════════════════════════════════════════════════════════════════
# Token gate cross-section
# ══════════════════════════════════════════════════════════════════════

async def test_views_reject_invalid_token_cluster_b(async_client, db):
    for section in ("plan", "evidence", "e041"):
        r = await async_client.get(
            f"/api/v1/public/auditor-portal/bogus.jwt.token/{section}",
        )
        assert r.status_code == 403, f"{section}: {r.text}"
