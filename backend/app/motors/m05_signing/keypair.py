"""Ed25519 keypair · process-level · M05 in-portal signing.

Pattern alineado con m07_evidence/signing.py: keypair persiste en
``var/keys/m05_signing_dev.ed25519.pem`` (auto-create dev) o cargado vía
env var ``M05_SIGNING_PRIVATE_KEY_PATH`` (production).

NOTA: para v5 NO se usan keypairs per-project. document_hash_sha256 +
intent_payload (con project_id + signed_at + signed_by_user_id) bind la
firma a contexto específico. Futura mejora MB-7+: keypairs encrypted
per-project en admin_secrets con rotación.
"""
from __future__ import annotations

import os
import threading
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


_REPO_ROOT = Path(__file__).resolve().parents[4].parent
_KEYS_DIR = _REPO_ROOT / "var" / "keys"
_DEFAULT_PRIV_PATH = _KEYS_DIR / "m05_signing_dev.ed25519.pem"
_DEFAULT_PUB_PATH = _KEYS_DIR / "m05_signing_dev.ed25519.pub.pem"

_lock = threading.Lock()
_private_key: Ed25519PrivateKey | None = None
_public_key: Ed25519PublicKey | None = None


def _key_path_private() -> Path:
    env = os.environ.get("M05_SIGNING_PRIVATE_KEY_PATH")
    return Path(env) if env else _DEFAULT_PRIV_PATH


def _key_path_public() -> Path:
    env = os.environ.get("M05_SIGNING_PUB_KEY_PATH")
    return Path(env) if env else _DEFAULT_PUB_PATH


def _write_keypair(private_key: Ed25519PrivateKey) -> None:
    """Persist keypair to disk."""
    _KEYS_DIR.mkdir(parents=True, exist_ok=True)
    priv_path = _key_path_private()
    pub_path = _key_path_public()

    priv_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    priv_path.write_bytes(priv_pem)
    priv_path.chmod(0o600)

    pub_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    pub_path.write_bytes(pub_pem)


def load_or_generate_keypair() -> tuple[Ed25519PrivateKey, Ed25519PublicKey]:
    """Carga el keypair de firma in-portal M05 (cacheado module-level).

    FIX P0-1: en producción la clave viene de env
    (``FULKRO_M05_SIGNING_PRIVATE_KEY``) vía el cargador canónico; en dev se
    genera/persiste en disco. Ya NO se genera una clave efímera silenciosa en
    producción (una rotación por-recreate invalidaría la verificación de toda
    firma previa · ver ``backend/app/core/signing_keys.py``).
    """
    global _private_key, _public_key
    with _lock:
        if _private_key is not None and _public_key is not None:
            return _private_key, _public_key

        from backend.app.core.signing_keys import load_signing_private_key

        _private_key = load_signing_private_key(
            env_var="FULKRO_M05_SIGNING_PRIVATE_KEY",
            file_path=_key_path_private(),
            label="M05 in-portal signing",
        )
        _public_key = _private_key.public_key()
        return _private_key, _public_key


def sign_payload(payload: bytes) -> bytes:
    """Sign payload · returns 64-byte Ed25519 signature."""
    priv, _ = load_or_generate_keypair()
    return priv.sign(payload)


def verify_signature(payload: bytes, signature: bytes) -> bool:
    """Verify signature · True if valid."""
    _, pub = load_or_generate_keypair()
    try:
        pub.verify(signature, payload)
        return True
    except InvalidSignature:
        return False


def get_public_key_bytes() -> bytes:
    """Return raw public key bytes (32 bytes)."""
    _, pub = load_or_generate_keypair()
    return pub.public_bytes_raw()


def get_public_key_pem() -> str:
    """Return public key PEM (audit trails + verifier UI)."""
    _, pub = load_or_generate_keypair()
    pem_bytes = pub.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return pem_bytes.decode("utf-8")


def reset_cache_for_tests() -> None:
    """Clear cached keys (test isolation)."""
    global _private_key, _public_key
    with _lock:
        _private_key = None
        _public_key = None
