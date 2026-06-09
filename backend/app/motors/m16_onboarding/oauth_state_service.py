"""OAuth state token service (SAN-E v3.MB-4.2.bis · Q2-A).

Anti-CSRF state generation + validation per OAuth flow.
Genera tokens 1-time-use con TTL de 10min · scope (client_user_id, project_id).

PKCE optional: code_verifier opcional para providers que requieren PKCE
(Microsoft 365, Azure, Google, Base custom). Stored junto al state token.
"""
from __future__ import annotations

import base64
import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.onboarding import OAuthStateToken


STATE_TOKEN_TTL_MINUTES = 10


@dataclass
class OAuthStateContext:
    """Resultado de validate_and_consume."""
    client_user_id: uuid.UUID
    project_id: uuid.UUID
    connector_type: str
    redirect_uri: str
    code_verifier: str | None


class OAuthStateError(Exception):
    """Errores en validación de state token (rejected · expired · consumed)."""


def _generate_state_token() -> str:
    """Genera state token URL-safe de 64 chars (~48 bytes entropy)."""
    return secrets.token_urlsafe(48)


def _generate_pkce_pair() -> tuple[str, str]:
    """Genera PKCE code_verifier + code_challenge (S256).

    Returns: (verifier, challenge)
    """
    verifier = secrets.token_urlsafe(64)[:128]
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


async def create_state(
    db: AsyncSession,
    *,
    client_user_id: uuid.UUID,
    project_id: uuid.UUID,
    connector_type: str,
    redirect_uri: str,
    use_pkce: bool = False,
) -> tuple[str, str | None]:
    """Crea state token y devuelve (state, code_challenge_si_pkce).

    Si use_pkce=True · genera PKCE pair · stora verifier · devuelve challenge.
    Si False · code_verifier en BD será None · no PKCE en authorize URL.
    """
    state = _generate_state_token()
    challenge: str | None = None
    verifier: str | None = None
    if use_pkce:
        verifier, challenge = _generate_pkce_pair()

    record = OAuthStateToken(
        state_token=state,
        client_user_id=client_user_id,
        project_id=project_id,
        connector_type=connector_type,
        redirect_uri=redirect_uri,
        code_verifier=verifier,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=STATE_TOKEN_TTL_MINUTES),
    )
    db.add(record)
    await db.flush()
    return state, challenge


async def validate_and_consume(
    db: AsyncSession, state: str,
) -> OAuthStateContext:
    """Valida state token: existe · no expired · no consumed. Marca consumed.

    Raises:
        OAuthStateError: si token no existe, expired, o ya consumido.
    """
    if not state:
        raise OAuthStateError("Missing state token")

    res = await db.execute(
        select(OAuthStateToken).where(OAuthStateToken.state_token == state)
    )
    record = res.scalar_one_or_none()
    if record is None:
        raise OAuthStateError("State token not found")
    if record.consumed_at is not None:
        raise OAuthStateError("State token already consumed (replay attempt)")
    now = datetime.now(timezone.utc)
    if record.expires_at < now:
        raise OAuthStateError("State token expired")

    record.consumed_at = now
    await db.flush()

    return OAuthStateContext(
        client_user_id=record.client_user_id,
        project_id=record.project_id,
        connector_type=record.connector_type,
        redirect_uri=record.redirect_uri,
        code_verifier=record.code_verifier,
    )


async def cleanup_expired(db: AsyncSession) -> int:
    """Borra tokens expirados o consumidos > 1h. Retorna count borrado.

    Útil como cron job (MB-7+ · scheduled task).
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
    res = await db.execute(
        select(OAuthStateToken).where(
            (OAuthStateToken.expires_at < datetime.now(timezone.utc))
            | (OAuthStateToken.consumed_at < cutoff)
        )
    )
    expired = list(res.scalars().all())
    for record in expired:
        await db.delete(record)
    return len(expired)
