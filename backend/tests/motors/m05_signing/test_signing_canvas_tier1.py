"""Tests M05 in-portal signing · TIER 1 canvas path · Ejecutable 7.7.

Cubre:
1. test_sign_canvas_dda_no_otp_required_tier1_bypass
2. test_sign_canvas_persists_image_name_surname_columns
3. test_sign_canvas_ed25519_signature_verifiable
4. test_sign_canvas_hash_chain_link_correct
5. test_sign_canvas_blocked_if_intent_expired
6. test_sign_canvas_blocked_if_already_signed
7. test_sign_canvas_message_includes_canvas_sha256_and_tier
8. test_verify_intent_signature_returns_valid_for_canvas_signed
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from sqlalchemy import select, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m05_signing.exceptions import (
    IntentExpiredError,
    InvalidIntentStateError,
)
from backend.app.motors.m05_signing.models import SigningEvent
from backend.app.motors.m05_signing.service import SigningService
from backend.tests.conftest import setup_test_project


_FAKE_CANVAS_DATAURL = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
)


def _doc_hash(content: str = "canvas-doc") -> str:
    return hashlib.sha256(content.encode()).hexdigest()


async def _create_user_id(db: AsyncSession, client_id: str) -> uuid.UUID:
    user_id = uuid.uuid4()
    await db.execute(
        sa_text(
            "INSERT INTO client_users "
            "(id, client_id, email, password_hash, created_at) "
            "VALUES (:uid, :cid, :email, 'x', now())"
        ),
        {
            "uid": str(user_id),
            "cid": client_id,
            "email": f"u{user_id.hex[:6]}@test.es",
        },
    )
    await db.flush()
    return user_id


@pytest.mark.asyncio
async def test_sign_canvas_dda_no_otp_required_tier1_bypass(db: AsyncSession):
    """TIER 1 canvas · dda (REQUIRES_STEP_UP_OTP) firma sin OTP gate (canvas path bypassa)."""
    client_id, project_id = await setup_test_project(db)
    user_id = await _create_user_id(db, client_id)
    svc = SigningService(db)

    intent = await svc.create_intent(
        project_id=uuid.UUID(project_id),
        signable_type="dda",
        document_hash_sha256=_doc_hash(),
        created_by_user_id=user_id,
    )
    # Intent starts otp_required pero TIER 1 canvas path no requiere OTP gate
    assert intent.status == "otp_required"

    event = await svc.sign_canvas(
        intent_id=intent.id,
        user_id=user_id,
        signature_canvas_dataurl=_FAKE_CANVAS_DATAURL,
        signed_name="Juan",
        signed_surname="Pérez García",
        ip_address="10.0.0.5",
    )

    await db.refresh(intent)
    assert intent.status == "signed"
    assert event.event_type == "signature_generated"
    assert event.signature_ed25519 is not None


@pytest.mark.asyncio
async def test_sign_canvas_persists_image_name_surname_columns(db: AsyncSession):
    """signing_events row stores canvas_dataurl + signed_name + signed_surname columns."""
    client_id, project_id = await setup_test_project(db)
    user_id = await _create_user_id(db, client_id)
    svc = SigningService(db)

    intent = await svc.create_intent(
        project_id=uuid.UUID(project_id),
        signable_type="policy_approval",
        document_hash_sha256=_doc_hash("policy"),
        created_by_user_id=user_id,
    )
    event = await svc.sign_canvas(
        intent_id=intent.id,
        user_id=user_id,
        signature_canvas_dataurl=_FAKE_CANVAS_DATAURL,
        signed_name="María",
        signed_surname="Martínez Núñez",
    )

    row = (await db.execute(
        select(SigningEvent).where(SigningEvent.id == event.id)
    )).scalar_one()
    assert row.signature_canvas_dataurl == _FAKE_CANVAS_DATAURL
    assert row.signed_name == "María"
    assert row.signed_surname == "Martínez Núñez"


@pytest.mark.asyncio
async def test_sign_canvas_ed25519_signature_verifiable(db: AsyncSession):
    """Ed25519 signature verify correctly with stored public key + message bytes."""
    client_id, project_id = await setup_test_project(db)
    user_id = await _create_user_id(db, client_id)
    svc = SigningService(db)

    intent = await svc.create_intent(
        project_id=uuid.UUID(project_id),
        signable_type="acta_comite",
        document_hash_sha256=_doc_hash(),
        created_by_user_id=user_id,
    )
    event = await svc.sign_canvas(
        intent_id=intent.id,
        user_id=user_id,
        signature_canvas_dataurl=_FAKE_CANVAS_DATAURL,
        signed_name="Carlos",
        signed_surname="López",
    )

    pubkey = Ed25519PublicKey.from_public_bytes(event.signature_public_key)
    # Verify · raises InvalidSignature si tampered
    pubkey.verify(
        event.signature_ed25519,
        event.signature_message.encode("utf-8"),
    )


@pytest.mark.asyncio
async def test_sign_canvas_hash_chain_link_correct(db: AsyncSession):
    """Hash chain link · 2nd canvas signature has previous_signature_hash = SHA256(prev signature)."""
    client_id, project_id = await setup_test_project(db)
    user_id = await _create_user_id(db, client_id)
    svc = SigningService(db)

    intent1 = await svc.create_intent(
        project_id=uuid.UUID(project_id),
        signable_type="acta_comite",
        document_hash_sha256=_doc_hash("doc1"),
        created_by_user_id=user_id,
    )
    event1 = await svc.sign_canvas(
        intent_id=intent1.id,
        user_id=user_id,
        signature_canvas_dataurl=_FAKE_CANVAS_DATAURL,
        signed_name="A", signed_surname="B",
    )

    intent2 = await svc.create_intent(
        project_id=uuid.UUID(project_id),
        signable_type="policy_approval",
        document_hash_sha256=_doc_hash("doc2"),
        created_by_user_id=user_id,
    )
    event2 = await svc.sign_canvas(
        intent_id=intent2.id,
        user_id=user_id,
        signature_canvas_dataurl=_FAKE_CANVAS_DATAURL,
        signed_name="A", signed_surname="B",
    )

    expected_prev_hash = hashlib.sha256(event1.signature_ed25519).hexdigest()
    assert event2.previous_signature_hash == expected_prev_hash
    assert event1.previous_signature_hash is None  # first event


@pytest.mark.asyncio
async def test_sign_canvas_blocked_if_intent_expired(db: AsyncSession):
    """Intent expired raises IntentExpiredError."""
    client_id, project_id = await setup_test_project(db)
    user_id = await _create_user_id(db, client_id)
    svc = SigningService(db)

    intent = await svc.create_intent(
        project_id=uuid.UUID(project_id),
        signable_type="acta_comite",
        document_hash_sha256=_doc_hash(),
        created_by_user_id=user_id,
    )
    # Manually expire
    intent.expires_at = datetime.now(UTC) - timedelta(hours=1)
    await db.flush()

    with pytest.raises(IntentExpiredError):
        await svc.sign_canvas(
            intent_id=intent.id,
            user_id=user_id,
            signature_canvas_dataurl=_FAKE_CANVAS_DATAURL,
            signed_name="X", signed_surname="Y",
        )


@pytest.mark.asyncio
async def test_sign_canvas_blocked_if_already_signed(db: AsyncSession):
    """Second sign_canvas attempt on same intent raises InvalidIntentStateError."""
    client_id, project_id = await setup_test_project(db)
    user_id = await _create_user_id(db, client_id)
    svc = SigningService(db)

    intent = await svc.create_intent(
        project_id=uuid.UUID(project_id),
        signable_type="acta_comite",
        document_hash_sha256=_doc_hash(),
        created_by_user_id=user_id,
    )
    await svc.sign_canvas(
        intent_id=intent.id,
        user_id=user_id,
        signature_canvas_dataurl=_FAKE_CANVAS_DATAURL,
        signed_name="X", signed_surname="Y",
    )

    with pytest.raises(InvalidIntentStateError):
        await svc.sign_canvas(
            intent_id=intent.id,
            user_id=user_id,
            signature_canvas_dataurl=_FAKE_CANVAS_DATAURL,
            signed_name="X", signed_surname="Y",
        )


@pytest.mark.asyncio
async def test_sign_canvas_message_includes_canvas_sha256_and_tier(db: AsyncSession):
    """Signature message JSON includes signature_canvas_sha256 + tier=TIER_1_CANVAS."""
    import json as _json
    client_id, project_id = await setup_test_project(db)
    user_id = await _create_user_id(db, client_id)
    svc = SigningService(db)

    intent = await svc.create_intent(
        project_id=uuid.UUID(project_id),
        signable_type="acta_comite",
        document_hash_sha256=_doc_hash(),
        created_by_user_id=user_id,
    )
    event = await svc.sign_canvas(
        intent_id=intent.id,
        user_id=user_id,
        signature_canvas_dataurl=_FAKE_CANVAS_DATAURL,
        signed_name="N", signed_surname="A",
    )

    msg = _json.loads(event.signature_message)
    assert msg["tier"] == "TIER_1_CANVAS"
    assert msg["signature_canvas_sha256"] == hashlib.sha256(
        _FAKE_CANVAS_DATAURL.encode("utf-8")
    ).hexdigest()
    assert msg["signed_name"] == "N"
    assert msg["signed_surname"] == "A"


@pytest.mark.asyncio
async def test_verify_intent_signature_returns_valid_for_canvas_signed(db: AsyncSession):
    """verify_intent_signature service helper returns valid=True for properly signed canvas intent."""
    client_id, project_id = await setup_test_project(db)
    user_id = await _create_user_id(db, client_id)
    svc = SigningService(db)

    intent = await svc.create_intent(
        project_id=uuid.UUID(project_id),
        signable_type="policy_approval",
        document_hash_sha256=_doc_hash(),
        created_by_user_id=user_id,
    )
    event = await svc.sign_canvas(
        intent_id=intent.id,
        user_id=user_id,
        signature_canvas_dataurl=_FAKE_CANVAS_DATAURL,
        signed_name="V", signed_surname="W",
    )

    result = await svc.verify_intent_signature(intent.id)
    assert result["valid"] is True
    assert result["signature_verify"] == "ok"
    assert result["event_id"] == str(event.id)


@pytest.mark.asyncio
async def test_sign_canvas_endpoint_signed_payload_enriched(
    db: AsyncSession, monkeypatch,
):
    """Ola 3 #12 · el payload de signing.signed del endpoint m05 va ENRIQUECIDO
    (signer_name + signable_label + primary_actor + project_id) y PASA el filtro
    admin · el admin ve "Fulanito firmó {documento}", no "alguien firmó algo".

    Llama al endpoint REAL (sign_intent_canvas) con un Request mínimo, espiando
    _emit_signature_sse para capturar el payload construido en el endpoint.
    """
    from unittest.mock import AsyncMock

    from starlette.requests import Request

    from backend.app.core.sse_dispatcher import event_matches_audience
    from backend.app.models.client_portal import ClientUser
    from backend.app.motors.m05_signing import api as m05_api
    from backend.app.motors.m05_signing.schemas import SignCanvasRequest

    client_id, project_id = await setup_test_project(db)
    user_id = await _create_user_id(db, client_id)
    user = await db.get(ClientUser, user_id)
    intent = await SigningService(db).create_intent(
        project_id=uuid.UUID(project_id),
        signable_type="dda",
        document_hash_sha256=_doc_hash(),
        created_by_user_id=user_id,
    )

    spy = AsyncMock()
    monkeypatch.setattr(m05_api, "_emit_signature_sse", spy)

    req = Request({
        "type": "http", "method": "POST", "path": "/", "query_string": b"",
        "headers": [(b"user-agent", b"pytest")], "client": ("1.2.3.4", 0),
    })

    await m05_api.sign_intent_canvas(
        intent_id=intent.id,
        body=SignCanvasRequest(
            signature_canvas_dataurl=_FAKE_CANVAS_DATAURL,
            signed_name="Fulanito",
            signed_surname="De Tal",
        ),
        request=req,
        db=db,
        user=user,
    )

    spy.assert_awaited_once()
    kw = spy.await_args.kwargs
    assert kw["event_type"] == "signing.signed"
    payload = kw["payload"]
    assert payload["signer_name"] == "Fulanito De Tal"
    assert payload["primary_actor"] == "cliente"
    assert payload["signable_label"]  # SIGNABLE_TYPE_LABELS["dda"]
    assert payload["project_id"] == project_id
    # PASA el filtro admin → el admin lo recibe en realtime.
    assert event_matches_audience("signing.signed", "admin", payload) is True
