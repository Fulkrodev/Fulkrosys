"""MFA cliente por CÓDIGO AL EMAIL (2026-06-09 · sustituye TOTP).

Cubre: issue_email_code (genera+almacena hash+caducidad), verify_email_code
(éxito consume · fallo incrementa intentos · caducado · max intentos),
confirm_email_enrollment (activa method='email'), y el dispatch de
verify_login_code según mfa_method.

Sin SMTP en test → el envío de email es best-effort; se stubea a no-op para
aislar la lógica del código.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m21_portal_cliente import mfa_service

pytestmark = pytest.mark.real_auth


class _StubSender:
    async def send(self, *args, **kwargs):
        return None


@pytest.fixture(autouse=True)
def _stub_email(monkeypatch):
    monkeypatch.setattr(
        "backend.app.core.email.sender.get_email_sender",
        lambda: _StubSender(),
    )
    # Código determinista para poder verificar.
    monkeypatch.setattr(mfa_service, "_generate_email_code", lambda: "246813")


@pytest.mark.asyncio
async def test_issue_email_code_stores_hash_and_expiry(db: AsyncSession, make_client_user):
    user = await make_client_user(email="mfa-email-1@example.com")
    await mfa_service.issue_email_code(db, user)
    assert user.mfa_email_code_hash == mfa_service._hash_email_code("246813")
    assert user.mfa_email_code_expires_at is not None
    assert user.mfa_email_code_attempts == 0
    assert user.mfa_email_code_sent_at is not None
    # NUNCA se guarda en claro.
    assert user.mfa_email_code_hash != "246813"


@pytest.mark.asyncio
async def test_verify_email_code_success_consumes(db: AsyncSession, make_client_user):
    user = await make_client_user(email="mfa-email-2@example.com")
    await mfa_service.issue_email_code(db, user)
    ok = await mfa_service.verify_email_code(db, user, "246813")
    assert ok is True
    # consumido (single-use)
    assert user.mfa_email_code_hash is None
    assert user.mfa_email_code_expires_at is None
    # segundo intento con el mismo código falla (ya consumido)
    assert await mfa_service.verify_email_code(db, user, "246813") is False


@pytest.mark.asyncio
async def test_verify_email_code_wrong_increments_attempts(db: AsyncSession, make_client_user):
    user = await make_client_user(email="mfa-email-3@example.com")
    await mfa_service.issue_email_code(db, user)
    assert await mfa_service.verify_email_code(db, user, "000000") is False
    assert user.mfa_email_code_attempts == 1
    # el código correcto sigue funcionando tras un fallo
    assert await mfa_service.verify_email_code(db, user, "246813") is True


@pytest.mark.asyncio
async def test_verify_email_code_expired_fails(db: AsyncSession, make_client_user):
    user = await make_client_user(email="mfa-email-4@example.com")
    await mfa_service.issue_email_code(db, user)
    user.mfa_email_code_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    await db.flush()
    assert await mfa_service.verify_email_code(db, user, "246813") is False


@pytest.mark.asyncio
async def test_verify_email_code_max_attempts_locks(db: AsyncSession, make_client_user):
    user = await make_client_user(email="mfa-email-5@example.com")
    await mfa_service.issue_email_code(db, user)
    for _ in range(mfa_service.EMAIL_CODE_MAX_ATTEMPTS):
        await mfa_service.verify_email_code(db, user, "000000")
    # alcanzado el máximo · ni el código correcto entra
    assert await mfa_service.verify_email_code(db, user, "246813") is False


@pytest.mark.asyncio
async def test_confirm_email_enrollment_enables_method_email(db: AsyncSession, make_client_user):
    user = await make_client_user(email="mfa-email-6@example.com")
    await mfa_service.issue_email_code(db, user)
    ok = await mfa_service.confirm_email_enrollment(db, user, "246813")
    assert ok is True
    assert user.mfa_enabled is True
    assert user.mfa_method == "email"
    # bad code → no activa
    user2 = await make_client_user(email="mfa-email-6b@example.com")
    await mfa_service.issue_email_code(db, user2)
    assert await mfa_service.confirm_email_enrollment(db, user2, "999999") is False
    assert user2.mfa_enabled is False


@pytest.mark.asyncio
async def test_verify_login_code_dispatches_to_email(db: AsyncSession, make_client_user):
    user = await make_client_user(email="mfa-email-7@example.com")
    user.mfa_method = "email"
    await mfa_service.issue_email_code(db, user)
    # verify_login_code (el que usa el login) debe enrutar al verificador de email
    assert await mfa_service.verify_login_code(db, user, "246813") is True


@pytest.mark.asyncio
async def test_disable_email_no_code_needed(db: AsyncSession, make_client_user):
    user = await make_client_user(email="mfa-email-8@example.com")
    await mfa_service.issue_email_code(db, user)
    await mfa_service.confirm_email_enrollment(db, user, "246813")
    assert user.mfa_enabled is True
    await mfa_service.disable(db, user, "")  # email: sin código
    assert user.mfa_enabled is False


@pytest.mark.asyncio
async def test_status_email_method(db: AsyncSession, make_client_user):
    user = await make_client_user(email="mfa-email-9@example.com")
    s = await mfa_service.status(db, user)
    assert s["method"] == "email"
    assert s["mfa_enabled"] is False
    assert s["email"] == "mfa-email-9@example.com"
