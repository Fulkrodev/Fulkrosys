"""CLUSTER 3 Phase C4.2 draft_report_api endpoint tests.

Verifica:
1. Auditor POST returns signed PDF binary + headers + audit_log emit
2. Auditor GET preview returns HTML
3. Admin POST returns signed PDF + audit_log direct emit
4. Recommendation override accepted · invalid rejected 400
5. Token gate enforced (bogus → 403)
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text as sa_text

from backend.app.motors.m09_audit_prep.audit_events import (
    ADMIN_DRAFT_REPORT_GENERATED,
    AUDITOR_DRAFT_REPORT_GENERATED,
    AUDITOR_DRAFT_REPORT_PREVIEW,
    AUDITOR_EVENT_TYPES,
    is_auditor_event,
)
from backend.app.motors.m12_magic_link.purposes import MagicLinkPurpose
from backend.app.motors.m12_magic_link.schemas import MagicLinkGenerateRequest
from backend.app.motors.m12_magic_link.service import MagicLinkService
from backend.tests.conftest import _admin_setup, setup_test_project


async def _create_link(db, *, project_id: str):
    req = MagicLinkGenerateRequest(
        project_id=uuid.UUID(project_id),
        purpose=MagicLinkPurpose.AUDITOR_PORTAL_ENAC,
        recipient_email="auditor-test@ejemplo.es",
    )
    svc = MagicLinkService(db)
    return await svc.generate_magic_link(req, base_url="http://test")


def test_canonical_namespace_includes_draft_report_events():
    assert is_auditor_event(AUDITOR_DRAFT_REPORT_GENERATED)
    assert is_auditor_event(AUDITOR_DRAFT_REPORT_PREVIEW)
    assert is_auditor_event(ADMIN_DRAFT_REPORT_GENERATED)
    assert AUDITOR_DRAFT_REPORT_GENERATED in AUDITOR_EVENT_TYPES


@pytest.mark.asyncio
async def test_auditor_post_returns_signed_pdf(async_client, db):
    _, project_id = await setup_test_project(db)
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    r = await async_client.post(
        f"/api/v1/public/auditor-portal/{resp.token}/audit/draft-report",
        json={},
    )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"
    assert "attachment" in r.headers["content-disposition"]
    assert r.headers["x-signature-algorithm"] == "Ed25519"
    assert len(r.headers["x-pdf-sha256"]) == 64
    assert r.content[:4] == b"%PDF"
    assert len(r.content) > 1000


@pytest.mark.asyncio
async def test_auditor_post_emits_canonical_event(async_client, db):
    _, project_id = await setup_test_project(db)
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    await async_client.post(
        f"/api/v1/public/auditor-portal/{resp.token}/audit/draft-report",
        json={"auditor_opinion_text": "Opinión preliminar de prueba"},
    )

    async with _admin_setup(db):
        row = (await db.execute(sa_text(
            "SELECT accion, payload_new->>'recommendation', "
            "payload_new->>'opinion_text_length' "
            "FROM audit_log "
            "WHERE accion = :accion AND project_id = :pid "
            "ORDER BY timestamp DESC LIMIT 1"
        ), {
            "accion": AUDITOR_DRAFT_REPORT_GENERATED, "pid": project_id,
        })).first()
    assert row is not None
    assert row[0] == AUDITOR_DRAFT_REPORT_GENERATED
    # opinion_text_length must reflect non-zero length
    assert int(row[2]) > 0


@pytest.mark.asyncio
async def test_auditor_get_preview_returns_html(async_client, db):
    _, project_id = await setup_test_project(db)
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    r = await async_client.get(
        f"/api/v1/public/auditor-portal/{resp.token}/audit/draft-report/preview",
    )
    assert r.status_code == 200, r.text
    assert "text/html" in r.headers["content-type"]
    body = r.text
    assert "<!DOCTYPE html>" in body
    assert "BORRADOR" in body
    assert "Categoría" in body or "Categoria" in body


@pytest.mark.asyncio
async def test_auditor_get_preview_emits_preview_event(async_client, db):
    _, project_id = await setup_test_project(db)
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    await async_client.get(
        f"/api/v1/public/auditor-portal/{resp.token}/audit/draft-report/preview",
    )
    async with _admin_setup(db):
        row = (await db.execute(sa_text(
            "SELECT accion FROM audit_log "
            "WHERE accion = :accion AND project_id = :pid "
            "ORDER BY timestamp DESC LIMIT 1"
        ), {
            "accion": AUDITOR_DRAFT_REPORT_PREVIEW, "pid": project_id,
        })).first()
    assert row is not None
    assert row[0] == AUDITOR_DRAFT_REPORT_PREVIEW


@pytest.mark.asyncio
async def test_auditor_post_invalid_recommendation_400(async_client, db):
    _, project_id = await setup_test_project(db)
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    r = await async_client.post(
        f"/api/v1/public/auditor-portal/{resp.token}/audit/draft-report",
        json={"recommendation": "INVALID_VALUE"},
    )
    assert r.status_code == 400
    assert "recommendation" in r.text.lower()


@pytest.mark.asyncio
async def test_auditor_post_bogus_token_403(async_client, db):
    r = await async_client.post(
        "/api/v1/public/auditor-portal/bogus.jwt.token/audit/draft-report",
        json={},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_admin_post_returns_signed_pdf_and_emits_event(async_client, db):
    _, project_id = await setup_test_project(db)
    await db.commit()

    r = await async_client.post(
        f"/api/v1/admin/projects/{project_id}/audit/draft-report",
        json={"recommendation": "APROBAR_CON_CONDICIONES"},
    )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"
    assert r.headers["x-recommendation"] == "APROBAR_CON_CONDICIONES"

    async with _admin_setup(db):
        row = (await db.execute(sa_text(
            "SELECT accion, payload_new->>'recommendation' FROM audit_log "
            "WHERE accion = :accion AND project_id = :pid "
            "ORDER BY timestamp DESC LIMIT 1"
        ), {
            "accion": ADMIN_DRAFT_REPORT_GENERATED, "pid": project_id,
        })).first()
    assert row is not None
    assert row[0] == ADMIN_DRAFT_REPORT_GENERATED
    assert row[1] == "APROBAR_CON_CONDICIONES"


@pytest.mark.asyncio
async def test_admin_get_preview_returns_html(async_client, db):
    _, project_id = await setup_test_project(db)
    await db.commit()

    r = await async_client.get(
        f"/api/v1/admin/projects/{project_id}/audit/draft-report/preview",
    )
    assert r.status_code == 200, r.text
    assert "text/html" in r.headers["content-type"]
    assert "BORRADOR" in r.text
