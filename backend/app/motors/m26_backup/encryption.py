"""Backup encryption layer · Fernet AES-128-CBC (ADR-048 · MB-10 Atom 10.6.A).

Pattern reuse de `m16_onboarding/token_encryption.py` adaptado a operaciones
file-level (backup artifacts) vs dict-level (OAuth tokens).

Key derivation:
- Source: ``settings.backup_encryption_key`` (env var ``BACKUP_ENCRYPTION_KEY``)
- Independiente de ``app_secret_key`` (permite rotación backup key sin afectar
  tokens OAuth/PAT)
- Transitional MB-12 forward: Vault/SOPS externalization cement sostained

Key fingerprint:
- ``current_key_fingerprint()`` retorna SHA256[:16] del key crudo · stored en
  ``BackupJob.encryption_key_id`` para rotation tracking forward

ISMS commitment honored literal: "Todas las copias de seguridad se almacenarán
cifradas en reposo" (F2_2_PROCEDIMIENTOS_CRITICOS:544).
"""
from __future__ import annotations

import base64
import hashlib
from functools import lru_cache
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from backend.app.config import get_settings


class BackupEncryptionError(Exception):
    """Raised cuando encryption/decryption fails o key no configurado."""


def _raw_key() -> str:
    """Return raw BACKUP_ENCRYPTION_KEY (validates non-empty)."""
    raw = get_settings().backup_encryption_key.get_secret_value()
    if not raw or len(raw) < 16:
        raise BackupEncryptionError(
            "BACKUP_ENCRYPTION_KEY not configured or too short (>=16 chars)"
        )
    return raw


@lru_cache(maxsize=1)
def _get_fernet() -> Fernet:
    """Derive Fernet key from BACKUP_ENCRYPTION_KEY (SHA256 → base64)."""
    raw = _raw_key()
    key = base64.urlsafe_b64encode(hashlib.sha256(raw.encode("utf-8")).digest())
    return Fernet(key)


def reset_fernet_cache() -> None:
    """Clear cached Fernet (tests + key rotation)."""
    _get_fernet.cache_clear()


def current_key_fingerprint() -> str:
    """SHA256[:16] hex fingerprint del key crudo.

    Usado en ``BackupJob.encryption_key_id`` para tracking rotation forward
    sin exponer el key actual.
    """
    raw = _raw_key()
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def encrypt_bytes(payload: bytes) -> bytes:
    """Encrypt raw bytes via Fernet."""
    return _get_fernet().encrypt(payload)


def decrypt_bytes(token: bytes) -> bytes:
    """Decrypt Fernet token back to raw bytes."""
    try:
        return _get_fernet().decrypt(token)
    except InvalidToken as exc:
        raise BackupEncryptionError(
            "Invalid token o BACKUP_ENCRYPTION_KEY rotated"
        ) from exc


def encrypt_file(input_path: str | Path, output_path: str | Path) -> Path:
    """Encrypt file at ``input_path`` to ``output_path`` (.enc).

    Returns ``Path(output_path)`` para chaining caller.
    """
    src = Path(input_path)
    dst = Path(output_path)
    payload = src.read_bytes()
    dst.write_bytes(encrypt_bytes(payload))
    return dst


def decrypt_file(input_path: str | Path, output_path: str | Path) -> Path:
    """Decrypt ``.enc`` file back to plaintext output."""
    src = Path(input_path)
    dst = Path(output_path)
    token = src.read_bytes()
    dst.write_bytes(decrypt_bytes(token))
    return dst
