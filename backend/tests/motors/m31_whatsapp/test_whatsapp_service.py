"""Tests for WhatsAppService · opt-in + send/inbound + RGPD export · atom 8.1."""
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select, text

from backend.app.models.client_portal import ClientUser
from backend.app.motors.m31_whatsapp.dialog_360_client import Dialog360Client
from backend.app.motors.m31_whatsapp.service import (
    WhatsAppError,
    WhatsAppService,
    validate_phone_e164,
)
from backend.tests.conftest import _admin_setup


pytestmark = pytest.mark.asyncio


async def _seed_client_project_user(
    db, *, verify_wa: bool = False,
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    user_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO clients (id, nombre, cif, created_at) "
            "VALUES (:id, 'TestC', :cif, now())"
        ), {"id": str(client_id), "cif": cif})
        await db.execute(text(
            "INSERT INTO projects "
            "(id, client_id, nombre, fase, categoria_objetivo, created_at) "
            "VALUES (:id, :cid, 'TestP', 'retainer_cierre', 'MEDIA', now())"
        ), {"id": str(project_id), "cid": str(client_id)})
        await db.execute(text(
            "INSERT INTO client_users "
            "(id, client_id, email, full_name, password_hash, created_at, "
            " whatsapp_number, whatsapp_verified_at) "
            "VALUES (:id, :cid, :em, 'Test User', 'x', now(), "
            " :wa, :ver)"
        ), {
            "id": str(user_id),
            "cid": str(client_id),
            "em": f"test+{uuid.uuid4().hex[:6]}@example.com",
            "wa": "+34666555444" if verify_wa else None,
            "ver": datetime.now(timezone.utc) if verify_wa else None,
        })
    await db.execute(
        text("SELECT set_config('app.current_client_id', :v, true)"),
        {"v": str(client_id)},
    )
    await db.execute(
        text("SELECT set_config('app.current_project_id', :v, true)"),
        {"v": str(project_id)},
    )
    await db.flush()
    return client_id, project_id, user_id


def test_validate_phone_e164_es_mobile_ok():
    assert validate_phone_e164("+34 666 555 444") == "+34666555444"
    assert validate_phone_e164("666 555 444") == "+34666555444"  # default ES


def test_validate_phone_e164_invalid_raises():
    with pytest.raises(WhatsAppError):
        validate_phone_e164("nope")


async def test_initiate_opt_in_invalid_phone_returns_error(db):
    _, _, user_id = await _seed_client_project_user(db)
    svc = WhatsAppService(client=Dialog360Client(mock_mode=True))
    result = await svc.initiate_opt_in(
        db, client_user_id=user_id, phone_raw="not-a-phone",
    )
    assert result.otp_sent is False
    assert result.error is not None


async def test_initiate_opt_in_valid_phone_sends_otp(db):
    _, _, user_id = await _seed_client_project_user(db)
    svc = WhatsAppService(client=Dialog360Client(mock_mode=True))
    result = await svc.initiate_opt_in(
        db, client_user_id=user_id, phone_raw="+34666555444",
    )
    assert result.otp_sent is True
    assert result.phone_e164 == "+34666555444"
    # User has OTP stored
    user = (await db.execute(
        select(ClientUser).where(ClientUser.id == user_id)
    )).scalar_one()
    assert user.whatsapp_number == "+34666555444"
    assert user.whatsapp_verification_otp is not None
    # Se guarda el SHA-256 hex (64 chars), NUNCA el OTP de 6 dígitos en claro.
    assert len(user.whatsapp_verification_otp) == 64


async def test_verify_otp_correct_marks_verified(db, monkeypatch):
    _, _, user_id = await _seed_client_project_user(db)
    svc = WhatsAppService(client=Dialog360Client(mock_mode=True))
    # El OTP se persiste HASHEADO; fijamos uno conocido para poder verificarlo.
    import backend.app.motors.m31_whatsapp.service as wa_service
    monkeypatch.setattr(wa_service, "_generate_otp", lambda *a, **k: "123456")
    await svc.initiate_opt_in(
        db, client_user_id=user_id, phone_raw="+34666555444",
    )

    ok = await svc.verify_otp(
        db, client_user_id=user_id, otp_input="123456",
    )
    assert ok is True

    user2 = (await db.execute(
        select(ClientUser).where(ClientUser.id == user_id)
    )).scalar_one()
    assert user2.whatsapp_verified_at is not None
    assert user2.whatsapp_opt_in_at is not None
    assert user2.whatsapp_verification_otp is None  # cleared after use


