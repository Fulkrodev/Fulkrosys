"""Tests for startup_checks · FASE 9.D · LECCIÓN-OPS-004.

Verifica que los hardening checks fallan fast con error accionable
cuando faltan claves Ed25519 o env vars críticas, y pasan silenciosos
cuando todo está en su sitio.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from backend.app.startup_checks import (
    CriticalConfigError,
    run_startup_checks,
    verify_critical_env,
    verify_ed25519_keys,
    verify_no_insecure_defaults,
)


# ─── verify_ed25519_keys ────────────────────────────────────────────


def test_verify_ed25519_keys_passes_when_all_present(tmp_path, monkeypatch):
    """Con los 4 archivos PEM presentes, no levanta excepción."""
    keys_dir = tmp_path / "var" / "keys"
    keys_dir.mkdir(parents=True)
    fakes = [
        "m6_signing_dev.ed25519.pem",
        "m6_signing_dev.ed25519.pub.pem",
        "ed25519_signing_private.pem",
        "ed25519_signing_private.pub.pem",
    ]
    for name in fakes:
        (keys_dir / name).write_text("fake-pem")

    # Reapunta los path constants del módulo a tmp_path
    import backend.app.startup_checks as sc
    monkeypatch.setattr(sc, "_M06_PRIV", keys_dir / fakes[0])
    monkeypatch.setattr(sc, "_M06_PUB", keys_dir / fakes[1])
    monkeypatch.setattr(sc, "_M07_PRIV", keys_dir / fakes[2])
    monkeypatch.setattr(sc, "_M07_PUB", keys_dir / fakes[3])

    # No raise → check OK
    verify_ed25519_keys()


def test_verify_ed25519_keys_raises_when_any_missing(tmp_path, monkeypatch):
    """FIX P0-1: en PRODUCCIÓN, si una clave de firma no es cargable (ni env ni
    fichero), verify_ed25519_keys aborta el arranque (load-probe de M05/M06/M07).
    """
    keys_dir = tmp_path / "var" / "keys"
    keys_dir.mkdir(parents=True)
    # Producción real (no test) + M05 sin clave en env + path de fichero
    # inexistente → el cargador canónico hace fail-fast → verify_ed25519_keys
    # agrega el error y aborta. Basta con que UNO de los 3 motores falle.
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("FULKRO_TESTING", raising=False)
    monkeypatch.delenv("FULKRO_M05_SIGNING_PRIVATE_KEY", raising=False)
    monkeypatch.setenv(
        "M05_SIGNING_PRIVATE_KEY_PATH", str(keys_dir / "no_existe_m05.pem"),
    )
    import backend.app.motors.m05_signing.keypair as _m05
    _m05.reset_cache_for_tests()
    try:
        with pytest.raises(CriticalConfigError) as excinfo:
            verify_ed25519_keys()
    finally:
        _m05.reset_cache_for_tests()
    assert "LECCIÓN-OPS-004" in str(excinfo.value)


# ─── verify_critical_env ────────────────────────────────────────────


def test_verify_critical_env_passes_when_set(monkeypatch):
    """Con todas las env vars críticas presentes, no levanta excepción."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    monkeypatch.setenv("FULKRO_AUTH_PRIVATE_KEY", "fake-pem-for-test")
    monkeypatch.setenv("FULKRO_ML_PRIVATE_KEY", "fake-pem-for-test")
    monkeypatch.setenv("FULKRO_BACKUP_SIGNING_KEY", "fake-pem-for-test")
    verify_critical_env()


def test_verify_critical_env_raises_when_missing(monkeypatch):
    """Sin DATABASE_URL, raise CriticalConfigError con mensaje accionable."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("FULKRO_AUTH_PRIVATE_KEY", "fake")
    monkeypatch.setenv("FULKRO_ML_PRIVATE_KEY", "fake")
    monkeypatch.setenv("FULKRO_BACKUP_SIGNING_KEY", "fake")
    with pytest.raises(CriticalConfigError) as excinfo:
        verify_critical_env()
    assert "DATABASE_URL" in str(excinfo.value)
    assert "--env-file .env" in str(excinfo.value)


def test_verify_critical_env_raises_when_auth_private_key_missing(monkeypatch):
    """Sin FULKRO_AUTH_PRIVATE_KEY, fail-fast (LECCIÓN-OPS-004)."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://t:t@localhost/t")
    monkeypatch.delenv("FULKRO_AUTH_PRIVATE_KEY", raising=False)
    monkeypatch.setenv("FULKRO_ML_PRIVATE_KEY", "fake")
    monkeypatch.setenv("FULKRO_BACKUP_SIGNING_KEY", "fake")
    with pytest.raises(CriticalConfigError) as excinfo:
        verify_critical_env()
    assert "FULKRO_AUTH_PRIVATE_KEY" in str(excinfo.value)


def test_verify_critical_env_raises_when_ml_private_key_missing(monkeypatch):
    """Sin FULKRO_ML_PRIVATE_KEY (magic links), fail-fast."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://t:t@localhost/t")
    monkeypatch.setenv("FULKRO_AUTH_PRIVATE_KEY", "fake")
    monkeypatch.delenv("FULKRO_ML_PRIVATE_KEY", raising=False)
    monkeypatch.setenv("FULKRO_BACKUP_SIGNING_KEY", "fake")
    with pytest.raises(CriticalConfigError) as excinfo:
        verify_critical_env()
    assert "FULKRO_ML_PRIVATE_KEY" in str(excinfo.value)


# ─── verify_no_insecure_defaults ────────────────────────────────────


def test_verify_no_insecure_defaults_passes_when_overridden(monkeypatch):
    """minio_secret_key custom != 'changeme' → check OK."""
    monkeypatch.setenv("FULKRO_MINIO_SECRET_KEY", "real-prod-secret-32-chars-xxxxxx")
    verify_no_insecure_defaults()


def test_verify_no_insecure_defaults_raises_when_changeme(monkeypatch):
    """minio_secret_key == 'changeme' (default config.py) → fail-fast."""
    monkeypatch.setenv("FULKRO_MINIO_SECRET_KEY", "changeme")
    with pytest.raises(CriticalConfigError) as excinfo:
        verify_no_insecure_defaults()
    assert "FULKRO_MINIO_SECRET_KEY" in str(excinfo.value)
    assert "default inseguro" in str(excinfo.value)


# ─── run_startup_checks ─────────────────────────────────────────────


def test_run_startup_checks_skipped_when_testing(monkeypatch):
    """Con FULKRO_TESTING=1, run_startup_checks devuelve sin ejecutar."""
    monkeypatch.setenv("FULKRO_TESTING", "1")
    monkeypatch.delenv("DATABASE_URL", raising=False)  # debería raise sin skip
    # No raise → skip funcionó
    run_startup_checks()


def test_run_startup_checks_executes_when_not_testing(monkeypatch):
    """Sin FULKRO_TESTING, ejecuta y respeta verify_critical_env."""
    monkeypatch.setenv("FULKRO_TESTING", "0")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("FULKRO_AUTH_PRIVATE_KEY", "fake")
    monkeypatch.setenv("FULKRO_ML_PRIVATE_KEY", "fake")
    monkeypatch.setenv("FULKRO_BACKUP_SIGNING_KEY", "fake")
    with pytest.raises(CriticalConfigError):
        run_startup_checks()
