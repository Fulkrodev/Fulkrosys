"""Ed25519 signing module for evidence integrity.

Generates or loads an Ed25519 keypair from disk (var/keys/),
signs payloads, and verifies signatures.
"""
from __future__ import annotations

import threading
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.exceptions import InvalidSignature

# Key paths: repo_root / var / keys /
_REPO_ROOT = Path(__file__).resolve().parents[3].parent
_KEYS_DIR = _REPO_ROOT / "var" / "keys"
_PRIVATE_KEY_PATH = _KEYS_DIR / "ed25519_signing_private.pem"
_PUBLIC_KEY_PATH = _KEYS_DIR / "ed25519_signing_private.pub.pem"

# In-memory cache
_lock = threading.Lock()
_private_key: Ed25519PrivateKey | None = None
_public_key: Ed25519PublicKey | None = None


def _write_keypair(private_key: Ed25519PrivateKey) -> None:
    """Persist keypair to disk."""
    _KEYS_DIR.mkdir(parents=True, exist_ok=True)

    priv_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    _PRIVATE_KEY_PATH.write_bytes(priv_pem)
    _PRIVATE_KEY_PATH.chmod(0o600)

    pub_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    _PUBLIC_KEY_PATH.write_bytes(pub_pem)


def load_or_generate_keypair() -> tuple[Ed25519PrivateKey, Ed25519PublicKey]:
    """Carga el keypair de firma de evidencias M07 (cacheado, thread-safe).

    FIX P0-1: en producción la clave viene de env
    (``FULKRO_M07_SIGNING_PRIVATE_KEY``) vía el cargador canónico; en dev se
    genera/persiste en disco. Ya NO se genera una clave efímera silenciosa en
    producción (una rotación por-recreate invalidaría la firma de toda evidencia
    previa · ver ``backend/app/core/signing_keys.py``).
    """
    global _private_key, _public_key
    with _lock:
        if _private_key is not None and _public_key is not None:
            return _private_key, _public_key

        from backend.app.core.signing_keys import load_signing_private_key

        _private_key = load_signing_private_key(
            env_var="FULKRO_M07_SIGNING_PRIVATE_KEY",
            file_path=_PRIVATE_KEY_PATH,
            label="M07 evidence signing",
        )
        _public_key = _private_key.public_key()
        return _private_key, _public_key


def sign_payload(payload: bytes) -> bytes:
    """Sign payload and return 64-byte Ed25519 signature."""
    priv, _ = load_or_generate_keypair()
    return priv.sign(payload)


def verify_signature(payload: bytes, signature: bytes) -> bool:
    """Verify a signature against payload. Returns True if valid."""
    _, pub = load_or_generate_keypair()
    try:
        pub.verify(signature, payload)
        return True
    except InvalidSignature:
        return False


def get_public_key_pem() -> str:
    """Return the public key in PEM format (for audit trails)."""
    _, pub = load_or_generate_keypair()
    pem_bytes = pub.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return pem_bytes.decode("utf-8")


def reset_cache_for_tests() -> None:
    """Clear cached keys (for test isolation)."""
    global _private_key, _public_key
    with _lock:
        _private_key = None
        _public_key = None
