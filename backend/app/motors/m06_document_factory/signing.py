"""Motor 6 -- Document Factory -- Ed25519 signing module.

Loads an Ed25519 key pair from disk and provides hash/sign/verify
functions used by the service to integrity-stamp generated documents.
"""
import hashlib
import os
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives import serialization

from backend.app.motors.m06_document_factory.exceptions import SigningError

_VAR_KEYS_DIR = Path(__file__).resolve().parents[4] / "var" / "keys"
_DEFAULT_PRIV_PATH = _VAR_KEYS_DIR / "m6_signing_dev.ed25519.pem"
_DEFAULT_PUB_PATH = _VAR_KEYS_DIR / "m6_signing_dev.ed25519.pub.pem"


def _key_path_private() -> Path:
    """Resolve private key path from env or default."""
    env = os.environ.get("M6_SIGNING_KEY_PATH")
    if env:
        return Path(env)
    return _DEFAULT_PRIV_PATH


def _key_path_public() -> Path:
    """Resolve public key path from env or default."""
    env = os.environ.get("M6_SIGNING_PUB_KEY_PATH")
    if env:
        return Path(env)
    return _DEFAULT_PUB_PATH


def _load_private_key() -> Ed25519PrivateKey:
    """Carga la clave privada Ed25519 (env en prod · disco en dev).

    FIX P0-1: en producción la clave viene de ``FULKRO_M06_SIGNING_PRIVATE_KEY``
    (PEM) vía el cargador canónico; en dev se genera/persiste en disco (antes m06
    crasheaba con ``SigningError`` si faltaba el fichero, contribuyendo al
    "deploy fresco no arranca"). Ver ``backend/app/core/signing_keys.py``.
    """
    from backend.app.core.signing_keys import (
        SigningKeyError,
        load_signing_private_key,
    )
    try:
        return load_signing_private_key(
            env_var="FULKRO_M06_SIGNING_PRIVATE_KEY",
            file_path=_key_path_private(),
            label="M06 document factory signing",
        )
    except SigningKeyError as exc:
        raise SigningError(str(exc)) from exc


def _load_public_key() -> Ed25519PublicKey:
    """Load Ed25519 public key from PEM file."""
    path = _key_path_public()
    if not path.exists():
        # Fall back: derive from private key  # pragma: no cover — pub key always present
        priv = _load_private_key()
        return priv.public_key()
    try:
        pem_bytes = path.read_bytes()
        key = serialization.load_pem_public_key(pem_bytes)
        if not isinstance(key, Ed25519PublicKey):  # pragma: no cover — type guard
            raise SigningError(f"Key at {path} is not an Ed25519 public key")
        return key
    except SigningError:  # pragma: no cover — re-raise
        raise
    except Exception as exc:  # pragma: no cover — corrupt PEM file
        raise SigningError(f"Failed to load public key from {path}: {exc}") from exc


def hash_sha256(data: bytes) -> str:
    """Return hex-encoded SHA-256 hash of data."""
    return hashlib.sha256(data).hexdigest()


def sign_bytes(data: bytes) -> bytes:
    """Sign arbitrary bytes with the Ed25519 private key."""
    priv = _load_private_key()
    return priv.sign(data)


def verify_bytes(data: bytes, signature: bytes) -> bool:
    """Verify an Ed25519 signature. Returns True on valid, False on invalid."""
    pub = _load_public_key()
    try:
        pub.verify(signature, data)
        return True
    except Exception:
        return False


def sign_document(docx_path: Path) -> tuple[str, str]:
    """Hash and sign a .docx file.

    Returns (hash_hex, signature_hex).
    Raises SigningError if key is missing or signing fails.
    """
    if not docx_path.exists():
        raise SigningError(f"Document not found at {docx_path}")
    data = docx_path.read_bytes()
    h = hash_sha256(data)
    sig = sign_bytes(data)
    return h, sig.hex()
