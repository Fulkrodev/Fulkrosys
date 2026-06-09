"""Tests master_key Fernet derivation + rotation (SAN-B.MB-3.ter.4).

Cubre:
- FULKRO_MASTER_ENCRYPTION_KEY env explicit
- Dev fallback derived from FULKRO_AUTH_PRIVATE_KEY
- Missing both → RuntimeError clear
- Key rotation history (MultiFernet primary + historical decrypt)
- Cache reset entre tests
"""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet

from backend.app.core.encryption.master_key import (
    get_master_fernet,
    reset_master_fernet_cache,
)


@pytest.fixture(autouse=True)
def _reset_cache_each_test():
    reset_master_fernet_cache()
    yield
    reset_master_fernet_cache()


def test_master_key_from_env_explicit():
    """FULKRO_MASTER_ENCRYPTION_KEY set → uses primary explicit."""
    key = Fernet.generate_key().decode("ascii")
    with patch.dict(os.environ, {"FULKRO_MASTER_ENCRYPTION_KEY": key}, clear=False):
        fernet = get_master_fernet()
    payload = fernet.encrypt(b"hello").decode("ascii")
    assert payload.startswith("gAAAAA")
    assert fernet.decrypt(payload.encode("ascii")) == b"hello"


def test_master_key_dev_fallback_from_auth_seed():
    """Sin master key, deriva de FULKRO_AUTH_PRIVATE_KEY (dev fallback)."""
    seed = "this-is-a-deterministic-test-seed-value-with-min-16-chars"
    env = {"FULKRO_AUTH_PRIVATE_KEY": seed}
    # Asegurar master no está set
    env["FULKRO_MASTER_ENCRYPTION_KEY"] = ""
    with patch.dict(os.environ, env, clear=False):
        fernet1 = get_master_fernet()
    payload = fernet1.encrypt(b"data").decode("ascii")

    # Re-derivar (mismo seed = misma key, decifra)
    reset_master_fernet_cache()
    with patch.dict(os.environ, env, clear=False):
        fernet2 = get_master_fernet()
    assert fernet2.decrypt(payload.encode("ascii")) == b"data"


def test_master_key_missing_both_raises():
    """Sin master ni auth seed → RuntimeError actionable."""
    env = {
        "FULKRO_MASTER_ENCRYPTION_KEY": "",
        "FULKRO_AUTH_PRIVATE_KEY": "",
    }
    with patch.dict(os.environ, env, clear=False):
        with pytest.raises(RuntimeError, match="master key unavailable"):
            get_master_fernet()


def test_master_key_short_auth_seed_raises():
    """Auth seed < 16 chars no es suficiente entropy → RuntimeError."""
    env = {
        "FULKRO_MASTER_ENCRYPTION_KEY": "",
        "FULKRO_AUTH_PRIVATE_KEY": "short",
    }
    with patch.dict(os.environ, env, clear=False):
        with pytest.raises(RuntimeError, match="master key unavailable"):
            get_master_fernet()


def test_key_rotation_history_decrypts_old_ciphertext():
    """MultiFernet permite decifrar texto cifrado con key antigua."""
    old_key = Fernet.generate_key().decode("ascii")
    new_key = Fernet.generate_key().decode("ascii")

    # Encriptar con old key
    old_fernet = Fernet(old_key.encode("ascii"))
    old_ciphertext = old_fernet.encrypt(b"legacy-data").decode("ascii")

    # Configurar new como primary, old en history
    env = {
        "FULKRO_MASTER_ENCRYPTION_KEY": new_key,
        "FULKRO_KEY_ROTATION_HISTORY": old_key,
    }
    with patch.dict(os.environ, env, clear=False):
        fernet = get_master_fernet()

    # MultiFernet decrypts old ciphertext
    assert fernet.decrypt(old_ciphertext.encode("ascii")) == b"legacy-data"

    # Pero encrypts con new primary key
    new_ct = fernet.encrypt(b"new-data").decode("ascii")
    new_only_fernet = Fernet(new_key.encode("ascii"))
    assert new_only_fernet.decrypt(new_ct.encode("ascii")) == b"new-data"


def test_key_rotation_invalid_history_skipped():
    """Líneas inválidas en history no rompen · skip + warn."""
    primary = Fernet.generate_key().decode("ascii")
    env = {
        "FULKRO_MASTER_ENCRYPTION_KEY": primary,
        "FULKRO_KEY_ROTATION_HISTORY": "not-a-valid-fernet-key\n\n",
    }
    with patch.dict(os.environ, env, clear=False):
        fernet = get_master_fernet()  # No crash
    payload = fernet.encrypt(b"x").decode("ascii")
    assert fernet.decrypt(payload.encode("ascii")) == b"x"
