"""Sliding-window rate limiting for login attempts.

Stored in ``auth_login_attempts`` so it is consistent across workers and
testable via a real DB fixture. Per-user lockout (``auth_users.locked_until``)
is handled separately in the service layer.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


MAX_ATTEMPTS_PER_IP = 5
WINDOW = timedelta(minutes=15)
LOCKOUT = timedelta(minutes=30)


async def count_recent_failures(
    db: AsyncSession, *, ip_address: str | None, since: datetime
) -> int:
    if not ip_address:
        return 0
    result = await db.execute(
        text(
            """
            SELECT COUNT(*) FROM auth_login_attempts
            WHERE ip_address = :ip
              AND success = false
              AND created_at >= :since
            """
        ),
        {"ip": ip_address, "since": since},
    )
    return int(result.scalar_one() or 0)


async def ip_is_rate_limited(
    db: AsyncSession, *, ip_address: str | None, now: datetime | None = None
) -> bool:
    now = now or datetime.now(timezone.utc)
    since = now - WINDOW
    count = await count_recent_failures(db, ip_address=ip_address, since=since)
    return count >= MAX_ATTEMPTS_PER_IP


async def record_attempt(
    db: AsyncSession,
    *,
    email: str | None,
    ip_address: str | None,
    user_agent: str | None,
    success: bool,
    reason: str | None = None,
) -> None:
    await db.execute(
        text(
            """
            INSERT INTO auth_login_attempts (email, ip_address, success, reason, user_agent)
            VALUES (:email, :ip, :success, :reason, :ua)
            """
        ),
        {
            "email": email,
            "ip": ip_address,
            "success": success,
            "reason": reason,
            "ua": (user_agent or "")[:500] or None,
        },
    )
