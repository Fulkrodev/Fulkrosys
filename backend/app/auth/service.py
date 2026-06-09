"""Auth service layer — business logic over SQLAlchemy + crypto helpers."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth import crypto, webauthn_svc
from backend.app.auth.rate_limit import LOCKOUT
from backend.app.models.auth import (
    Session,
    TOTPSecret,
    User,
    WebAuthnCredential,
)

PASSWORD_LOCKOUT_THRESHOLD = 5


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email.lower()))
    return result.scalar_one_or_none()


async def get_user(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_webauthn_credentials(
    db: AsyncSession, user_id: uuid.UUID
) -> list[WebAuthnCredential]:
    result = await db.execute(
        select(WebAuthnCredential).where(WebAuthnCredential.user_id == user_id)
    )
    return list(result.scalars().all())


async def get_totp_secret(db: AsyncSession, user_id: uuid.UUID) -> TOTPSecret | None:
    result = await db.execute(
        select(TOTPSecret).where(TOTPSecret.user_id == user_id)
    )
    return result.scalar_one_or_none()


def user_is_locked(user: User, *, now: datetime | None = None) -> bool:
    if user.locked_until is None:
        return False
    now = now or datetime.now(timezone.utc)
    return user.locked_until > now


async def register_failed_attempt(db: AsyncSession, user: User) -> None:
    user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
    if user.failed_login_attempts >= PASSWORD_LOCKOUT_THRESHOLD:
        user.locked_until = datetime.now(timezone.utc) + LOCKOUT
        user.failed_login_attempts = 0
    await db.flush()


async def register_successful_login(db: AsyncSession, user: User) -> None:
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = datetime.now(timezone.utc)
    await db.flush()


async def create_session(
    db: AsyncSession,
    *,
    user: User,
    ip_address: str | None,
    user_agent: str | None,
) -> tuple[str, str, datetime, str]:
    """Create a session row and return ``(token, csrf, expires_at, jti)``.

    El JWT incluye claims role-aware (``role``, ``is_owner``) para que
    el frontend pueda hacer role gating en AuthGuard / login redirect
    sin consultar BD. Backend NUNCA confía solo en estos claims —
    dependencies como ``require_owner`` validan contra ``user.role``
    de BD (defensa en profundidad, ver ADR-015).
    """
    csrf = crypto.generate_csrf_token()
    extra_claims = {
        "role": user.role,
        "is_owner": user.role == "owner",
    }
    token, jti, expires_at = crypto.issue_token(
        user_id=str(user.id),
        typ="session",
        csrf_token=csrf,
        extra_claims=extra_claims,
    )
    db.add(
        Session(
            user_id=user.id,
            jti=jti,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=(user_agent or "")[:500] or None,
        )
    )
    await db.flush()
    return token, csrf, expires_at, jti


async def revoke_session(db: AsyncSession, jti: str) -> bool:
    result = await db.execute(
        update(Session)
        .where(Session.jti == jti, Session.revoked_at.is_(None))
        .values(revoked_at=datetime.now(timezone.utc))
        .returning(Session.id)
    )
    return result.scalar_one_or_none() is not None


async def session_is_active(db: AsyncSession, jti: str) -> Session | None:
    result = await db.execute(select(Session).where(Session.jti == jti))
    session = result.scalar_one_or_none()
    if session is None:
        return None
    if session.revoked_at is not None:
        return None
    if session.expires_at <= datetime.now(timezone.utc):
        return None
    return session


def stored_credentials(creds: list[WebAuthnCredential]) -> list[webauthn_svc.StoredCredential]:
    return [
        webauthn_svc.StoredCredential(
            credential_id=c.credential_id,
            public_key=c.public_key,
            sign_count=c.sign_count,
        )
        for c in creds
    ]


async def upsert_webauthn_credential(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    credential_id: bytes,
    public_key: bytes,
    device_name: str | None,
) -> WebAuthnCredential:
    existing = await db.execute(
        select(WebAuthnCredential).where(
            WebAuthnCredential.credential_id == credential_id
        )
    )
    cred = existing.scalar_one_or_none()
    if cred is None:
        cred = WebAuthnCredential(
            user_id=user_id,
            credential_id=credential_id,
            public_key=public_key,
            device_name=device_name,
        )
        db.add(cred)
    else:
        cred.public_key = public_key
        if device_name:
            cred.device_name = device_name
    await db.flush()
    return cred


async def bump_sign_count(
    db: AsyncSession, credential: WebAuthnCredential, *, sign_count: int
) -> None:
    credential.sign_count = sign_count
    credential.last_used_at = datetime.now(timezone.utc)
    await db.flush()
