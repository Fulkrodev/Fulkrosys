"""Master key Fernet · single-tenant MVP · soporta rotación.

Production: ``FULKRO_MASTER_ENCRYPTION_KEY`` env var (32-byte URL-safe
base64 key generada con ``Fernet.generate_key()``).

Dev fallback: derived deterministically from ``FULKRO_AUTH_PRIVATE_KEY``
(consistent across restarts · evita romper rows existentes en dev).

Rotación: ``FULKRO_KEY_ROTATION_HISTORY`` env (newline-separated old keys).
MultiFernet aplica primary key para encrypt y todas las keys (primary +
history) para decrypt. Rota: añadir nuevo primary, mover anterior a
history, re-encrypt rows opcionalmente vía script.

Refs: ADR-032 · SAN-B.MB-3.ter.4
"""
from __future__ import annotations

import base64
import hashlib
import logging
import os
from functools import lru_cache

from cryptography.fernet import Fernet, MultiFernet


logger = logging.getLogger(__name__)


def _derive_dev_key_from_auth_seed(seed: str) -> bytes:
    """Derive Fernet key from FULKRO_AUTH_PRIVATE_KEY seed.

    Same SHA256→base64 derivation que m16/token_encryption + m08/
    ssh_credentials_crypto · pero usando AUTH_PRIVATE_KEY (más specific
    semantically para encryption-at-rest dev).
    """
    return base64.urlsafe_b64encode(hashlib.sha256(seed.encode("utf-8")).digest())


@lru_cache(maxsize=1)
def get_master_fernet() -> MultiFernet:
    """Master Fernet for field-level encryption at rest.

    Production: requires ``FULKRO_MASTER_ENCRYPTION_KEY``.
    Dev: deriva de ``FULKRO_AUTH_PRIVATE_KEY`` si master no está set
    (warning logged · suficiente para dev/test pero no para producción
    cliente real).

    Raises:
        RuntimeError: ni master key ni auth seed disponibles.
    """
    primary_key_str = os.environ.get("FULKRO_MASTER_ENCRYPTION_KEY", "").strip()
    if primary_key_str:
        primary = Fernet(primary_key_str.encode("ascii"))
    else:
        # Dev fallback · derived deterministically from AUTH_PRIVATE_KEY
        seed = os.environ.get("FULKRO_AUTH_PRIVATE_KEY", "").strip()
        if not seed or len(seed) < 16:
            raise RuntimeError(
                "Encryption master key unavailable: set "
                "FULKRO_MASTER_ENCRYPTION_KEY (production) or "
                "FULKRO_AUTH_PRIVATE_KEY (dev fallback). Generate "
                "production key with: python -c "
                "'from cryptography.fernet import Fernet; "
                "print(Fernet.generate_key().decode())'"
            )
        logger.warning(
            "FULKRO_MASTER_ENCRYPTION_KEY not set · using dev fallback "
            "derived from FULKRO_AUTH_PRIVATE_KEY. Set explicit master "
            "key for production deployments."
        )
        primary = Fernet(_derive_dev_key_from_auth_seed(seed))

    history_raw = os.environ.get("FULKRO_KEY_ROTATION_HISTORY", "")
    historical = []
    for line in history_raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            historical.append(Fernet(line.encode("ascii")))
        except ValueError:
            logger.warning(
                "Skipping invalid Fernet key in FULKRO_KEY_ROTATION_HISTORY "
                "(must be 32-byte URL-safe base64)."
            )

    return MultiFernet([primary] + historical)


def reset_master_fernet_cache() -> None:
    """Para tests que cambian env vars en runtime."""
    get_master_fernet.cache_clear()
