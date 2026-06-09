"""Tests M08 ssh_credentials_crypto · Fernet round-trip + corner cases.

Cubre SAN-B.MB-3.bis.2 (helper para Lynis SSH remote audit).
"""
from __future__ import annotations

import pytest

from backend.app.motors.m08_verification.ssh_credentials_crypto import (
    decrypt_credentials,
    encrypt_credentials,
    reset_fernet_cache,
)


def test_encrypt_decrypt_roundtrip_key_method():
    payload = {
        "host": "10.0.0.5",
        "port": 22,
        "user": "root",
        "auth_method": "key",
        "key_path_local": "/secure/path/cliente_x.pem",
    }
    enc = encrypt_credentials(payload)
    assert isinstance(enc, str)
    assert "10.0.0.5" not in enc
    assert "/secure/path" not in enc

    dec = decrypt_credentials(enc)
    assert dec == payload


def test_encrypt_decrypt_roundtrip_password_method():
    payload = {
        "host": "192.168.1.10",
        "port": 2222,
        "user": "auditor",
        "auth_method": "password",
        "password": "s3cret-NotInLogs!",
    }
    enc = encrypt_credentials(payload)
    assert "s3cret-NotInLogs" not in enc

    dec = decrypt_credentials(enc)
    assert dec == payload


def test_decrypt_invalid_token_raises():
    with pytest.raises(ValueError, match="No se puede descifrar"):
        decrypt_credentials("totally-not-a-valid-fernet-token")


def test_encrypt_produces_different_output_each_call():
    """Fernet es probabilistic: misma payload → diferente ciphertext (IV)."""
    payload = {"host": "1.2.3.4", "user": "root", "auth_method": "key",
               "key_path_local": "/p"}
    enc1 = encrypt_credentials(payload)
    enc2 = encrypt_credentials(payload)
    assert enc1 != enc2
    assert decrypt_credentials(enc1) == decrypt_credentials(enc2) == payload


def test_reset_fernet_cache_clears():
    """reset_fernet_cache permite reload tras cambio app_secret_key (test-only)."""
    payload = {"host": "h", "user": "u", "auth_method": "key", "key_path_local": "/k"}
    enc = encrypt_credentials(payload)
    reset_fernet_cache()
    # Mismo secret → debería seguir descifrando
    assert decrypt_credentials(enc) == payload
