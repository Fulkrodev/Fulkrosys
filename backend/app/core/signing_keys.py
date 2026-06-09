"""Carga canónica de claves Ed25519 de firma (M05 / M06 / M07).

FIX P0-1 (auditoría 2026-06-09). En producción las claves de firma DEBEN venir
de variable de entorno (PEM completo), inyectadas UNA sola vez por
``scripts/generate-prod-secrets.sh`` — igual que ``FULKRO_AUTH_PRIVATE_KEY`` /
``FULKRO_ML_PRIVATE_KEY`` / ``FULKRO_BACKUP_SIGNING_KEY``.

Antes, los 3 motores autogeneraban su keypair en ``var/keys/`` si faltaba. En
Hetzner, sin volumen persistente para ``/app/var``, cada ``docker recreate`` del
contenedor generaba un par NUEVO → invalidaba la verificación de TODA firma
previa (contratos M05, documentos M06, dossier ENAC, evidencias M07): la
trazabilidad R6/ENAC quedaba nominal. M06 además crasheaba el arranque de firma
(no autogenera → ``SigningError``).

Política canónica de carga:
  1. env var con el PEM completo (producción · clave estable cross-recreate).
  2. fichero PEM en disco (conveniencia de dev/CI · reproducible).
  3. ni env ni fichero:
       - dev/test → generar + persistir en disco (no secreto, idempotente).
       - producción → fail-fast (SigningKeyError). NUNCA clave efímera silenciosa.
"""
from __future__ import annotations

import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


class SigningKeyError(RuntimeError):
    """Falta una clave de firma obligatoria (o es inválida) en producción."""


def is_production() -> bool:
    """True solo en producción real (NO en test runs · FULKRO_TESTING=1)."""
    if os.environ.get("FULKRO_TESTING", "").strip() in {"1", "true", "yes"}:
        return False
    return (os.environ.get("APP_ENV") or "").strip().lower() in {"production", "prod"}


def load_signing_private_key(
    *,
    env_var: str,
    file_path: Path,
    label: str,
) -> Ed25519PrivateKey:
    """Carga la clave privada Ed25519 de firma según la política canónica.

    Args:
        env_var: nombre de la env var que en producción trae el PEM completo.
        file_path: ruta del PEM en disco (dev/CI).
        label: etiqueta legible del motor para mensajes de error.
    """
    pem_env = os.environ.get(env_var)
    if pem_env:
        key = serialization.load_pem_private_key(
            pem_env.encode("utf-8"), password=None,
        )
        if not isinstance(key, Ed25519PrivateKey):
            raise SigningKeyError(
                f"{label}: {env_var} no contiene una clave Ed25519 válida",
            )
        return key

    if file_path.exists():
        key = serialization.load_pem_private_key(
            file_path.read_bytes(), password=None,
        )
        if not isinstance(key, Ed25519PrivateKey):
            raise SigningKeyError(
                f"{label}: la clave en {file_path} no es Ed25519",
            )
        return key

    if is_production():
        raise SigningKeyError(
            f"{label}: falta la clave de firma. En producción debe inyectarse "
            f"vía la env var {env_var} (PEM Ed25519). Generar con "
            f"scripts/generate-prod-secrets.sh. NUNCA se autogenera en producción "
            f"(una clave efímera por-recreate invalida la verificación de todas "
            f"las firmas previas · trazabilidad ENAC/R6).",
        )

    # Dev/test: generar + persistir (no secreto · reproducible cross-run).
    key = Ed25519PrivateKey.generate()
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(
            key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            ),
        )
        file_path.chmod(0o600)
    except OSError:
        # Filesystem read-only en algún CI: la clave en memoria sigue sirviendo
        # para este proceso (dev/test no exige persistencia cross-recreate).
        pass
    return key
