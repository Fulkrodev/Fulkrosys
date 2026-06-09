"""Tests for Motor 7 Ed25519 signing module."""
import pytest

from backend.app.motors.m07_evidence.signing import (
    load_or_generate_keypair,
    sign_payload,
    verify_signature,
    get_public_key_pem,
    reset_cache_for_tests,
)


@pytest.fixture(autouse=True)
def _clean_keys(tmp_path, monkeypatch):
    """Redirect key storage to tmp_path and clear cache between tests."""
    import backend.app.motors.m07_evidence.signing as mod

    test_keys = tmp_path / "keys"
    test_keys.mkdir()
    monkeypatch.setattr(mod, "_KEYS_DIR", test_keys)
    monkeypatch.setattr(mod, "_PRIVATE_KEY_PATH", test_keys / "ed25519_signing_private.pem")
    monkeypatch.setattr(mod, "_PUBLIC_KEY_PATH", test_keys / "ed25519_signing_private.pub.pem")
    reset_cache_for_tests()
    yield
    reset_cache_for_tests()


class TestKeypairGeneration:

    def test_generates_keypair_when_none_exists(self):
        priv, pub = load_or_generate_keypair()
        assert priv is not None
        assert pub is not None

    def test_loads_existing_keypair_from_disk(self):
        priv1, pub1 = load_or_generate_keypair()
        # Clear cache but keep files
        reset_cache_for_tests()
        priv2, pub2 = load_or_generate_keypair()
        # Should load same key from disk
        pem1 = pub1.public_bytes(
            encoding=__import__("cryptography").hazmat.primitives.serialization.Encoding.PEM,
            format=__import__("cryptography").hazmat.primitives.serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        pem2 = pub2.public_bytes(
            encoding=__import__("cryptography").hazmat.primitives.serialization.Encoding.PEM,
            format=__import__("cryptography").hazmat.primitives.serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        assert pem1 == pem2


class TestSignAndVerify:

    def test_sign_verify_roundtrip(self):
        payload = b"test payload for signing"
        sig = sign_payload(payload)
        assert len(sig) == 64
        assert verify_signature(payload, sig) is True

    def test_verify_fails_with_wrong_payload(self):
        payload = b"original payload"
        sig = sign_payload(payload)
        assert verify_signature(b"different payload", sig) is False

    def test_verify_fails_with_wrong_signature(self):
        payload = b"some payload"
        wrong_sig = b"\x00" * 64
        assert verify_signature(payload, wrong_sig) is False

    def test_deterministic_signatures(self):
        """Ed25519 signatures are deterministic for same key+payload."""
        payload = b"deterministic test"
        sig1 = sign_payload(payload)
        sig2 = sign_payload(payload)
        assert sig1 == sig2


class TestPublicKeyPEM:

    def test_public_key_pem_format(self):
        pem = get_public_key_pem()
        assert pem.startswith("-----BEGIN PUBLIC KEY-----")
        assert pem.strip().endswith("-----END PUBLIC KEY-----")
        assert isinstance(pem, str)
