"""Tests backup encryption layer (ADR-043 · MB-10 Atom 10.6.A)."""
from __future__ import annotations

from pathlib import Path

import pytest

from backend.app.config import get_settings
from backend.app.motors.m26_backup import encryption as enc
from backend.app.motors.m26_backup.encryption import BackupEncryptionError


@pytest.fixture(autouse=True)
def _reset_key(monkeypatch):
    """Reset settings + fernet cache between tests."""
    monkeypatch.setenv(
        "BACKUP_ENCRYPTION_KEY", "test-backup-key-32-bytes-min-length"
    )
    get_settings.cache_clear()
    enc.reset_fernet_cache()
    yield
    get_settings.cache_clear()
    enc.reset_fernet_cache()


def test_encrypt_decrypt_bytes_roundtrip():
    plaintext = b"sensitive backup payload bytes \x00\xff"
    token = enc.encrypt_bytes(plaintext)
    assert token != plaintext
    assert enc.decrypt_bytes(token) == plaintext


def test_encrypt_changes_content():
    plaintext = b"hello world"
    token1 = enc.encrypt_bytes(plaintext)
    token2 = enc.encrypt_bytes(plaintext)
    # Fernet incluye timestamp + nonce → distinto cada llamada
    assert token1 != token2
    # Pero ambos decryption return same plaintext
    assert enc.decrypt_bytes(token1) == plaintext
    assert enc.decrypt_bytes(token2) == plaintext


def test_decrypt_invalid_token_raises():
    with pytest.raises(BackupEncryptionError, match="Invalid token"):
        enc.decrypt_bytes(b"not-a-valid-fernet-token")


def test_decrypt_with_rotated_key_raises(monkeypatch):
    """Token cifrado con key A NO descifrable con key B."""
    plaintext = b"backup snapshot"
    token = enc.encrypt_bytes(plaintext)

    # Rotate key
    monkeypatch.setenv(
        "BACKUP_ENCRYPTION_KEY", "completely-different-key-32-chars"
    )
    get_settings.cache_clear()
    enc.reset_fernet_cache()

    with pytest.raises(BackupEncryptionError):
        enc.decrypt_bytes(token)


def test_key_fingerprint_stable():
    fp1 = enc.current_key_fingerprint()
    fp2 = enc.current_key_fingerprint()
    assert fp1 == fp2
    assert len(fp1) == 16
    assert all(c in "0123456789abcdef" for c in fp1)


def test_key_fingerprint_changes_on_rotation(monkeypatch):
    fp_before = enc.current_key_fingerprint()
    monkeypatch.setenv(
        "BACKUP_ENCRYPTION_KEY", "rotated-key-different-fingerprint"
    )
    get_settings.cache_clear()
    enc.reset_fernet_cache()
    fp_after = enc.current_key_fingerprint()
    assert fp_before != fp_after


def test_raw_key_too_short_raises(monkeypatch):
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", "short")
    get_settings.cache_clear()
    enc.reset_fernet_cache()
    with pytest.raises(BackupEncryptionError, match="too short"):
        enc.encrypt_bytes(b"payload")


def test_raw_key_empty_raises(monkeypatch):
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", "")
    get_settings.cache_clear()
    enc.reset_fernet_cache()
    with pytest.raises(BackupEncryptionError, match="not configured"):
        enc.encrypt_bytes(b"payload")


def test_encrypt_file_decrypt_file_roundtrip(tmp_path: Path):
    src = tmp_path / "backup.tar.gz"
    payload = b"binary backup data " * 1024  # ~20 KB
    src.write_bytes(payload)

    enc_path = tmp_path / "backup.tar.gz.enc"
    decrypted_path = tmp_path / "backup.restored.tar.gz"

    out_enc = enc.encrypt_file(src, enc_path)
    assert out_enc == enc_path
    assert enc_path.exists()
    assert enc_path.read_bytes() != payload  # encrypted differs

    out_dec = enc.decrypt_file(enc_path, decrypted_path)
    assert out_dec == decrypted_path
    assert decrypted_path.read_bytes() == payload  # roundtrip OK


def test_encrypt_file_accepts_str_path(tmp_path: Path):
    """API accepts str paths in addition to Path."""
    src = tmp_path / "data.txt"
    src.write_bytes(b"text content")
    enc_path = str(tmp_path / "data.txt.enc")
    out = enc.encrypt_file(str(src), enc_path)
    assert out.exists()
