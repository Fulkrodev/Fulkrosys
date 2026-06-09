"""Startup hardening checks · FASE 9.D · LECCIÓN-OPS-004.

Falla fast en arranque si claves criptográficas críticas o env vars
imprescindibles no están cargadas correctamente. Evita el caso (real,
documentado en LECCIÓN-OPS-004) de uvicorn dev arrancado sin
`--env-file .env` que genera keypairs efímeros y firma cookies que no
persisten entre restarts → redirect /login + 401 silenciosos en
endpoints de signing M06/M07.

Ejecuta desde `lifespan` en `backend/app/main.py`. Skip automático en
test runs (`FULKRO_TESTING=1` set por conftest) para no romper tests
unitarios que no requieren keys reales en disco.
"""
from __future__ import annotations

import os
from pathlib import Path

from loguru import logger


# Repo root via path traversal · backend/app/startup_checks.py → /home/usuario/fulkro
_REPO_ROOT = Path(__file__).resolve().parents[2]
_KEYS_DIR = _REPO_ROOT / "var" / "keys"

# Claves Ed25519 esperadas en disco (paths espejo signing.py de M06+M07).
# Si M06/M07 cambian sus paths, actualizar aquí para mantener consistencia.
_M06_PRIV = _KEYS_DIR / "m6_signing_dev.ed25519.pem"
_M06_PUB = _KEYS_DIR / "m6_signing_dev.ed25519.pub.pem"
_M07_PRIV = _KEYS_DIR / "ed25519_signing_private.pem"
_M07_PUB = _KEYS_DIR / "ed25519_signing_private.pub.pem"

# Env vars críticas · sin estas el arranque no tiene sentido en
# dev/staging/prod. Las claves Ed25519 (AUTH/ML/BACKUP) son opcionales
# en pure-dev (los servicios generan ephemeral con warning) pero el
# warning silencioso causó el bug LECCIÓN-OPS-004 (login MFA aparenta
# éxito pero rebota a /login). Aquí abortamos fail-fast en non-test.
_REQUIRED_ENV_VARS = (
    "DATABASE_URL",
    "FULKRO_AUTH_PRIVATE_KEY",
    "FULKRO_ML_PRIVATE_KEY",
    "FULKRO_BACKUP_SIGNING_KEY",
)

# Defaults inseguros que NUNCA deben llegar a producción.
# `minio_secret_key` default era "changeme" en config.py — riesgo crítico
# si producción no override env var.
_INSECURE_DEFAULTS: tuple[tuple[str, str], ...] = (
    ("FULKRO_MINIO_SECRET_KEY", "changeme"),
)


class CriticalConfigError(RuntimeError):
    """Configuración crítica ausente · arranque debe abortar."""


def _testing_mode() -> bool:
    """True si estamos en test run · skip checks que requieren disco real."""
    return os.environ.get("FULKRO_TESTING", "").strip() in {"1", "true", "yes"}


