"""Tests M21 Portal Cliente · auth + endpoints · single-user-RW (ADR-013 v3).

Tests adaptados post MB-3 cleanup: drop multi-role + scopes machinery.
1 usuario por cliente con acceso RW unico.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text as sa_text

from backend.app.models.client_portal import (
    ClientUser,
)
from backend.app.motors.m21_portal_cliente import auth_service
from backend.app.motors.m21_portal_cliente.auth_service import AuthError
from backend.app.motors.m21_portal_cliente.scopes import PORTAL_SCOPE
from backend.tests.conftest import _admin_setup, setup_test_project

# Sub-fase 4.D ADR-021: opt-out del autouse override (validamos auth real).
pytestmark = pytest.mark.real_auth


# ════════════════════════════════════════════════════════════════════
# Single-user-RW catalog (ADR-013 v3)
# ════════════════════════════════════════════════════════════════════

class TestPortalScope:
    def test_portal_scope_is_rw_constant(self):
        assert PORTAL_SCOPE == "rw"


# ════════════════════════════════════════════════════════════════════
# User creation + login
# ════════════════════════════════════════════════════════════════════

async def _get_datafake_client(db) -> uuid.UUID:
    """Crea cliente + project para tests."""
    _, project_id = await setup_test_project(db)
    r = await db.execute(sa_text(
        "SELECT get_project_owner(:pid)"), {"pid": project_id},
    )
    raw = r.scalar()
    return raw if isinstance(raw, uuid.UUID) else uuid.UUID(str(raw))


class TestUserCreation:
    @pytest.mark.asyncio
    async def test_create_user_generates_temp_password(self, db):
        async with _admin_setup(db):
            client_id = await _get_datafake_client(db)
            user, temp = await auth_service.create_user(
                db, client_id=client_id,
                email="test1@example.com",
                full_name="Test User",
            )
        assert user.email == "test1@example.com"
        assert user.must_change_password is True
        assert len(temp) >= 12

    @pytest.mark.asyncio
    async def test_create_user_duplicate_email_raises(self, db):
        async with _admin_setup(db):
            client_id = await _get_datafake_client(db)
            await auth_service.create_user(
                db, client_id=client_id, email="dup@ex.es",
                full_name="A",
            )
            with pytest.raises(AuthError):
                await auth_service.create_user(
                    db, client_id=client_id, email="dup@ex.es",
                    full_name="B",
                )


# ════════════════════════════════════════════════════════════════════
# Login / logout
# ════════════════════════════════════════════════════════════════════

class TestLogin:
    @pytest.mark.asyncio
    async def test_login_success_issues_jwt(self, db):
        async with _admin_setup(db):
            client_id = await _get_datafake_client(db)
            user, temp = await auth_service.create_user(
                db, client_id=client_id, email="login@ex.es",
                full_name="Login",
            )
        async with _admin_setup(db):
            u, token, _csrf, exp = await auth_service.login(
                db, "login@ex.es", temp,
            )
        assert u.id == user.id
        assert token
        assert exp > __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc,
        )

    @pytest.mark.asyncio
    async def test_login_wrong_password_raises(self, db):
        async with _admin_setup(db):
            client_id = await _get_datafake_client(db)
            await auth_service.create_user(
                db, client_id=client_id, email="bad@ex.es",
                full_name="B",
            )
            with pytest.raises(AuthError):
                await auth_service.login(db, "bad@ex.es", "wrong_pwd")

    @pytest.mark.asyncio
    async def test_login_lockout_after_5_failures(self, db):
        async with _admin_setup(db):
            client_id = await _get_datafake_client(db)
            await auth_service.create_user(
                db, client_id=client_id, email="lock@ex.es",
                full_name="L",
            )
            for _ in range(5):
                try:
                    await auth_service.login(db, "lock@ex.es", "bad")
                except AuthError:
                    pass
            with pytest.raises(AuthError, match="bloqueada|locked|invalid|invalida"):
                await auth_service.login(db, "lock@ex.es", "anything")

    @pytest.mark.asyncio
    async def test_login_unknown_email_raises(self, db):
        async with _admin_setup(db):
            with pytest.raises(AuthError):
                await auth_service.login(
                    db, "unknown@nowhere.es", "whatever",
                )

    @pytest.mark.asyncio
    async def test_logout_revokes_session(self, db):
        async with _admin_setup(db):
            client_id = await _get_datafake_client(db)
            _, temp = await auth_service.create_user(
                db, client_id=client_id, email="lout@ex.es",
                full_name="LO",
            )
            user, token, _csrf, _ = await auth_service.login(
                db, "lout@ex.es", temp,
            )
            from backend.app.auth.crypto import decode_token
            jti = decode_token(token)["jti"]
            ok = await auth_service.logout(db, jti)
        assert ok is True
        async with _admin_setup(db):
            r = await db.execute(sa_text(
                "SELECT revoked_at FROM client_sessions WHERE jwt_jti = :j"
            ), {"j": jti})
            assert r.scalar() is not None


# ════════════════════════════════════════════════════════════════════
# Password change
# ════════════════════════════════════════════════════════════════════

class TestPassword:
    @pytest.mark.asyncio
    async def test_change_password(self, db):
        async with _admin_setup(db):
            client_id = await _get_datafake_client(db)
            user, temp = await auth_service.create_user(
                db, client_id=client_id, email="chpwd@ex.es",
                full_name="CP",
            )
            await auth_service.change_password(
                db, user.id, temp, "NewP@ssword12345",
            )
            # Login con nueva
            u, token, _csrf, _ = await auth_service.login(
                db, "chpwd@ex.es", "NewP@ssword12345",
            )
        assert u.must_change_password is False

    @pytest.mark.asyncio
    async def test_change_password_wrong_old_raises(self, db):
        async with _admin_setup(db):
            client_id = await _get_datafake_client(db)
            user, temp = await auth_service.create_user(
                db, client_id=client_id, email="wrong@ex.es",
                full_name="W",
            )
            with pytest.raises(AuthError):
                await auth_service.change_password(
                    db, user.id, "wrong", "NewP@ssword12345",
                )

    @pytest.mark.asyncio
    async def test_change_password_too_short(self, db):
        async with _admin_setup(db):
            client_id = await _get_datafake_client(db)
            user, temp = await auth_service.create_user(
                db, client_id=client_id, email="short@ex.es",
                full_name="S",
            )
            with pytest.raises(AuthError):
                await auth_service.change_password(
                    db, user.id, temp, "short",
                )


# ════════════════════════════════════════════════════════════════════
# Session verification
# ════════════════════════════════════════════════════════════════════

class TestSessionVerify:
    @pytest.mark.asyncio
    async def test_verify_session_ok(self, db):
        async with _admin_setup(db):
            client_id = await _get_datafake_client(db)
            user, temp = await auth_service.create_user(
                db, client_id=client_id, email="verify@ex.es",
                full_name="V",
            )
            _, token, _csrf, _ = await auth_service.login(db, "verify@ex.es", temp)
            u, session = await auth_service.verify_session(db, token)
        assert u.id == user.id
        assert session.revoked_at is None

    @pytest.mark.asyncio
    async def test_verify_session_revoked_raises(self, db):
        async with _admin_setup(db):
            client_id = await _get_datafake_client(db)
            _, temp = await auth_service.create_user(
                db, client_id=client_id, email="rev@ex.es",
                full_name="R",
            )
            user, token, _csrf, _ = await auth_service.login(db, "rev@ex.es", temp)
            from backend.app.auth.crypto import decode_token
            jti = decode_token(token)["jti"]
            await auth_service.logout(db, jti)
            with pytest.raises(AuthError, match="revocada|Sesion"):
                await auth_service.verify_session(db, token)

    @pytest.mark.asyncio
    async def test_verify_session_bad_token_raises(self, db):
        async with _admin_setup(db):
            with pytest.raises(AuthError):
                await auth_service.verify_session(db, "not.a.jwt")


# ════════════════════════════════════════════════════════════════════
# User mgmt (reset password + deactivate + list)
# ════════════════════════════════════════════════════════════════════

class TestUserMgmt:
    @pytest.mark.asyncio
    async def test_reset_password_by_marcos(self, db):
        async with _admin_setup(db):
            client_id = await _get_datafake_client(db)
            user, temp = await auth_service.create_user(
                db, client_id=client_id, email="reset@ex.es",
                full_name="R",
            )
            new_temp = await auth_service.reset_password_by_marcos(
                db, user.id,
            )
        assert new_temp != temp
        assert len(new_temp) >= 12
        async with _admin_setup(db):
            refreshed = await db.get(ClientUser, user.id)
            assert refreshed.must_change_password is True

    @pytest.mark.asyncio
    async def test_deactivate_user_revokes_sessions(self, db):
        async with _admin_setup(db):
            client_id = await _get_datafake_client(db)
            user, temp = await auth_service.create_user(
                db, client_id=client_id, email="dea@ex.es",
                full_name="D",
            )
            _, token, _csrf, _ = await auth_service.login(db, "dea@ex.es", temp)
            await auth_service.deactivate_user(db, user.id)
            with pytest.raises(AuthError):
                await auth_service.verify_session(db, token)

    @pytest.mark.asyncio
    async def test_list_users_by_client(self, db):
        async with _admin_setup(db):
            client_id = await _get_datafake_client(db)
            await auth_service.create_user(
                db, client_id=client_id, email="u1@ex.es",
                full_name="1",
            )
            await auth_service.create_user(
                db, client_id=client_id, email="u2@ex.es",
                full_name="2",
            )
            users = await auth_service.list_users_by_client(db, client_id)
        assert len(users) >= 2


# ════════════════════════════════════════════════════════════════════
# Audit log
# ════════════════════════════════════════════════════════════════════

class TestAuditLog:
    @pytest.mark.asyncio
    async def test_login_success_logged(self, db):
        async with _admin_setup(db):
            client_id = await _get_datafake_client(db)
            _, temp = await auth_service.create_user(
                db, client_id=client_id, email="audit@ex.es",
                full_name="A",
            )
            await auth_service.login(db, "audit@ex.es", temp)
            r = await db.execute(sa_text(
                "SELECT COUNT(*) FROM client_user_audit "
                "WHERE action = 'login_success'"
            ))
            count = r.scalar() or 0
        assert count >= 1

    @pytest.mark.asyncio
    async def test_failed_login_logged(self, db):
        async with _admin_setup(db):
            client_id = await _get_datafake_client(db)
            _, _ = await auth_service.create_user(
                db, client_id=client_id, email="fail@ex.es",
                full_name="F",
            )
            try:
                await auth_service.login(db, "fail@ex.es", "wrong")
            except AuthError:
                pass
            r = await db.execute(sa_text(
                "SELECT COUNT(*) FROM client_user_audit "
                "WHERE action = 'login_failure'"
            ))
            count = r.scalar() or 0
        assert count >= 1
