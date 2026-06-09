"""Tests M05 in-portal signing service · SAN-E v3.MB-5.2.

12 tests cubren:
  Intent lifecycle:
    1. test_create_intent_basic_no_otp_required
    2. test_create_intent_dda_requires_step_up_otp
    3. test_create_intent_logs_intent_created_event
  OTP step-up:
    4. test_request_otp_returns_6_digit_code
    5. test_verify_otp_correct_code_advances_state
    6. test_verify_otp_wrong_code_increments_attempts
    7. test_verify_otp_max_attempts_raises
  Sign + Ed25519:
    8. test_sign_simple_intent_generates_valid_ed25519_signature
    9. test_sign_blocks_if_otp_required_not_verified
    10. test_sign_blocks_if_intent_expired
  Hash chain:
    11. test_hash_chain_first_signature_no_previous
    12. test_hash_chain_subsequent_signatures_linked_and_verifiable
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m05_signing.exceptions import (
    IntentExpiredError,
    OtpMaxAttemptsError,
    StepUpOtpRequiredError,
)
from backend.app.motors.m05_signing.keypair import (
    get_public_key_bytes,
    reset_cache_for_tests,
)
from backend.app.motors.m05_signing.models import (
    SigningEvent,
    SigningIntent,
    SigningOtpCode,
)
from backend.app.motors.m05_signing.service import SigningService
from backend.tests.conftest import setup_test_project


def _doc_hash(content: str = "test-doc") -> str:
    return hashlib.sha256(content.encode()).hexdigest()


async def _create_user_id(db: AsyncSession, client_id: str) -> uuid.UUID:
    """Create a minimal client_user for testing · returns user_id."""
    from sqlalchemy import text as sa_text
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


# =====================================================================
# 1. Intent lifecycle
# =====================================================================


@pytest.mark.asyncio
async def test_create_intent_basic_no_otp_required(db: AsyncSession):
    """acta_comite NO requiere OTP · status=pending · requires_step_up_otp=false."""
    client_id, project_id = await setup_test_project(db)
    user_id = await _create_user_id(db, client_id)
    svc = SigningService(db)

    intent = await svc.create_intent(
        project_id=uuid.UUID(project_id),
        signable_type="acta_comite",
        document_hash_sha256=_doc_hash(),
        created_by_user_id=user_id,
    )

    assert intent.status == "pending"
    assert intent.requires_step_up_otp is False
    assert intent.signable_type == "acta_comite"


@pytest.mark.asyncio
async def test_create_intent_dda_requires_step_up_otp(db: AsyncSession):
    """dda en REQUIRES_STEP_UP_OTP · status=otp_required · requires_step_up_otp=true."""
    client_id, project_id = await setup_test_project(db)
    user_id = await _create_user_id(db, client_id)
    svc = SigningService(db)

    intent = await svc.create_intent(
        project_id=uuid.UUID(project_id),
        signable_type="dda",
        document_hash_sha256=_doc_hash("dda-content"),
        created_by_user_id=user_id,
    )

    assert intent.status == "otp_required"
    assert intent.requires_step_up_otp is True


@pytest.mark.asyncio
async def test_create_intent_logs_intent_created_event(db: AsyncSession):
    """Crear intent emite signing_events row con event_type=intent_created."""
    client_id, project_id = await setup_test_project(db)
    user_id = await _create_user_id(db, client_id)
    svc = SigningService(db)

    intent = await svc.create_intent(
        project_id=uuid.UUID(project_id),
        signable_type="policy_approval",
        document_hash_sha256=_doc_hash(),
        created_by_user_id=user_id,
    )

    events = (await db.execute(
        select(SigningEvent).where(
            SigningEvent.signing_intent_id == intent.id,
        )
    )).scalars().all()
    assert len(events) == 1
    assert events[0].event_type == "intent_created"
    assert events[0].actor_user_id == user_id


# =====================================================================
# 2. OTP step-up
# =====================================================================


@pytest.mark.asyncio
async def test_request_otp_sends_email_redacts_response(db: AsyncSession):
    """request_otp · sends email · stores sha256 hash · returns masked email NOT plain code.

    SAN-E v3.MB-5.2.bis: API response NEVER includes plain code · solo via
    email out-of-band. Service-level result object contains otp_code_plain
    para uso interno · dataclass NO se serializa via API.
    """
    client_id, project_id = await setup_test_project(db)
    user_id = await _create_user_id(db, client_id)
    svc = SigningService(db)

    intent = await svc.create_intent(
        project_id=uuid.UUID(project_id),
        signable_type="conformidad_ens",
        document_hash_sha256=_doc_hash(),
        created_by_user_id=user_id,
    )

    result = await svc.request_otp(
        intent_id=intent.id,
        user_id=user_id,
        request_ip="192.168.1.1",
    )

    # Service result · plain code disponible para tests + render email
    assert len(result.otp_code_plain) == 6
    assert result.otp_code_plain.isdigit()
    assert result.email_ok is True  # mock backend siempre ok
    # Mask correcto: u<id>@test.es → u***@test.es
    assert result.sent_to_email_masked.startswith("u")
    assert "***" in result.sent_to_email_masked
    assert result.sent_to_email_masked.endswith("@test.es")
    assert result.expires_in_seconds == 300

    # Verify hash stored en signing_otp_codes
    stored = (await db.execute(
        select(SigningOtpCode).where(
            SigningOtpCode.signing_intent_id == intent.id,
        )
    )).scalar_one()
    expected_hash = hashlib.sha256(result.otp_code_plain.encode()).hexdigest()
    assert stored.code_sha256 == expected_hash
    assert stored.attempts == 0

    # Verify audit log: event_type='otp_sent' · NO contiene plain code
    otp_sent_events = (await db.execute(
        select(SigningEvent).where(
            SigningEvent.signing_intent_id == intent.id,
            SigningEvent.event_type == "otp_sent",
        )
    )).scalars().all()
    assert len(otp_sent_events) == 1
    payload = otp_sent_events[0].event_payload
    assert "sent_to_email_masked" in payload
    assert "***" in payload["sent_to_email_masked"]
    assert "otp_code" not in payload
    assert "otp" not in payload
    assert result.otp_code_plain not in str(payload)
    assert payload["email_send_ok"] is True
    assert payload["request_ip"] == "192.168.1.1"


@pytest.mark.asyncio
async def test_verify_otp_correct_code_advances_state(db: AsyncSession):
    """OTP correcto · intent.status=otp_verified · otp consumed."""
    client_id, project_id = await setup_test_project(db)
    user_id = await _create_user_id(db, client_id)
    svc = SigningService(db)

    intent = await svc.create_intent(
        project_id=uuid.UUID(project_id),
        signable_type="dda",
        document_hash_sha256=_doc_hash(),
        created_by_user_id=user_id,
    )
    result = await svc.request_otp(intent_id=intent.id, user_id=user_id)
    valid = await svc.verify_otp(
        intent_id=intent.id, user_id=user_id, otp_code=result.otp_code_plain,
    )

    assert valid is True
    refreshed = await db.get(SigningIntent, intent.id)
    assert refreshed.status == "otp_verified"


@pytest.mark.asyncio
async def test_verify_otp_wrong_code_increments_attempts(db: AsyncSession):
    """OTP incorrecto · returns False · attempts++ · intent state unchanged."""
    client_id, project_id = await setup_test_project(db)
    user_id = await _create_user_id(db, client_id)
    svc = SigningService(db)

    intent = await svc.create_intent(
        project_id=uuid.UUID(project_id),
        signable_type="dda",
        document_hash_sha256=_doc_hash(),
        created_by_user_id=user_id,
    )
    await svc.request_otp(intent_id=intent.id, user_id=user_id)

    valid = await svc.verify_otp(
        intent_id=intent.id, user_id=user_id, otp_code="000000",
    )
    assert valid is False

    otp = (await db.execute(
        select(SigningOtpCode).where(
            SigningOtpCode.signing_intent_id == intent.id,
        )
    )).scalar_one()
    assert otp.attempts == 1
    refreshed = await db.get(SigningIntent, intent.id)
    assert refreshed.status == "otp_required"


@pytest.mark.asyncio
async def test_verify_otp_max_attempts_raises(db: AsyncSession):
    """5+ attempts wrong · raises OtpMaxAttemptsError."""
    client_id, project_id = await setup_test_project(db)
    user_id = await _create_user_id(db, client_id)
    svc = SigningService(db)

    intent = await svc.create_intent(
        project_id=uuid.UUID(project_id),
        signable_type="renewal",
        document_hash_sha256=_doc_hash(),
        created_by_user_id=user_id,
    )
    await svc.request_otp(intent_id=intent.id, user_id=user_id)

    # 5 wrong attempts
    for _ in range(5):
        await svc.verify_otp(
            intent_id=intent.id, user_id=user_id, otp_code="999999",
        )

    # 6th raises
    with pytest.raises(OtpMaxAttemptsError):
        await svc.verify_otp(
            intent_id=intent.id, user_id=user_id, otp_code="999999",
        )


# =====================================================================
# 3. Sign + Ed25519
# =====================================================================


@pytest.mark.asyncio
async def test_sign_simple_intent_generates_valid_ed25519_signature(
    db: AsyncSession,
):
    """acta_comite (no OTP) · sign genera signature Ed25519 verificable."""
    reset_cache_for_tests()
    client_id, project_id = await setup_test_project(db)
    user_id = await _create_user_id(db, client_id)
    svc = SigningService(db)

    intent = await svc.create_intent(
        project_id=uuid.UUID(project_id),
        signable_type="acta_comite",
        document_hash_sha256=_doc_hash("acta-001"),
        created_by_user_id=user_id,
    )
    event = await svc.sign(
        intent_id=intent.id,
        user_id=user_id,
        ip_address="127.0.0.1",
        user_agent="pytest",
    )

    assert event.event_type == "signature_generated"
    assert event.signature_ed25519 is not None
    assert len(event.signature_ed25519) == 64  # Ed25519 sig size
    assert event.signature_public_key == get_public_key_bytes()
    assert event.event_hash_sha256 is not None

    # Verify Ed25519 signature roundtrip
    pub = Ed25519PublicKey.from_public_bytes(event.signature_public_key)
    pub.verify(event.signature_ed25519, event.signature_message.encode())

    refreshed = await db.get(SigningIntent, intent.id)
    assert refreshed.status == "signed"


@pytest.mark.asyncio
async def test_sign_blocks_if_otp_required_not_verified(db: AsyncSession):
    """dda intent · sign sin OTP verified → StepUpOtpRequiredError."""
    client_id, project_id = await setup_test_project(db)
    user_id = await _create_user_id(db, client_id)
    svc = SigningService(db)

    intent = await svc.create_intent(
        project_id=uuid.UUID(project_id),
        signable_type="dda",
        document_hash_sha256=_doc_hash(),
        created_by_user_id=user_id,
    )
    with pytest.raises(StepUpOtpRequiredError):
        await svc.sign(intent_id=intent.id, user_id=user_id)


@pytest.mark.asyncio
async def test_sign_blocks_if_intent_expired(db: AsyncSession):
    """Intent con expires_at < now · sign raises IntentExpiredError + status=expired."""
    client_id, project_id = await setup_test_project(db)
    user_id = await _create_user_id(db, client_id)
    svc = SigningService(db)

    intent = await svc.create_intent(
        project_id=uuid.UUID(project_id),
        signable_type="acta_comite",
        document_hash_sha256=_doc_hash(),
        created_by_user_id=user_id,
    )
    # Force expire
    intent.expires_at = datetime.now(UTC) - timedelta(hours=1)
    await db.flush()

    with pytest.raises(IntentExpiredError):
        await svc.sign(intent_id=intent.id, user_id=user_id)

    refreshed = await db.get(SigningIntent, intent.id)
    assert refreshed.status == "expired"


# =====================================================================
# 4. Hash chain
# =====================================================================


@pytest.mark.asyncio
async def test_hash_chain_first_signature_no_previous(db: AsyncSession):
    """Primera firma del project · previous_signature_hash IS NULL."""
    reset_cache_for_tests()
    client_id, project_id = await setup_test_project(db)
    user_id = await _create_user_id(db, client_id)
    svc = SigningService(db)

    intent = await svc.create_intent(
        project_id=uuid.UUID(project_id),
        signable_type="acta_comite",
        document_hash_sha256=_doc_hash("first"),
        created_by_user_id=user_id,
    )
    event = await svc.sign(intent_id=intent.id, user_id=user_id)
    assert event.previous_signature_hash is None


@pytest.mark.asyncio
async def test_hash_chain_subsequent_signatures_linked_and_verifiable(
    db: AsyncSession,
):
    """3 firmas sucesivas · cada una linked al previous · chain valid."""
    reset_cache_for_tests()
    client_id, project_id = await setup_test_project(db)
    user_id = await _create_user_id(db, client_id)
    svc = SigningService(db)

    events: list[SigningEvent] = []
    for i in range(3):
        intent = await svc.create_intent(
            project_id=uuid.UUID(project_id),
            signable_type="acta_comite",
            document_hash_sha256=_doc_hash(f"chain-{i}"),
            created_by_user_id=user_id,
        )
        event = await svc.sign(intent_id=intent.id, user_id=user_id)
        events.append(event)

    assert events[0].previous_signature_hash is None
    assert events[1].previous_signature_hash == hashlib.sha256(
        events[0].signature_ed25519
    ).hexdigest()
    assert events[2].previous_signature_hash == hashlib.sha256(
        events[1].signature_ed25519
    ).hexdigest()

    # verify_chain_integrity end-to-end
    report = await svc.verify_chain_integrity(uuid.UUID(project_id))
    assert report["chain_valid"] is True
    assert report["total_signatures"] == 3
    assert report["broken_links"] == []


def test_f0_governance_signable_types_dedicated():
    """F0-3 (Ejecutable 8 Pasada 16 · F-14-07/P10-F04): E-002/E-150/E-155 tienen
    SignableType dedicado (no caen a document_generic). Gobierno FASE 0 sin OTP
    (como acta_comite). Mapeo E-code → tipo disponible para el flujo de firma."""
    from backend.app.motors.m05_signing.signable_types import (
        SIGNABLE_TYPES,
        SIGNABLE_TYPE_LABELS,
        REQUIRES_STEP_UP_OTP,
        signable_type_for_ecode,
    )
    nuevos = ("acta_nombramiento_roles", "plan_adecuacion", "documento_alcance")
    for t in nuevos:
        assert t in SIGNABLE_TYPES, f"{t} no registrado en SIGNABLE_TYPES"
        assert t in SIGNABLE_TYPE_LABELS, f"{t} sin label humano"
        assert t not in REQUIRES_STEP_UP_OTP, f"{t} gobierno FASE 0 → sin OTP (como acta_comite)"
    # Mapeo E-code → tipo dedicado (no document_generic)
    assert signable_type_for_ecode("E-002") == "acta_nombramiento_roles"
    assert signable_type_for_ecode("E-150") == "plan_adecuacion"
    assert signable_type_for_ecode("E-155") == "documento_alcance"
    assert signable_type_for_ecode("e-155") == "documento_alcance"  # case-insensitive
    assert signable_type_for_ecode("E-100") == "document_generic"     # otros → genérico
    assert signable_type_for_ecode(None) == "document_generic"