def verify_ed25519_keys() -> None:
    """Verifica que las 3 claves Ed25519 de firma (M05/M06/M07) son CARGABLES.

    FIX P0-1: en producción las claves vienen de env
    (``FULKRO_M05/M06/M07_SIGNING_PRIVATE_KEY``), inyectadas una sola vez por
    ``scripts/generate-prod-secrets.sh``. Antes este check miraba SOLO disco
    (M06+M07) y los motores autogeneraban claves efímeras si faltaban → cada
    ``docker recreate`` rotaba la clave e invalidaba la verificación de toda
    firma previa (contratos, dossier ENAC, evidencias). Ahora intentamos CARGAR
    cada clave por su loader canónico: en producción sin env → SigningKeyError →
    el arranque aborta (fail-fast); en dev se generan en disco reproducible.
    """
    errors: list[str] = []
    try:
        from backend.app.motors.m05_signing import keypair as _m05
        _m05.load_or_generate_keypair()
    except Exception as exc:  # noqa: BLE001 — agregamos y reportamos los 3
        errors.append(f"M05 ({type(exc).__name__}): {exc}")
    try:
        from backend.app.motors.m06_document_factory import signing as _m06
        _m06.sign_bytes(b"startup-probe")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"M06 ({type(exc).__name__}): {exc}")
    try:
        from backend.app.motors.m07_evidence import signing as _m07
        _m07.load_or_generate_keypair()
    except Exception as exc:  # noqa: BLE001
        errors.append(f"M07 ({type(exc).__name__}): {exc}")
    if errors:
        raise CriticalConfigError(
            "Claves Ed25519 de firma no cargables: " + " · ".join(errors)
            + ". En producción inyectar FULKRO_M05/M06/M07_SIGNING_PRIVATE_KEY "
            "(PEM) vía scripts/generate-prod-secrets.sh. NUNCA autogenerar en "
            "producción (rotación silenciosa invalida firmas · LECCIÓN-OPS-004 + "
            "auditoría 2026-06-09)."
        )
    logger.info(
        "Startup check OK: claves Ed25519 de firma M05+M06+M07 cargables",
    )


def verify_critical_env() -> None:
    """Verifica que las env vars críticas están definidas.

    Si `uvicorn` se arranca sin `--env-file .env`, `DATABASE_URL`
    estará ausente y el siguiente intento de query crashea con
    `AttributeError: NoneType` o similar. Mejor abortar aquí con un
    mensaje accionable.

    Cubre también las 3 claves Ed25519 inyectadas por env (AUTH/ML/BACKUP)
    cuyo missing antes solo emitía warning silencioso → ephemeral key
    invisible (LECCIÓN-OPS-004 manifestación múltiple).
    """
    missing = [k for k in _REQUIRED_ENV_VARS if not os.environ.get(k)]
    if missing:
        raise CriticalConfigError(
            f"Env vars críticas ausentes: {missing}. "
            f"En dev: arrancar uvicorn con `--env-file .env` "
            f"(LECCIÓN-OPS-004). En prod: gestor de secrets."
        )
    logger.info("Startup check OK: env vars críticas presentes")


def verify_no_insecure_defaults() -> None:
    """Aborta si alguna env var crítica conserva su default inseguro.

    Caso conocido: `minio_secret_key` defaultea a "changeme" en
    `config.py:43`. Si producción olvida override, MinIO acepta bucket
    access con credenciales triviales. Aquí abortamos fail-fast antes
    de que el servicio quede expuesto.
    """
    leaked = [
        env_name
        for env_name, insecure_value in _INSECURE_DEFAULTS
        if os.environ.get(env_name, "").strip() == insecure_value
    ]
    if leaked:
        raise CriticalConfigError(
            f"Env vars con default inseguro detectado: {leaked}. "
            f"Override obligatorio en dev/staging/prod (no usar valores "
            f"placeholder de config.py)."
        )
    logger.info("Startup check OK: 0 defaults inseguros activos")


def verify_app_secret_key() -> None:
    """En producción, app_secret_key NO puede ser default ni débil.

    Deriva el cifrado Fernet de tokens OAuth (m16) y credenciales SSH de
    pentest (m08). Si producción olvida el override, esos secretos quedan
    cifrados con una clave trivial/predecible (auditoría seguridad
    2026-06-07). En dev solo warning (no rompe el flujo local).
    """
    from backend.app.config import get_settings

    settings = get_settings()
    raw = getattr(settings, "app_secret_key", "")
    if hasattr(raw, "get_secret_value"):  # pydantic SecretStr
        raw = raw.get_secret_value()
    key = (raw or "").strip()
    weak = key in ("", "change-this", "changeme") or len(key) < 32
    if not getattr(settings, "is_production", False):
        if weak:
            logger.warning(
                "app_secret_key es default/débil (dev OK). En PRODUCCIÓN será "
                "fatal · genera una clave aleatoria >=32 chars."
            )
        return
    if weak:
        raise CriticalConfigError(
            "FULKRO_APP_SECRET_KEY ausente/default/débil en producción "
            "(>=32 chars aleatorios requeridos). Deriva el cifrado Fernet de "
            "tokens OAuth (m16) + credenciales SSH pentest (m08). Override "
            "obligatorio vía gestor de secrets."
        )
    logger.info("Startup check OK: app_secret_key robusta (producción)")


