"""Batch A diagnóstico previo · flujo capa legal (Art. 13 + consentimiento + gate).

Prod-fiel: el lead entra account-less (consume → session_secret), ve el texto
Art. 13, y SOLO puede responder el cuestionario tras registrar el consentimiento
(gate /me/next-question + /me/responses → 403 consent_required sin consent).
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from backend.app.models.precliente_consent import PreClienteDiagnosticConsent
from backend.app.motors.m12_magic_link.purposes import MagicLinkPurpose
from backend.app.motors.m16_onboarding.enums import Role, Sector
from backend.app.motors.m16_onboarding.service import create_session
from backend.tests.conftest import setup_test_project

BASE = "/api/v1/onboarding"


async def _lead_session_headers(async_client, db):
    """Crea sesión precliente (emite magic-link) + consume → headers account-less."""
    _, project_id_str = await setup_test_project(db)
    sess = await create_session(
        db, project_id=uuid.UUID(project_id_str),
        sector=Sector.SERVICIOS_PROFESIONALES, role=Role.SPONSOR,
        interlocutor_email="lead@example.com", interlocutor_name="Lead",
        ttl_hours=14 * 24, language="es", metadata_extra=None,
        purpose=MagicLinkPurpose.DIAGNOSTICO_PRECLIENTE,
    )
    token = sess["magic_link_url"].split("token=")[1]
    r = await async_client.post(f"{BASE}/consume", json={"token": token})
    assert r.status_code == 200, r.text
    body = r.json()
    headers = {
        "X-Onboarding-Session-Id": body["session_id"],
        "X-Onboarding-Session-Secret": body["session_secret"],
    }
    return headers, uuid.UUID(body["session_id"])


@pytest.mark.asyncio
async def test_consent_text_then_gate_then_consent(async_client, db):
    headers, session_id = await _lead_session_headers(async_client, db)

    # 1. El lead ve el texto Art. 13 versionado.
    ct = await async_client.get(f"{BASE}/me/consent-text", headers=headers)
    assert ct.status_code == 200
    assert ct.json()["version"] == "v2"
    assert "Responsable: Marcos Mata García (Fulkro)" in ct.json()["text"]
    # FIX P4-2a · contacto canónico público (no el buzón admin/login)
    assert "marcosmata@fulkro.es" in ct.json()["text"]

    # 2. Gate: sin consentimiento registrado → 403 en next-question.
    nq = await async_client.get(f"{BASE}/me/next-question", headers=headers)
    assert nq.status_code == 403
    assert nq.json()["detail"] == "consent_required"

    # 2b. Gate también en /me/responses.
    rr = await async_client.post(
        f"{BASE}/me/responses",
        json={"question_id": "q1", "answer_value": {"v": "x"}},
        headers=headers,
    )
    assert rr.status_code == 403

    # 3. Registrar consentimiento (version + IP + user-agent server-side).
    rc = await async_client.post(
        f"{BASE}/me/consent", json={"consented": True}, headers=headers,
    )
    assert rc.status_code == 200, rc.text
    assert rc.json()["recorded"] is True
    assert rc.json()["version"] == "v2"

    # 4. Tras el consentimiento, el gate ya NO bloquea (403 desaparece).
    nq2 = await async_client.get(f"{BASE}/me/next-question", headers=headers)
    assert nq2.status_code != 403

    # 5. La fila quedó registrada con version + scope (append-only).
    row = (await db.execute(
        select(PreClienteDiagnosticConsent).where(
            PreClienteDiagnosticConsent.onboarding_session_id == session_id
        )
    )).scalar_one()
    assert row.consent_text_version == "v2"
    assert row.legal_basis == "interes_legitimo_art_6_1_f"
    assert row.consented is True
    assert row.user_agent is not None  # httpx envía user-agent por defecto


@pytest.mark.asyncio
async def test_consent_rejected_when_not_accepted(async_client, db):
    headers, _ = await _lead_session_headers(async_client, db)
    rc = await async_client.post(
        f"{BASE}/me/consent", json={"consented": False}, headers=headers,
    )
    assert rc.status_code == 400
    # sigue bloqueado
    nq = await async_client.get(f"{BASE}/me/next-question", headers=headers)
    assert nq.status_code == 403
