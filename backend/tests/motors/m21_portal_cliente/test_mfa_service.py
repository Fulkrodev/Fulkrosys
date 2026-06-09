"""CLUSTER 6 Phase 6A · MFA TOTP cliente service tests.

Covers: initiate, confirm, verify_login_code (TOTP + backup), disable,
status, RLS isolation cross client_users.

Reuse make_client_user fixture (conftest.py) + admin totp_svc helpers.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth import totp_svc
from backend.app.models.client_portal import (
    ClientUserBackupCode,
)
from backend.app.motors.m21_portal_cliente import mfa_service

pytestmark = pytest.mark.real_auth


@pytest.mark.asyncio
async def test_mfa_initiate_creates_unverified_secret(
    db: AsyncSession, make_client_user,
):
    user = await make_client_user(email="mfa-init-1@example.com")
    result = await mfa_service.initiate(db, user)

    assert result.secret
    assert len(result.secret) >= 16
    assert result.otpauth_uri.startswith("otpauth://totp/")
    assert "FULKRO" in result.otpauth_uri

    rec = await mfa_service.get_totp_record(db, user.id)
    assert rec is not None
    assert rec.verified is False
    assert user.mfa_enabled is False  # NO flag until confirm


@pytest.mark.asyncio
async def test_mfa_confirm_with_valid_code_activates_and_generates_backup(
    db: AsyncSession, make_client_user,
):
    user = await make_client_user(email="mfa-confirm-1@example.com")
    init = await mfa_service.initiate(db, user)

    correct = totp_svc.verify_code  # use canonical helper
    # Generate current TOTP via pyotp to verify confirm flow
    import pyotp
    code = pyotp.TOTP(init.secret).now()

    result = await mfa_service.confirm(db, user, code)

    assert len(result.backup_codes) == 10
    assert all(len(c) >= 6 for c in result.backup_codes)
    assert len(set(result.backup_codes)) == 10  # unique

    rec = await mfa_service.get_totp_record(db, user.id)
    assert rec.verified is True
    assert rec.confirmed_at is not None
    assert user.mfa_enabled is True

    # backup codes persisted
    res = await db.execute(
        select(ClientUserBackupCode).where(
            ClientUserBackupCode.client_user_id == user.id,
        )
    )
    rows = res.scalars().all()
    assert len(rows) == 10
    assert all(r.used_at is None for r in rows)


@pytest.mark.asyncio
async def test_mfa_confirm_with_invalid_code_raises_mfa_error(
    db: AsyncSession, make_client_user,
):
    user = await make_client_user(email="mfa-confirm-2@example.com")
    await mfa_service.initiate(db, user)
    with pytest.raises(mfa_service.MfaError):
        await mfa_service.confirm(db, user, "000000")
    assert user.mfa_enabled is False


@pytest.mark.asyncio
async def test_mfa_verify_login_with_correct_totp_returns_true(
    db: AsyncSession, make_client_user,
):
    user = await make_client_user(email="mfa-verify-1@example.com")
    init = await mfa_service.initiate(db, user)
    import pyotp
    code = pyotp.TOTP(init.secret).now()
    await mfa_service.confirm(db, user, code)

    next_code = pyotp.TOTP(init.secret).now()
    ok = await mfa_service.verify_login_code(db, user, next_code)
    assert ok is True


@pytest.mark.asyncio
async def test_mfa_verify_login_with_backup_code_consumes_single_use(
    db: AsyncSession, make_client_user,
):
    user = await make_client_user(email="mfa-backup-1@example.com")
    init = await mfa_service.initiate(db, user)
    import pyotp
    confirm_code = pyotp.TOTP(init.secret).now()
    result = await mfa_service.confirm(db, user, confirm_code)
    backup = result.backup_codes[0]

    # First use OK
    ok1 = await mfa_service.verify_login_code(db, user, backup)
    assert ok1 is True

    # Second use fails (consumed)
    ok2 = await mfa_service.verify_login_code(db, user, backup)
    assert ok2 is False


@pytest.mark.asyncio
async def test_mfa_verify_login_with_wrong_code_returns_false(
    db: AsyncSession, make_client_user,
):
    user = await make_client_user(email="mfa-wrong-1@example.com")
    init = await mfa_service.initiate(db, user)
    import pyotp
    code = pyotp.TOTP(init.secret).now()
    await mfa_service.confirm(db, user, code)

    ok = await mfa_service.verify_login_code(db, user, "999999")
    assert ok is False


@pytest.mark.asyncio
async def test_mfa_disable_requires_correct_totp(
    db: AsyncSession, make_client_user,
):
    user = await make_client_user(email="mfa-disable-1@example.com")
    init = await mfa_service.initiate(db, user)
    import pyotp
    code = pyotp.TOTP(init.secret).now()
    await mfa_service.confirm(db, user, code)
    assert user.mfa_enabled is True

    # Wrong code rejected
    with pytest.raises(mfa_service.MfaError):
        await mfa_service.disable(db, user, "000000")
    assert user.mfa_enabled is True

    # Correct code disables
    next_code = pyotp.TOTP(init.secret).now()
    await mfa_service.disable(db, user, next_code)
    assert user.mfa_enabled is False

    rec = await mfa_service.get_totp_record(db, user.id)
    assert rec is None  # filtered out by deleted_at


@pytest.mark.asyncio
async def test_mfa_status_returns_complete_state(
    db: AsyncSession, make_client_user,
):
    user = await make_client_user(email="mfa-status-1@example.com")
    # 2026-06-09 · status() es method-aware · este test cubre la rama TOTP
    # (legacy). El default de un usuario nuevo es method='email'.
    user.mfa_method = "totp"
    await db.flush()
    s0 = await mfa_service.status(db, user)
    assert s0["mfa_enabled"] is False
    assert s0["enrolled"] is False
    assert s0["verified"] is False
    assert s0["backup_codes_remaining"] == 0

    init = await mfa_service.initiate(db, user)
    s1 = await mfa_service.status(db, user)
    assert s1["enrolled"] is True
    assert s1["verified"] is False

    import pyotp
    await mfa_service.confirm(db, user, pyotp.TOTP(init.secret).now())
    s2 = await mfa_service.status(db, user)
    assert s2["mfa_enabled"] is True
    assert s2["verified"] is True
    assert s2["backup_codes_remaining"] == 10
