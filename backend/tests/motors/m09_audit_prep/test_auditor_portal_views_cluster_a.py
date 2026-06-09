"""Auditor portal Phase 5 Cluster A views · Summary + DdA + MAGERIT.

Verifica para cada endpoint:
1. 200 OK + payload shape (read-only data fetched)
2. audit_log row emitted con accion auditor_portal.view target payload
3. NO consume usos (peek-only · solo session start consume)
4. RLS isolation respected (project_id matches token-bound project)

Architecture mirror Phase 4 test_auditor_portal.py · pattern reusable.
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
# Summary view
# ══════════════════════════════════════════════════════════════════════

async def test_summary_view_returns_metadata_and_counts(async_client, db):
    """GET /summary returns cliente + project + counts."""
    _, project_id = await setup_test_project(db)
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    r = await async_client.get(
        f"/api/v1/public/auditor-portal/{resp.token}/summary",
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "cliente" in body
    assert "project" in body
    assert "counts" in body
    assert body["project"]["id"] == project_id
    counts = body["counts"]
    assert "dda_entries" in counts
    assert "evidence_files" in counts
    assert "magerit_analyses" in counts
    assert "pentest_runs" in counts


async def test_summary_view_emits_audit_log_with_target(async_client, db):
    """GET /summary emite audit_log accion auditor_portal.view payload target=summary."""
    _, project_id = await setup_test_project(db)
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    await async_client.get(
        f"/api/v1/public/auditor-portal/{resp.token}/summary",
    )

    async with _admin_setup(db):
        row = (await db.execute(sa_text(
            "SELECT accion, payload_new->>'target' AS target, project_id "
            "FROM audit_log "
            "WHERE tabla = 'auditor_portal' AND accion = 'auditor_portal.view' "
            "AND project_id = :pid "
            "AND payload_new->>'target' = 'summary' "
            "ORDER BY timestamp DESC LIMIT 1"
        ), {"pid": project_id})).first()
    assert row is not None, "audit_log row con target=summary debe persistir"
    assert row[0] == "auditor_portal.view"
    assert row[1] == "summary"
    assert str(row[2]) == project_id


async def test_summary_view_does_not_consume_usos(async_client, db):
    """View peek-only · NO incrementa usos (solo session start consume)."""
    _, project_id = await setup_test_project(db)
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    async with _admin_setup(db):
        before = (await db.execute(sa_text(
            "SELECT usos FROM magic_links WHERE id = :id"
        ), {"id": str(resp.magic_link_id)})).scalar_one()

    await async_client.get(
        f"/api/v1/public/auditor-portal/{resp.token}/summary",
    )

    async with _admin_setup(db):
        after = (await db.execute(sa_text(
            "SELECT usos FROM magic_links WHERE id = :id"
        ), {"id": str(resp.magic_link_id)})).scalar_one()
    assert after == before, "View peek NO debe incrementar usos"


# ══════════════════════════════════════════════════════════════════════
# DdA view
# ══════════════════════════════════════════════════════════════════════

async def test_dda_view_returns_medidas_list(async_client, db):
    """GET /dda devuelve estructura medidas + total + is_signed."""
    _, project_id = await setup_test_project(db)
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    r = await async_client.get(
        f"/api/v1/public/auditor-portal/{resp.token}/dda",
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["project_id"] == project_id
    assert "medidas" in body
    assert isinstance(body["medidas"], list)
    assert "total" in body
    assert "is_signed" in body


async def test_dda_view_family_filter_applied(async_client, db):
    """GET /dda?family=org responde 200 + filter_family echo."""
    _, project_id = await setup_test_project(db)
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    r = await async_client.get(
        f"/api/v1/public/auditor-portal/{resp.token}/dda?family=org",
    )
    assert r.status_code == 200
    body = r.json()
    assert body["filter_family"] == "org"


async def test_dda_view_emits_audit_log_target_dda(async_client, db):
    _, project_id = await setup_test_project(db)
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    await async_client.get(
        f"/api/v1/public/auditor-portal/{resp.token}/dda",
    )

    async with _admin_setup(db):
        row = (await db.execute(sa_text(
            "SELECT accion, payload_new->>'target' FROM audit_log "
            "WHERE tabla = 'auditor_portal' "
            "AND payload_new->>'target' = 'dda' "
            "AND project_id = :pid ORDER BY timestamp DESC LIMIT 1"
        ), {"pid": project_id})).first()
    assert row is not None
    assert row[1] == "dda"


# ══════════════════════════════════════════════════════════════════════
# MAGERIT view
# ══════════════════════════════════════════════════════════════════════

async def test_magerit_view_returns_empty_when_no_analysis(async_client, db):
    """Sin análisis MAGERIT registrado · returns analysis=null + assets=[]."""
    _, project_id = await setup_test_project(db)
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    r = await async_client.get(
        f"/api/v1/public/auditor-portal/{resp.token}/magerit",
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["project_id"] == project_id
    assert body["analysis"] is None
    assert body["assets"] == []
    assert body["risks_total"] == 0


async def test_magerit_view_emits_audit_log_target_magerit(async_client, db):
    _, project_id = await setup_test_project(db)
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    await async_client.get(
        f"/api/v1/public/auditor-portal/{resp.token}/magerit",
    )

    async with _admin_setup(db):
        row = (await db.execute(sa_text(
            "SELECT accion, payload_new->>'target' FROM audit_log "
            "WHERE tabla = 'auditor_portal' "
            "AND payload_new->>'target' = 'magerit' "
            "AND project_id = :pid ORDER BY timestamp DESC LIMIT 1"
        ), {"pid": project_id})).first()
    assert row is not None
    assert row[1] == "magerit"


# ══════════════════════════════════════════════════════════════════════
# Token gate cross-section (regression Phase 4)
# ══════════════════════════════════════════════════════════════════════

async def test_views_reject_invalid_token(async_client, db):
    """Views deny acceso con token inválido (403 Invalid token)."""
    for section in ("summary", "dda", "magerit"):
        r = await async_client.get(
            f"/api/v1/public/auditor-portal/bogus.jwt.token/{section}",
        )
        assert r.status_code == 403, f"{section}: {r.text}"