async def test_verify_otp_lockout_after_max_attempts(db, monkeypatch):
    """Tras MAX_OTP_ATTEMPTS fallos el OTP queda bloqueado · ni el correcto pasa
    (anti-brute-force del espacio 10^6 dentro del TTL)."""
    _, _, user_id = await _seed_client_project_user(db)
    svc = WhatsAppService(client=Dialog360Client(mock_mode=True))
    import backend.app.motors.m31_whatsapp.service as wa_service
    monkeypatch.setattr(wa_service, "_generate_otp", lambda *a, **k: "123456")
    await svc.initiate_opt_in(
        db, client_user_id=user_id, phone_raw="+34666555444",
    )
    for _ in range(wa_service.MAX_OTP_ATTEMPTS):
        assert await svc.verify_otp(
            db, client_user_id=user_id, otp_input="000000",
        ) is False
    # 6º intento con el OTP CORRECTO sigue bloqueado.
    assert await svc.verify_otp(
        db, client_user_id=user_id, otp_input="123456",
    ) is False


async def test_verify_otp_wrong_returns_false(db):
    _, _, user_id = await _seed_client_project_user(db)
    svc = WhatsAppService(client=Dialog360Client(mock_mode=True))
    await svc.initiate_opt_in(
        db, client_user_id=user_id, phone_raw="+34666555444",
    )
    ok = await svc.verify_otp(
        db, client_user_id=user_id, otp_input="000000",
    )
    assert ok is False


async def test_send_outbound_creates_message(db):
    _, project_id, user_id = await _seed_client_project_user(
        db, verify_wa=True,
    )
    svc = WhatsAppService(client=Dialog360Client(mock_mode=True))
    thread = await svc.get_or_create_thread(
        db, project_id=project_id, client_user_id=user_id,
    )
    msg = await svc.send_outbound(
        db, thread=thread, body="Hola cliente, novedades disponibles.",
    )
    assert msg.direction == "outbound"
    assert msg.sender_type == "marcos"
    assert msg.whatsapp_message_id is not None
    assert thread.messages_count >= 1


async def test_handle_inbound_creates_message_when_verified_user(db):
    _, _, user_id = await _seed_client_project_user(db, verify_wa=True)
    svc = WhatsAppService(client=Dialog360Client(mock_mode=True))
    msg = await svc.handle_inbound(
        db, from_phone="+34666555444", body="Gracias!",
        whatsapp_message_id="wamid.IN_1",
    )
    assert msg is not None
    assert msg.direction == "inbound"
    assert msg.sender_type == "cliente"
    assert msg.content == "Gracias!"


async def test_handle_inbound_ignores_unknown_phone(db):
    await _seed_client_project_user(db, verify_wa=True)
    svc = WhatsAppService(client=Dialog360Client(mock_mode=True))
    msg = await svc.handle_inbound(
        db, from_phone="+34999000111", body="not me", whatsapp_message_id=None,
    )
    assert msg is None


async def test_export_rgpd_art15_returns_threads_and_messages(db):
    _, project_id, user_id = await _seed_client_project_user(
        db, verify_wa=True,
    )
    svc = WhatsAppService(client=Dialog360Client(mock_mode=True))
    thread = await svc.get_or_create_thread(
        db, project_id=project_id, client_user_id=user_id,
    )
    await svc.send_outbound(db, thread=thread, body="msg 1")
    await svc.send_outbound(db, thread=thread, body="msg 2")

    payload = await svc.export_rgpd_art15(db, user_id)
    assert payload.client_user_id == str(user_id)
    assert len(payload.threads) == 1
    assert len(payload.messages) >= 2
