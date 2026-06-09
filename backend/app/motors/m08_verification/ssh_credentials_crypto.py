"""SSH credentials encryption for M08 Lynis remote audit.

Uses Fernet (AES-128-CBC + HMAC-SHA256) with key derived from
``app_secret_key``. Credentials never stored in cleartext in DB.

Pattern replicado de ``m16_onboarding/token_encryption.py`` con dos
diferencias menores:
- Column TEXT (str) en vez de BYTEA (bytes) → encrypt retorna str URL-safe.
- Cache separado del módulo m16 (no cross-contaminación).

Refs: SAN-B.MB-3.bis.2 · cierre TODO-M8-G2
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
    """Derive Fernet key from app_secret_key (mismo derivation que m16)."""
    secret = get_settings().app_secret_key.get_secret_value()
    if not secret or len(secret) < 16:
        raise ValueError("app_secret_key too short or not configured")
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode("utf-8")).digest())
    return Fernet(key)


def encrypt_credentials(credentials: dict) -> str:
    """Encrypt a credentials dict to URL-safe base64 string (TEXT column)."""
    payload = json.dumps(credentials, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _get_fernet().encrypt(payload).decode("ascii")


def decrypt_credentials(encrypted: str) -> dict:
    """Decrypt str back to credentials dict."""
    try:
        payload = _get_fernet().decrypt(encrypted.encode("ascii"))
        return json.loads(payload.decode("utf-8"))
    except InvalidToken:
        raise ValueError("No se puede descifrar: token invalido o clave cambiada")


def reset_fernet_cache() -> None:
    """For tests that change app_secret_key."""
    _get_fernet.cache_clear()
