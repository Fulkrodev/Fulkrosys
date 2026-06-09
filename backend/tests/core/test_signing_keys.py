"""Tests del cargador canónico de claves de firma Ed25519 (FIX P0-1).

Prueba el contrato: env PEM primero · fichero en disco · dev genera+persiste ·
producción fail-fast (NUNCA clave efímera silenciosa que invalide firmas).
"""
from __future__ import annotations

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from backend.app.core.signing_keys import (
    SigningKeyError,
    load_signing_private_key,
)

_ENV = "FULKRO_TEST_SIGNING_KEY"


def _pem() -> str:
    key = Ed25519PrivateKey.generate()
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()


def test_loads_from_env_pem(monkeypatch, tmp_path):
    monkeypatch.setenv(_ENV, _pem())
    fp = tmp_path / "unused.pem"
    key = load_signing_private_key(env_var=_ENV, file_path=fp, label="t")
    assert isinstance(key, Ed25519PrivateKey)
    assert not fp.exists()  # viene de env · no escribe a disco


def test_loads_from_file_when_no_env(monkeypatch, tmp_path):
    monkeypatch.delenv(_ENV, raising=False)
    fp = tmp_path / "k.pem"
    fp.write_text(_pem())
    key = load_signing_private_key(env_var=_ENV, file_path=fp, label="t")
    assert isinstance(key, Ed25519PrivateKey)


def test_dev_generates_and_persists(monkeypatch, tmp_path):
    monkeypatch.delenv(_ENV, raising=False)
    monkeypatch.setenv("FULKRO_TESTING", "1")  # camino dev/test
    fp = tmp_path / "gen.pem"
    key = load_signing_private_key(env_var=_ENV, file_path=fp, label="t")
    assert isinstance(key, Ed25519PrivateKey)
    assert fp.exists()


def test_production_fail_fast_when_missing(monkeypatch, tmp_path):
    monkeypatch.delenv(_ENV, raising=False)
    monkeypatch.delenv("FULKRO_TESTING", raising=False)
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(SigningKeyError):
        load_signing_private_key(
            env_var=_ENV, file_path=tmp_path / "missing.pem", label="t",
        )


def test_env_pem_invalid_raises(monkeypatch, tmp_path):
    monkeypatch.setenv(_ENV, "no-soy-un-pem")
    with pytest.raises(Exception):  # noqa: B017 — load_pem_private_key levanta
        load_signing_private_key(
            env_var=_ENV, file_path=tmp_path / "x.pem", label="t",
        )
