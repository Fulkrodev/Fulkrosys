"""One-time TOTP enrolment for the seed user (``marcosmata@fulkro.es``).

Login requires MFA. The seed user has neither WebAuthn nor TOTP configured, so
before the first UI login, run this script once on the server to enrol a TOTP
secret. Scan the printed QR / provisioning URI with any authenticator app and
the login flow will accept the 6-digit codes.

Usage:
    PYTHONPATH=. python3 backend/scripts/bootstrap_marcos_totp.py

It is idempotent: rerunning regenerates a fresh secret for the seed user.
"""
from __future__ import annotations

import asyncio
import os
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from backend.app.auth import totp_svc
from backend.app.config import get_settings


DEFAULT_EMAIL = "marcosmata@fulkro.es"


async def main(email: str) -> int:
    settings = get_settings()
    url = os.environ.get(
        "DATABASE_MIGRATE_URL_ASYNC",
        settings.database_url.replace(
            "fulkro_app:changeme", "fulkro:changeme"
        ),
    )

    engine = create_async_engine(url, echo=False)
    try:
        async with engine.connect() as conn:
            user = await conn.execute(
                text(
                    "SELECT id, email, display_name FROM auth_users "
                    "WHERE email = :e"
                ),
                {"e": email},
            )
            row = user.first()
            if row is None:
                print(f"[error] No auth user with email {email!r}")
                return 1

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
            await conn.commit()

        uri = totp_svc.provisioning_uri(secret, email)
        print()
        print("TOTP enrolment OK.")
        print(f"  user:   {row.email}")
        print(f"  secret: {secret}")
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
    email = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_EMAIL
    sys.exit(asyncio.run(main(email)))
