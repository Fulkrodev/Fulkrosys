"""Auditor portal Phase 5 Cluster C views · Audit Log + Pentest + Documents.

Verifica para cada endpoint:
1. 200 OK + payload shape
2. audit_log row emitted target=<view> en payload_new
3. Filter param applied (audit_log accion · limit) · empty-state graceful
4. Token gate respected (bogus → 403)
5. R6 hash chain integrity preserved (audit_log view shows hash_current)

Architecture mirror Clusters A + B.
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
# Audit Log view
# ══════════════════════════════════════════════════════════════════════

async def test_audit_log_view_returns_entries(async_client, db):
    """GET /audit-log returns entries · project bounded · view event own audit_log."""
    _, project_id = await setup_test_project(db)
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    r = await async_client.get(
        f"/api/v1/public/auditor-portal/{resp.token}/audit-log",
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["project_id"] == project_id
    assert "entries" in body
    assert "total_for_project" in body
    assert body["limit"] == 100
    # The view itself emits audit_log row · al menos 1
    assert body["returned"] >= 1


async def test_audit_log_view_emits_target_audit_log(async_client, db):
    _, project_id = await setup_test_project(db)
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    await async_client.get(
        f"/api/v1/public/auditor-portal/{resp.token}/audit-log",
    )

    async with _admin_setup(db):
        row = (await db.execute(sa_text(
            "SELECT accion, payload_new->>'target' FROM audit_log "
            "WHERE tabla = 'auditor_portal' "
            "AND payload_new->>'target' = 'audit_log' "
            "AND project_id = :pid ORDER BY timestamp DESC LIMIT 1"
        ), {"pid": project_id})).first()
    assert row is not None
    assert row[1] == "audit_log"


async def test_audit_log_view_accion_filter(async_client, db):
    """Filter accion devuelve sólo entries con accion match."""
    _, project_id = await setup_test_project(db)
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    # Trigger another view to populate diverse acciones
    await async_client.get(
        f"/api/v1/public/auditor-portal/{resp.token}/summary",
    )

    r = await async_client.get(
        f"/api/v1/public/auditor-portal/{resp.token}/audit-log?accion=auditor_portal.view&limit=10",
    )
    assert r.status_code == 200
    body = r.json()
    assert body["filter_accion"] == "auditor_portal.view"
    assert body["limit"] == 10
    for entry in body["entries"]:
        assert entry["accion"] == "auditor_portal.view"


async def test_audit_log_view_hash_truncated(async_client, db):
    """hash_current entries truncated 16 chars + ellipsis para chain integrity preserved."""
    _, project_id = await setup_test_project(db)
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    r = await async_client.get(
        f"/api/v1/public/auditor-portal/{resp.token}/audit-log",
    )
    body = r.json()
    assert body["returned"] >= 1
    for entry in body["entries"]:
        if entry["hash_current"]:
            assert entry["hash_current"].endswith("…")


# ══════════════════════════════════════════════════════════════════════
# Pentest view
# ══════════════════════════════════════════════════════════════════════

async def test_pentest_view_empty_state(async_client, db):
    """Sin verification_runs · total_runs=0 + runs=[] graceful."""
    _, project_id = await setup_test_project(db)
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    r = await async_client.get(
        f"/api/v1/public/auditor-portal/{resp.token}/pentest",
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total_runs"] == 0
    assert body["runs"] == []


async def test_pentest_view_emits_target_pentest(async_client, db):
    _, project_id = await setup_test_project(db)
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    await async_client.get(
        f"/api/v1/public/auditor-portal/{resp.token}/pentest",
    )

    async with _admin_setup(db):
        row = (await db.execute(sa_text(
            "SELECT accion, payload_new->>'target' FROM audit_log "
            "WHERE tabla = 'auditor_portal' "
            "AND payload_new->>'target' = 'pentest' "
            "AND project_id = :pid ORDER BY timestamp DESC LIMIT 1"
        ), {"pid": project_id})).first()
    assert row is not None
    assert row[1] == "pentest"


async def test_pentest_view_with_run_returns_severity_counts(async_client, db):
    """Insert verification_run · response includes severity_counts shape."""
    _, project_id = await setup_test_project(db)
    run_id = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(sa_text(
            "INSERT INTO verification_runs (id, project_id, category, mode, "
            "status, scope_jsonb, total_findings, confirmed_findings, "
            "critical_count, high_count, medium_count, low_count, info_count, "
            "security_score) "
            "VALUES (:id, :pid, 'ALTO', 'external_handoff', 'completed', "
            "'{}'::jsonb, 10, 8, 2, 3, 2, 1, 0, 75)"
        ), {"id": str(run_id), "pid": project_id})
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    r = await async_client.get(
        f"/api/v1/public/auditor-portal/{resp.token}/pentest",
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total_runs"] == 1
    run = body["runs"][0]
    assert run["category"] == "ALTO"
    assert run["security_score"] == 75
    assert run["severity_counts"]["critical"] == 2
    assert run["severity_counts"]["high"] == 3


# ══════════════════════════════════════════════════════════════════════
# Documents view
# ══════════════════════════════════════════════════════════════════════

async def test_documents_view_empty_state(async_client, db):
    """Sin audit_preparation_runs · total_runs=0 + runs=[]."""
    _, project_id = await setup_test_project(db)
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    r = await async_client.get(
        f"/api/v1/public/auditor-portal/{resp.token}/documents",
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total_runs"] == 0
    assert body["runs"] == []
    assert body["signed_zip_endpoint"].startswith(
        "/api/v1/public/auditor-portal/"
    )


async def test_documents_view_emits_target_documents(async_client, db):
    _, project_id = await setup_test_project(db)
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    await async_client.get(
        f"/api/v1/public/auditor-portal/{resp.token}/documents",
    )

    async with _admin_setup(db):
        row = (await db.execute(sa_text(
            "SELECT accion, payload_new->>'target' FROM audit_log "
            "WHERE tabla = 'auditor_portal' "
            "AND payload_new->>'target' = 'documents' "
            "AND project_id = :pid ORDER BY timestamp DESC LIMIT 1"
        ), {"pid": project_id})).first()
    assert row is not None
    assert row[1] == "documents"


async def test_documents_view_signed_zip_flag(async_client, db):
    """Run con dossier_generated_at flag signed_zip_available=true."""
    _, project_id = await setup_test_project(db)
    run_id = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(sa_text(
            "INSERT INTO audit_preparation_runs (id, project_id, categoria, "
            "estado, dossier_generated_at) "
            "VALUES (:id, :pid, 'MEDIA', 'dossier_generated', now())"
        ), {"id": str(run_id), "pid": project_id})
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    r = await async_client.get(
        f"/api/v1/public/auditor-portal/{resp.token}/documents",
    )
    body = r.json()
    assert body["total_runs"] == 1
    assert body["runs"][0]["signed_zip_available"] is True


# ══════════════════════════════════════════════════════════════════════
# Token gate cross-section
# ══════════════════════════════════════════════════════════════════════

async def test_views_reject_invalid_token_cluster_c(async_client, db):
    for section in ("audit-log", "pentest", "documents"):
        r = await async_client.get(
            f"/api/v1/public/auditor-portal/bogus.jwt.token/{section}",
        )
        assert r.status_code == 403, f"{section}: {r.text}"
