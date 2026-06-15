"""Tests del endpoint PÚBLICO de aprobación de acta vía magic-link.

POST /api/v1/minutes-signing/approve · reemplaza el mock LegacyDocumentSignFlow.
Verifica que consume el magic-link APROBACION_ACTA y registra la firma REAL del
asistente (committee_meetings.firmas), no una firma falsa.
"""
from __future__ import annotations

import uuid
from datetime import date
from urllib.parse import parse_qs, urlparse

import pytest

from backend.app.database import set_tenant_context
from backend.app.motors.m18_communication.minutes_service import MinutesService
from backend.tests.conftest import setup_test_project

APPROVE = "/api/v1/minutes-signing/approve"


def _attendees() -> list[dict]:
    return [
        {"nombre": "Maria Perez", "cargo": "CEO",
         "organizacion": "DataForma", "email": "ceo@dataforma.es"},
        {"nombre": "Jorge Fernandez", "cargo": "CISO",
         "organizacion": "DataForma", "email": "rseg@dataforma.es"},
    ]


def _token(url: str) -> str:
    return parse_qs(urlparse(url).query)["token"][0]


async def _create_sent_acta(db, project_id: str):
    svc = MinutesService(db)
    m = await svc.create(
        project_id=uuid.UUID(project_id),
        tipo_comite="kickoff", titulo="Comite", fecha=date(2026, 4, 21),
        presidente="Maria Perez", secretario="Jorge Fernandez",
        asistentes=_attendees(),
    )
    await svc.generate_docx(m.id, cliente_razon="DataForma")
    sent = await svc.send_for_signature(
        m.id, cliente_razon="DataForma", base_url="https://app.fulkro.es",
    )
    await db.commit()  # el endpoint público usa su propia sesión → persistir
    return m, sent


@pytest.mark.asyncio
async def test_public_approve_acta_records_real_signature(async_client, db):
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(
        db, client_id=uuid.UUID(client_id), project_id=uuid.UUID(project_id),
    )
    m, sent = await _create_sent_acta(db, project_id)
    envio = sent["envios"][0]

    r = await async_client.post(APPROVE, json={
        "token": _token(envio["url"]), "otp": envio["otp"], "accepted": True,
    })
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "approved"

    # La firma quedó REALMENTE registrada (no un mock).
    status = await MinutesService(db).get_signing_status(m.id)
    assert status["firmas_recibidas"] == 1


@pytest.mark.asyncio
async def test_public_approve_acta_wrong_otp_rejected(async_client, db):
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(
        db, client_id=uuid.UUID(client_id), project_id=uuid.UUID(project_id),
    )
    _m, sent = await _create_sent_acta(db, project_id)

    r = await async_client.post(APPROVE, json={
        "token": _token(sent["envios"][0]["url"]),
        "otp": "000000", "accepted": True,
    })
    assert r.status_code == 403, r.text


@pytest.mark.asyncio
async def test_public_approve_acta_requires_acceptance(async_client, db):
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(
        db, client_id=uuid.UUID(client_id), project_id=uuid.UUID(project_id),
    )
    _m, sent = await _create_sent_acta(db, project_id)
    envio = sent["envios"][0]

    r = await async_client.post(APPROVE, json={
        "token": _token(envio["url"]), "otp": envio["otp"], "accepted": False,
    })
    assert r.status_code == 422, r.text