def verify_email_backend() -> None:
    """En producción el backend de email NO puede ser 'mock' (FIX P1-9).

    Con ``email_backend='mock'`` los magic-links de acceso del cliente (R5) y las
    notificaciones M20 se descartan en silencio devolviendo ``email_sent=True``
    → el cliente nunca recibe su enlace y el flujo aparenta éxito.
    ``.env.prod.template`` fija ``SMTP_*`` pero el default de config.py es 'mock'
    (fail-open) si no se activa ``EMAIL_BACKEND``.
    """
    from backend.app.config import get_settings

    settings = get_settings()
    if not getattr(settings, "is_production", False):
        return
    backend = (getattr(settings, "email_backend", "") or "").strip().lower()
    if backend in ("", "mock"):
        raise CriticalConfigError(
            "EMAIL_BACKEND='mock'/vacío en producción: magic-links y "
            "notificaciones se descartan en silencio (email_sent=True falso). "
            "Configurar EMAIL_BACKEND=smtp (con SMTP_HOST/USER/PASSWORD) o "
            "postmark_api (con POSTMARK_API_TOKEN)."
        )
    if backend == "smtp" and not (getattr(settings, "smtp_host", "") or "").strip():
        raise CriticalConfigError(
            "EMAIL_BACKEND='smtp' en producción pero SMTP_HOST vacío."
        )
    if backend == "postmark_api":
        tok = getattr(settings, "postmark_api_token", "")
        if hasattr(tok, "get_secret_value"):
            tok = tok.get_secret_value()
        if not (tok or "").strip():
            raise CriticalConfigError(
                "EMAIL_BACKEND='postmark_api' en producción pero "
                "POSTMARK_API_TOKEN vacío."
            )
    logger.info("Startup check OK: email_backend válido (producción)")


def verify_backup_encryption_key() -> None:
    """En producción BACKUP_ENCRYPTION_KEY no puede faltar/ser placeholder (P3-2).

    Deriva la Fernet que cifra los backups M26. El placeholder
    ``REPLACE_ME_RANDOM_48B`` (21 chars) pasaba el check ``>=16`` de
    encryption.py y cifraba los backups con un valor público commiteado →
    confidencialidad nula de los backups offsite.
    """
    from backend.app.config import get_settings

    settings = get_settings()
    if not getattr(settings, "is_production", False):
        return
    raw = getattr(settings, "backup_encryption_key", "")
    if hasattr(raw, "get_secret_value"):
        raw = raw.get_secret_value()
    key = (raw or "").strip()
    if not key or key.startswith("REPLACE_ME") or len(key) < 16:
        raise CriticalConfigError(
            "BACKUP_ENCRYPTION_KEY ausente/placeholder/débil en producción "
            "(>=16 chars aleatorios reales requeridos). Cifra los backups M26. "
            "Generar con scripts/generate-prod-secrets.sh."
        )
    logger.info("Startup check OK: BACKUP_ENCRYPTION_KEY robusta (producción)")


def run_startup_checks() -> None:
    """Entry-point para `lifespan` · ejecuta todos los checks.

    Skip automático si `FULKRO_TESTING=1` (set por conftest.py) para no
    interferir con tests unitarios que mockean DB/keys.
    """
    if _testing_mode():
        logger.debug("Startup checks skipped (FULKRO_TESTING=1)")
        return
    verify_critical_env()
    verify_no_insecure_defaults()
    verify_app_secret_key()
    verify_email_backend()
    verify_backup_encryption_key()
    verify_ed25519_keys()
    logger.info("Startup checks completados OK")
