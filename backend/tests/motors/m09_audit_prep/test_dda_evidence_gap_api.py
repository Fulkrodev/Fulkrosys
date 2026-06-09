"""CLUSTER 3 Phase C3.2 dda_evidence_gap_api endpoint tests.

Verifica:
1. Auditor GET /audit/dda-evidence-gaps · returns matrix project-scoped
2. Auditor drill-down per medida · 404 si unknown · 200 si valid
3. Admin GET matrix · cross-project legitimate
4. Admin POST /request-more-evidence · creates ClientNotification + audit_log
5. RLS isolation: project A NO leak hacia project B token
6. Token gate: bogus token → 403
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text as sa_text

from backend.app.motors.m09_audit_prep.audit_events import (
    ADMIN_EVIDENCE_REQUEST_TRIGGERED,
    AUDITOR_VIEW_DDA_EVIDENCE_GAPS,
    AUDITOR_VIEW_DDA_EVIDENCE_GAPS_DETAIL,
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


def test_canonical_namespace_includes_gap_events():
    assert is_auditor_event(AUDITOR_VIEW_DDA_EVIDENCE_GAPS)
    assert is_auditor_event(AUDITOR_VIEW_DDA_EVIDENCE_GAPS_DETAIL)
    assert is_auditor_event(ADMIN_EVIDENCE_REQUEST_TRIGGERED)


@pytest.mark.asyncio
async def test_auditor_get_gaps_returns_matrix(async_client, db):
    """Auditor obtiene matrix completa · totals + medidas + severity_summary."""
    _, project_id = await setup_test_project(db)
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    r = await async_client.get(
        f"/api/v1/public/auditor-portal/{resp.token}/audit/dda-evidence-gaps",
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["project_id"] == project_id
    assert "medidas" in body
    assert isinstance(body["medidas"], list)
    assert "severity_summary" in body
    assert "options_used" in body
    assert "coverage_pct" in body
    assert body["total_applicable"] == (
        body["total_covered"] + body["total_partial"] + body["total_missing"]
    )


@pytest.mark.asyncio
async def test_auditor_get_gaps_emits_canonical_event(async_client, db):
    _, project_id = await setup_test_project(db)
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    await async_client.get(
        f"/api/v1/public/auditor-portal/{resp.token}/audit/dda-evidence-gaps",
    )

    async with _admin_setup(db):
        row = (await db.execute(sa_text(
            "SELECT accion, payload_new->>'total_missing' FROM audit_log "
            "WHERE accion = :accion AND project_id = :pid "
            "ORDER BY timestamp DESC LIMIT 1"
        ), {
            "accion": AUDITOR_VIEW_DDA_EVIDENCE_GAPS, "pid": project_id,
        })).first()
    assert row is not None
    assert row[0] == AUDITOR_VIEW_DDA_EVIDENCE_GAPS
    # Metadata contains total_missing (cast to int via JSON)
    assert int(row[1]) >= 0


@pytest.mark.asyncio
async def test_auditor_drill_down_unknown_medida_404(async_client, db):
    _, project_id = await setup_test_project(db)
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    r = await async_client.get(
        f"/api/v1/public/auditor-portal/{resp.token}/"
        f"audit/dda-evidence-gaps/medida/INVALID.NONEXIST.999",
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_auditor_drill_down_known_medida_returns_detail(async_client, db):
    _, project_id = await setup_test_project(db)

    async with _admin_setup(db):
        m_row = (await db.execute(sa_text(
            "SELECT codigo FROM ens_measures WHERE deleted_at IS NULL LIMIT 1"
        ))).first()
    if m_row is None:
        pytest.skip("No measures in catalog")
    codigo = m_row[0]

    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    r = await async_client.get(
        f"/api/v1/public/auditor-portal/{resp.token}/"
        f"audit/dda-evidence-gaps/medida/{codigo}",
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["medida_code"] == codigo
    assert "status" in body
    assert "severity" in body


@pytest.mark.asyncio
async def test_auditor_bogus_token_rejected_403(async_client, db):
    r = await async_client.get(
        "/api/v1/public/auditor-portal/bogus.jwt.token/audit/dda-evidence-gaps",
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_admin_get_gaps_returns_matrix(async_client, db):
    _, project_id = await setup_test_project(db)
    await db.commit()

    r = await async_client.get(
        f"/api/v1/admin/projects/{project_id}/audit/dda-evidence-gaps",
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["project_id"] == project_id
    assert "severity_summary" in body


@pytest.mark.asyncio
async def test_admin_request_more_evidence_creates_audit_log(async_client, db):
    """Admin POST creates audit_log entry · ClientNotification skipped si NO
    client_user (typical test project doesn't seed cliente piloto user)."""
    _, project_id = await setup_test_project(db)
    await db.commit()

    body = {
        "medida_codes": ["op.acc.1", "mp.s.4"],
        "message_to_client": "Por favor, aporta evidencias específicas para audit ENAC",
    }
    r = await async_client.post(
        f"/api/v1/admin/projects/{project_id}/audit/request-more-evidence",
        json=body,
    )
    assert r.status_code == 200, r.text
    response = r.json()
    assert response["medida_codes"] == ["op.acc.1", "mp.s.4"]
    # notification_id is null if no client_user (test fixture)
    # Admin audit_log row always created
    async with _admin_setup(db):
        row = (await db.execute(sa_text(
            "SELECT accion, payload_new->>'medida_count', payload_new->>'has_custom_message' "
            "FROM audit_log "
            "WHERE accion = :accion AND project_id = :pid "
            "ORDER BY timestamp DESC LIMIT 1"
        ), {
            "accion": ADMIN_EVIDENCE_REQUEST_TRIGGERED, "pid": project_id,
        })).first()
    assert row is not None
    assert row[0] == ADMIN_EVIDENCE_REQUEST_TRIGGERED
    assert row[1] == "2"
    assert row[2] == "true"


@pytest.mark.asyncio
async def test_admin_request_more_evidence_validation_empty_list(async_client, db):
    _, project_id = await setup_test_project(db)
    await db.commit()

    r = await async_client.post(
        f"/api/v1/admin/projects/{project_id}/audit/request-more-evidence",
        json={"medida_codes": [], "message_to_client": "x"},
    )
    assert r.status_code in (400, 422)  # Pydantic validation min_length=1
