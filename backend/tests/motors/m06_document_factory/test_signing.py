"""Tests for Motor 6 signing module."""
import pytest

from backend.app.motors.m06_document_factory.signing import (
    hash_sha256,
    sign_bytes,
    verify_bytes,
    sign_document,
    _key_path_private,
    _key_path_public,
    _load_private_key,
)
from backend.app.motors.m06_document_factory.exceptions import SigningError


class TestHashing:

    def test_hash_sha256_deterministic(self):
        h1 = hash_sha256(b"hello world")
        h2 = hash_sha256(b"hello world")
        assert h1 == h2
        assert len(h1) == 64

    def test_hash_changes_with_content(self):
        h1 = hash_sha256(b"content A")
        h2 = hash_sha256(b"content B")
        assert h1 != h2

    def test_hash_sha256_empty_bytes(self):
        h = hash_sha256(b"")
        assert len(h) == 64
        assert isinstance(h, str)

    def test_hash_sha256_is_hex(self):
        h = hash_sha256(b"test")
        assert all(c in "0123456789abcdef" for c in h)


class TestSigning:

    def test_sign_and_verify_roundtrip(self):
        data = b"test data to sign"
        sig = sign_bytes(data)
        assert isinstance(sig, bytes)
        assert len(sig) == 64
        assert verify_bytes(data, sig) is True

    def test_verify_wrong_signature_returns_false(self):
        data = b"test data"
        sig = sign_bytes(data)
        assert verify_bytes(b"wrong data", sig) is False

    def test_verify_tampered_signature_returns_false(self):
        data = b"test data"
        sig = bytearray(sign_bytes(data))
        sig[0] = (sig[0] + 1) % 256  # Flip one byte
        assert verify_bytes(data, bytes(sig)) is False

    def test_signature_different_per_content(self):
        sig1 = sign_bytes(b"content 1")
        sig2 = sign_bytes(b"content 2")
        assert sig1 != sig2

    def test_sign_document_from_file(self, tmp_path):
        docx = tmp_path / "test.docx"
        docx.write_bytes(b"fake docx content for testing")
        h, sig = sign_document(docx)
        assert len(h) == 64
        assert len(sig) > 0

    def test_sign_document_nonexistent_raises(self, tmp_path):
        with pytest.raises(SigningError, match="Document not found"):
            sign_document(tmp_path / "missing.docx")


class TestKeyPaths:

    def test_key_path_private_default(self):
        path = _key_path_private()
        assert "m6_signing_dev.ed25519.pem" in str(path)

    def test_key_path_private_from_env(self, monkeypatch):
        monkeypatch.setenv("M6_SIGNING_KEY_PATH", "/custom/path.pem")
        path = _key_path_private()
        assert str(path) == "/custom/path.pem"

    def test_key_path_public_from_env(self, monkeypatch):
        monkeypatch.setenv("M6_SIGNING_PUB_KEY_PATH", "/custom/pub.pem")
        path = _key_path_public()
        assert str(path) == "/custom/pub.pem"

    def test_load_private_key_missing_raises_in_production(self, monkeypatch, tmp_path):
        # FIX P0-1: en producción una clave de firma ausente DEBE fallar fast (no
        # autogenerar: una clave efímera por-recreate invalidaría la verificación
        # de toda firma previa). En dev se genera (ver test siguiente).
        monkeypatch.setenv("M6_SIGNING_KEY_PATH", str(tmp_path / "missing.pem"))
        monkeypatch.delenv("FULKRO_M06_SIGNING_PRIVATE_KEY", raising=False)
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.delenv("FULKRO_TESTING", raising=False)
        with pytest.raises(SigningError):
            _load_private_key()

    def test_load_private_key_missing_generates_in_dev(self, monkeypatch, tmp_path):
        # En dev/test una clave ausente se genera + persiste (reproducible · no
        # secreto). Antes m06 crasheaba; ahora solo producción fail-fast.
        path = tmp_path / "generated.pem"
        monkeypatch.setenv("M6_SIGNING_KEY_PATH", str(path))
        monkeypatch.delenv("FULKRO_M06_SIGNING_PRIVATE_KEY", raising=False)
        key = _load_private_key()
        assert key is not None
        assert path.exists()

    def test_load_private_key_success(self):
        """Default key exists and loads correctly."""
        key = _load_private_key()
        assert key is not None
