"""Alta de TOTP para un usuario administrador ya existente en ``auth_users``.

El login exige MFA y el usuario sembrado por las migraciones nace SIN WebAuthn
y SIN TOTP, así que antes del primer acceso por la UI hay que enrolar un
secreto. Escanea el URI/QR que imprime con cualquier aplicación de
autenticación y el flujo de login aceptará los códigos de 6 dígitos.

Uso (CLI, comportamiento histórico intacto):
    PYTHONPATH=. python3 backend/scripts/bootstrap_marcos_totp.py [email]

Sin argumento usa ``marcosmata@fulkro.es`` (el correo que deja vivo la
migración ``seed_admin_email_marcosmata_001``). Cada ejecución REGENERA el
secreto: el autenticador antiguo deja de valer.

Además de la CLI, este módulo expone las tres piezas reutilizables que usa
``backend/scripts/demo_bootstrap.py`` (OPS-026 · DRY, sin duplicar lógica):

    enroll_totp(conn, email, reuse_existing=False) -> (secret, uri)
    current_code(secret) -> str        # código válido en este instante
    resolve_async_db_url()             # misma resolución de URL que la CLI
"""
from __future__ import annotations

import asyncio
import os
import sys

import pyotp
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from backend.app.auth import totp_svc
from backend.app.config import get_settings


DEFAULT_EMAIL = "marcosmata@fulkro.es"


def resolve_async_db_url() -> str:
    """URL asyncpg con la que conectarse.

    Prioridad: ``DATABASE_MIGRATE_URL_ASYNC`` (rol con privilegios de
    migración) → ``settings.database_url`` con el usuario de aplicación
    elevado a ``fulkro`` (las tablas ``auth_*`` no llevan RLS, pero el rol de
    la app puede no tener INSERT en algún despliegue antiguo).
    """
    return os.environ.get(
        "DATABASE_MIGRATE_URL_ASYNC",
        get_settings().database_url.replace(
            "fulkro_app:changeme", "fulkro:changeme"
        ),
    )


def current_code(secret: str) -> str:
    """Código TOTP válido AHORA para ``secret``.

    Usa las constantes canónicas de ``backend.app.auth.totp_svc`` (6 dígitos,
    ventana de 30 s) para que lo impreso sea exactamente lo que valida
    ``POST /api/v1/auth/totp/verify``.
    """
    return pyotp.TOTP(
        secret, digits=totp_svc.TOTP_DIGITS, interval=totp_svc.TOTP_INTERVAL
    ).now()


async def enroll_totp(
    conn, email: str, *, reuse_existing: bool = False
) -> tuple[str, str]:
    """Enrola (o reutiliza) el secreto TOTP de ``email``. Devuelve (secreto, URI).

    ``conn`` es una ``AsyncConnection`` o ``AsyncSession`` ya abierta: quien
    llama decide la transacción (la CLI hace su propio ``commit``).

    ``reuse_existing=True`` deja intacto el secreto ya enrolado — así el
    arranque del demo es idempotente y NO invalida el autenticador que el
    operador ya escaneó. ``False`` (por defecto) mantiene el comportamiento
    histórico de esta CLI: regenerar siempre.

    Lanza ``LookupError`` si el correo no existe en ``auth_users``.
    """
    row = (
        await conn.execute(
            text("SELECT id FROM auth_users WHERE email = :e"), {"e": email}
        )
    ).first()
    if row is None:
        raise LookupError(f"no hay usuario en auth_users con email {email!r}")

    secret: str | None = None
    if reuse_existing:
        existing = (
            await conn.execute(
                text(
                    "SELECT secret FROM auth_totp_secrets "
                    "WHERE user_id = :uid AND verified = true"
                ),
                {"uid": row.id},
            )
        ).first()
        if existing is not None:
            secret = existing.secret

    if secret is None:
        secret = totp_svc.generate_secret()
        await conn.execute(
            text(
                "INSERT INTO auth_totp_secrets (user_id, secret, verified) "
                "VALUES (:uid, :s, true) "
                "ON CONFLICT (user_id) DO UPDATE SET "
                "secret = EXCLUDED.secret, verified = true"
            ),
            {"uid": row.id, "s": secret},
        )

    return secret, totp_svc.provisioning_uri(secret, email)


async def main(email: str) -> int:
    engine = create_async_engine(resolve_async_db_url(), echo=False)
    try:
        async with engine.connect() as conn:
            try:
                secret, uri = await enroll_totp(conn, email)
            except LookupError as exc:
                print(f"[error] {exc}")
                return 1
            await conn.commit()

        print()
        print("TOTP enrolment OK.")
        print(f"  user:   {email}")
        print(f"  secret: {secret}")
        print(f"  codigo valido ahora: {current_code(secret)}")
        print()
        print("Scan this URI with your authenticator (or paste the secret):")
        print(f"  {uri}")
        print()
        print(
            "If you have `qrencode` installed, render the QR in the terminal:\n"
            f"  qrencode -t ANSI256 {uri!r}"
        )
        return 0
    finally:
        await engine.dispose()


if __name__ == "__main__":
    arg_email = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_EMAIL
    sys.exit(asyncio.run(main(arg_email)))
