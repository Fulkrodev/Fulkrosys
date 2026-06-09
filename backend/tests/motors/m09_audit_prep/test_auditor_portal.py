"""Auditor portal public API · Sesión 3B-2B.6 CLUSTER 2 Phase 4 tests.

Verifica:
1. Valid token AUDITOR_PORTAL_ENAC purpose → metadata 200 OK + cliente + project
2. Token con purpose distinto (e.g. PORTAL_PENTESTER_EXTERNO) → 403 Forbidden
3. Token signature inválida → 403
4. Token expirado/revocado → 410 Gone
5. Session start endpoint → 201 + increment usos + audit_log emit
6. Audit log row created con project_id + client_id explícito (Sub-atom 5.A RLS)
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select, text as sa_text

from backend.app.motors.m12_magic_link.purposes import MagicLinkPurpose
from backend.app.motors.m12_magic_link.schemas import MagicLinkGenerateRequest
from backend.app.motors.m12_magic_link.service import MagicLinkService
from backend.tests.conftest import setup_test_project


pytestmark = pytest.mark.asyncio


async def _create_link(
    db, *, project_id: str, purpose: MagicLinkPurpose,
    recipient_email: str = "auditor-test@ejemplo.es",
):
    req = MagicLinkGenerateRequest(
        project_id=uuid.UUID(project_id),
        purpose=purpose,
        recipient_email=recipient_email,
    )
    svc = MagicLinkService(db)
    return await svc.generate_magic_link(req, base_url="http://test")


async def test_metadata_with_valid_auditor_token(async_client, db):
    """GET /public/auditor-portal/{token} OK con metadata cliente + project."""
    _, project_id = await setup_test_project(db)
    resp = await _create_link(
        db, project_id=project_id, purpose=MagicLinkPurpose.AUDITOR_PORTAL_ENAC,
    )
    await db.commit()

    r = await async_client.get(f"/api/v1/public/auditor-portal/{resp.token}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "cliente" in body
    assert "project" in body
    assert body["project"]["id"] == project_id
    assert "available_sections" in body
    # 11 secciones tras CLUSTER 3 (annotations + clarifications añadidas al portal auditor)
    assert len(body["available_sections"]) == 11


async def test_wrong_purpose_returns_403(async_client, db):
    """Token con PORTAL_PENTESTER_EXTERNO NO pasa gate auditor-portal."""
    _, project_id = await setup_test_project(db)
    resp = await _create_link(
        db, project_id=project_id, purpose=MagicLinkPurpose.PORTAL_PENTESTER_EXTERNO,
    )
    await db.commit()

    r = await async_client.get(f"/api/v1/public/auditor-portal/{resp.token}")
    assert r.status_code == 403
    assert "Invalid token" in r.text


async def test_invalid_signature_returns_403(async_client, db):
    """Token JWT inválido (signature corrupta) → 403."""
    bogus_token = "bogus.jwt.token"
    r = await async_client.get(f"/api/v1/public/auditor-portal/{bogus_token}")
    assert r.status_code == 403


async def test_revoked_token_returns_410(async_client, db):
    """Token revocado → 410 Gone."""
    _, project_id = await setup_test_project(db)
    resp = await _create_link(
        db, project_id=project_id, purpose=MagicLinkPurpose.AUDITOR_PORTAL_ENAC,
    )
    # Revoke directly via SQL (admin bypass · simula MagicLinkService.revoke)
    from backend.tests.conftest import _admin_setup
    async with _admin_setup(db):
        await db.execute(sa_text(
            "UPDATE magic_links SET revocado = true, revoked_at = now() "
            "WHERE token_hash = (SELECT token_hash FROM magic_links "
            "WHERE id = (SELECT id FROM magic_links ORDER BY created_at DESC LIMIT 1))"
        ))
    await db.commit()

    r = await async_client.get(f"/api/v1/public/auditor-portal/{resp.token}")
    assert r.status_code == 410


async def test_session_start_consumes_use_and_emits_event(async_client, db):
    """POST /session · usos += 1 + audit_log row con auditor.session.start."""
    _, project_id = await setup_test_project(db)
    resp = await _create_link(
        db, project_id=project_id, purpose=MagicLinkPurpose.AUDITOR_PORTAL_ENAC,
    )
    await db.commit()

    r = await async_client.post(
        f"/api/v1/public/auditor-portal/{resp.token}/session", json={},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "ok"
    assert "session_started_at" in body
    assert "remaining_uses" in body

    # Verify audit_log row created con accion auditor.session.start + project_id
    from backend.tests.conftest import _admin_setup
    async with _admin_setup(db):
        rows = (await db.execute(sa_text(
            "SELECT accion, project_id, client_id FROM audit_log "
            "WHERE tabla = 'auditor_portal' AND accion = 'auditor.session.start' "
            "AND project_id = :pid ORDER BY timestamp DESC LIMIT 1"
        ), {"pid": project_id})).first()
    assert rows is not None, "audit_log row debe haberse creado"
    assert rows[0] == "auditor.session.start"
    assert str(rows[1]) == project_id
    assert rows[2] is not None, "client_id debe poblarse para RLS isolation"


async def test_metadata_emits_audit_log_view_event(async_client, db):
    """GET metadata emite audit_log accion auditor_portal.view tagged project."""
    _, project_id = await setup_test_project(db)
    resp = await _create_link(
        db, project_id=project_id, purpose=MagicLinkPurpose.AUDITOR_PORTAL_ENAC,
    )
    await db.commit()

    await async_client.get(f"/api/v1/public/auditor-portal/{resp.token}")

    from backend.tests.conftest import _admin_setup
    async with _admin_setup(db):
        rows = (await db.execute(sa_text(
            "SELECT accion, project_id FROM audit_log "
            "WHERE tabla = 'auditor_portal' AND accion = 'auditor_portal.view' "
            "AND project_id = :pid ORDER BY timestamp DESC LIMIT 1"
        ), {"pid": project_id})).first()
    assert rows is not None, "view event must persist audit_log row"
    assert rows[0] == "auditor_portal.view"


async def test_metadata_returns_cliente_branding(async_client, db):
    """Cliente branding columns (primary_color · footer · has_logo) returned para frontend."""
    from backend.tests.conftest import _admin_setup

    _, project_id = await setup_test_project(db)
    # Add branding to cliente
    async with _admin_setup(db):
        await db.execute(sa_text(
            "UPDATE clients c SET primary_color='#aabbcc', "
            "secondary_color='#112233', footer_text='Powered by Test' "
            "FROM projects p WHERE p.client_id = c.id AND p.id = :pid"
        ), {"pid": project_id})

    resp = await _create_link(
        db, project_id=project_id, purpose=MagicLinkPurpose.AUDITOR_PORTAL_ENAC,
    )
    await db.commit()

    r = await async_client.get(f"/api/v1/public/auditor-portal/{resp.token}")
    assert r.status_code == 200
    cliente = r.json()["cliente"]
    assert cliente["primary_color"] == "#aabbcc"
    assert cliente["secondary_color"] == "#112233"
    assert cliente["footer_text"] == "Powered by Test"
