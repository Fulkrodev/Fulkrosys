"""Tests del endpoint PÚBLICO de firma de documento vía magic-link FIRMA_DOCUMENTO.

POST /api/v1/document-signing/sign · §3.1 audit-2026-06-15 · reemplaza el mock
LegacyDocumentSignFlow. Verifica que consume el magic-link FIRMA_DOCUMENTO y
registra la firma Ed25519 REAL (signing_events · hash chain R6), no una firma
falsa con setTimeout.
"""
from __future__ import annotations

import uuid
from urllib.parse import parse_qs, urlparse

import pytest

from backend.app.database import set_tenant_context
from backend.app.motors.m05_signing.service import SigningService
from backend.app.motors.m12_magic_link.purposes import MagicLinkPurpose
from backend.app.motors.m12_magic_link.schemas import MagicLinkGenerateRequest
from backend.app.motors.m12_magic_link.service import MagicLinkService
from backend.tests.conftest import setup_test_project

SIGN = "/api/v1/document-signing/sign"
_HASH = "a" * 64  # snapshot hash dummy (64-hex)


def _token(url: str) -> str:
    return parse_qs(urlparse(url).query)["token"][0]


async def _firma_documento_link(db, project_id: str, scope: dict):
    svc = MagicLinkService(db)
    resp = await svc.generate_magic_link(
        MagicLinkGenerateRequest(
            project_id=uuid.UUID(project_id),
            purpose=MagicLinkPurpose.FIRMA_DOCUMENTO,
            recipient_email="rinfo@cliente-e2e.es",
            scope=scope,
        ),
        base_url="https://app.fulkro.es",
    )
    await db.commit()  # el endpoint público usa su propia sesión → persistir
    return resp


@pytest.mark.asyncio
async def test_sign_document_records_real_ed25519(async_client, db):
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(
        db, client_id=uuid.UUID(client_id), project_id=uuid.UUID(project_id),
    )
    resp = await _firma_documento_link(db, project_id, {
        "document_type": "acta_e012",
        "categorization_id": str(uuid.uuid4()),
        "acta_snapshot_hash": _HASH,
        "recipient_name": "Responsable de la Información",
        "recipient_role": "responsable_informacion",
    })

    r = await async_client.post(SIGN, json={
        "token": _token(resp.url), "otp": resp.otp, "accepted": True,
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "signed"
    assert body["document_type"] == "acta_e012"

    # La firma quedó REALMENTE registrada (Ed25519 + hash chain R6 válida).
    report = await SigningService(db).verify_chain_integrity(uuid.UUID(project_id))
    assert report["total_signatures"] == 1
    assert report["chain_valid"] is True


@pytest.mark.asyncio
async def test_sign_document_generic_fallback(async_client, db):
    """document_type desconocido (k6 reunión) → document_generic, firma igual."""
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(
        db, client_id=uuid.UUID(client_id), project_id=uuid.UUID(project_id),
    )
    resp = await _firma_documento_link(db, project_id, {
        "meeting_id": str(uuid.uuid4()),
        "etapa_k": "K6",
        "title": "Acta de la reunión K.6",
    })

    r = await async_client.post(SIGN, json={
        "token": _token(resp.url), "otp": resp.otp, "accepted": True,
    })
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "signed"
    report = await SigningService(db).verify_chain_integrity(uuid.UUID(project_id))
    assert report["total_signatures"] == 1


@pytest.mark.asyncio
async def test_sign_document_wrong_otp_rejected(async_client, db):
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(
        db, client_id=uuid.UUID(client_id), project_id=uuid.UUID(project_id),
    )
    resp = await _firma_documento_link(db, project_id, {
        "document_type": "dda_e040_rseg", "dda_snapshot_hash": _HASH,
    })

    r = await async_client.post(SIGN, json={
        "token": _token(resp.url), "otp": "000000", "accepted": True,
    })
    assert r.status_code == 403, r.text
    # NADA firmado tras OTP incorrecto.
    report = await SigningService(db).verify_chain_integrity(uuid.UUID(project_id))
    assert report["total_signatures"] == 0


@pytest.mark.asyncio
async def test_sign_document_requires_acceptance(async_client, db):
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(
        db, client_id=uuid.UUID(client_id), project_id=uuid.UUID(project_id),
    )
    resp = await _firma_documento_link(db, project_id, {
        "document_type": "acta_e012", "acta_snapshot_hash": _HASH,
    })

    r = await async_client.post(SIGN, json={
        "token": _token(resp.url), "otp": resp.otp, "accepted": False,
    })
    assert r.status_code == 422, r.text


@pytest.mark.asyncio
async def test_sign_document_wrong_purpose_rejected(async_client, db):
    """Un magic-link que NO es FIRMA_DOCUMENTO no firma documentos (400)."""
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(
        db, client_id=uuid.UUID(client_id), project_id=uuid.UUID(project_id),
    )
    svc = MagicLinkService(db)
    resp = await svc.generate_magic_link(
        MagicLinkGenerateRequest(
            project_id=uuid.UUID(project_id),
            purpose=MagicLinkPurpose.APROBACION_PROPUESTA,
            recipient_email="cliente@e2e.es",
            scope={"propuesta_codigo": "P-E2E-001", "importe_total": "1 EUR"},
        ),
        base_url="https://app.fulkro.es",
    )
    await db.commit()

    r = await async_client.post(SIGN, json={
        "token": _token(resp.url), "otp": resp.otp, "accepted": True,
    })
    assert r.status_code in (400, 403), r.text
