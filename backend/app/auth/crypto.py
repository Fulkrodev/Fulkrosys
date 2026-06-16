"""Crypto primitives for auth: Ed25519 JWT, bcrypt passwords, CSRF tokens.

Ed25519 key pair is loaded from the env var ``FULKRO_AUTH_PRIVATE_KEY`` (PEM).
If not set, an ephemeral pair is generated at import time — tokens will be
invalidated on process restart. Production MUST set the env var.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import uuid4

import bcrypt
import jwt as pyjwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)
from loguru import logger


JWT_ALGORITHM = "EdDSA"
SESSION_TTL = timedelta(hours=8)
MFA_TICKET_TTL = timedelta(minutes=5)
REGISTRATION_TICKET_TTL = timedelta(minutes=10)

TokenType = Literal["session", "mfa_ticket", "registration_ticket"]


def _load_keys() -> tuple[bytes, bytes]:
    """Load Ed25519 key pair from env or generate ephemeral for dev."""
    env_priv = os.environ.get("FULKRO_AUTH_PRIVATE_KEY")
    if env_priv:
        private_key = serialization.load_pem_private_key(
            env_priv.encode("utf-8"), password=None
        )
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        public_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        logger.info("Auth: Ed25519 key pair loaded from FULKRO_AUTH_PRIVATE_KEY")
        return private_pem, public_pem

    from backend.app.core.signing_keys import is_production

    if is_production():
        raise RuntimeError(
            "FULKRO_AUTH_PRIVATE_KEY no definido en producción. Debe inyectarse "
            "la clave Ed25519 (PEM): sin ella las sesiones se invalidarían en cada "
            "reinicio. NUNCA se autogenera en producción (fail-fast)."
        )

    logger.warning(
        "Auth: FULKRO_AUTH_PRIVATE_KEY not set. Generating ephemeral Ed25519 key "
        "(dev/test only). Tokens will be invalidated on process restart."
    )
    private_key = Ed25519PrivateKey.generate()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_pem


_PRIVATE_PEM, _PUBLIC_PEM = _load_keys()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode(
        "utf-8"
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def constant_time_eq(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def issue_token(
    *,
    user_id: str,
    typ: TokenType,
    jti: str | None = None,
    ttl: timedelta | None = None,
    csrf_token: str | None = None,
    extra_claims: dict | None = None,
) -> tuple[str, str, datetime]:
    """Generate a signed JWT.

    ``extra_claims`` permite añadir claims aplicación-específicos al
    payload (ej. ``role``, ``is_owner`` para sessions). Los claims
    base (``sub``, ``jti``, ``typ``, ``iat``,
    ``exp``, ``csrf``) tienen prioridad y no son sobrescribibles desde
    ``extra_claims``.

    Returns ``(token, jti, expires_at)``.
    """
    if ttl is None:
        ttl = {
            "session": SESSION_TTL,
            "mfa_ticket": MFA_TICKET_TTL,
            "registration_ticket": REGISTRATION_TICKET_TTL,
        }[typ]

    now = datetime.now(timezone.utc)
    expires_at = now + ttl
    jti = jti or uuid4().hex

    payload: dict = {}
    if extra_claims:
        payload.update(extra_claims)
    # Base claims sobrescriben extra_claims si chocan.
    payload.update(
        {
            "sub": user_id,
            "jti": jti,
            "typ": typ,
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
        }
    )
    if csrf_token is not None:
        payload["csrf"] = csrf_token

    token = pyjwt.encode(payload, _PRIVATE_PEM, algorithm=JWT_ALGORITHM)
    return token, jti, expires_at


def decode_token(token: str) -> dict:
    """Verify JWT signature and decode. Raises ``pyjwt.InvalidTokenError`` on failure."""
    return pyjwt.decode(token, _PUBLIC_PEM, algorithms=[JWT_ALGORITHM])


def get_public_pem() -> bytes:
    """Accesor público de la clave pública Ed25519 (PEM) para JWKS / verificación.

    Evita que otros módulos lean el global "privado" ``_PUBLIC_PEM`` directamente
    (§4.5 tracker:390a · encapsulación).
    """
    return _PUBLIC_PEM


def hash_jti(jti: str) -> str:
    """Hash a JTI for DB storage comparisons (unused today, reserved)."""
    return hashlib.sha256(jti.encode("utf-8")).hexdigest()
