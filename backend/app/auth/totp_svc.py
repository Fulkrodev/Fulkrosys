"""TOTP helpers (pyotp). Fallback MFA when WebAuthn is unavailable."""
from __future__ import annotations

import pyotp

TOTP_ISSUER = "FULKRO"
TOTP_DIGITS = 6
TOTP_INTERVAL = 30
TOTP_VALID_WINDOW = 1  # accept +/- 1 step (30s) to tolerate clock drift


def generate_secret() -> str:
    return pyotp.random_base32()


def verify_code(secret: str, code: str) -> bool:
    if not code or not code.isdigit() or len(code) != TOTP_DIGITS:
        return False
    totp = pyotp.TOTP(secret, digits=TOTP_DIGITS, interval=TOTP_INTERVAL)
    return totp.verify(code, valid_window=TOTP_VALID_WINDOW)


def provisioning_uri(secret: str, account_name: str) -> str:
    totp = pyotp.TOTP(secret, digits=TOTP_DIGITS, interval=TOTP_INTERVAL)
    return totp.provisioning_uri(name=account_name, issuer_name=TOTP_ISSUER)
