"""Token encryption for OAuth/PAT credentials.

Uses Fernet (AES-128-CBC + HMAC-SHA256) with key derived from app_secret_key.
Tokens never stored in cleartext in DB.
"""
from __future__ import annotations

import base64
import hashlib
import json
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from backend.app.config import get_settings


@lru_cache(maxsize=1)
def _get_fernet() -> Fernet:
    """Derive Fernet key from app_secret_key."""
    secret = get_settings().app_secret_key.get_secret_value()
    if not secret or len(secret) < 16:
        raise ValueError("app_secret_key too short or not configured")
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode("utf-8")).digest())
    return Fernet(key)


def encrypt_credentials(credentials: dict) -> bytes:
    """Encrypt a credentials dict to bytes (stored in BYTEA column)."""
    payload = json.dumps(credentials, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _get_fernet().encrypt(payload)


def decrypt_credentials(encrypted: bytes) -> dict:
    """Decrypt bytes back to credentials dict."""
    try:
        payload = _get_fernet().decrypt(encrypted)
        return json.loads(payload.decode("utf-8"))
    except InvalidToken:
        raise ValueError("No se puede descifrar: token invalido o clave cambiada")


def encrypt_str(value: str) -> str:
    """Encrypt a string secret → urlsafe token str (storable en JSON)."""
    return _get_fernet().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_str(token: str) -> str:
    """Decrypt a token produced by ``encrypt_str``."""
    try:
        return _get_fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken:
        raise ValueError("No se puede descifrar: token invalido o clave cambiada")


def reset_fernet_cache() -> None:
    """For tests that change app_secret_key."""
    _get_fernet.cache_clear()
