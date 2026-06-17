"""Helper SMTP config resolution: AdminSettings override parcial + Settings env fallback.

Plan v4.2 tarea 4.20 literal: admin SOLO edita host/port/user/password.
from_email/from_name/use_tls SIEMPRE de Settings env (no editables UI).

Prioridad resolución:
    1. override one-shot dict (test envío sin persistir) — solo host/port/user/password
    2. AdminSettings.smtp custom (host/port/user/password) field-by-field
    3. Settings env como fallback completo

from_email/from_name: parseados de Settings.smtp_from legacy ("Name <email>").
use_tls: SIEMPRE de Settings.smtp_use_tls.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.admin_settings import service as admin_settings_service
from backend.app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class SmtpConfig:
    """Config SMTP resuelta lista para uso por EmailSender._send_smtp."""

    host: str
    port: int
    username: Optional[str]
    password: Optional[str]
    from_email: str
    from_name: Optional[str]
    use_tls: bool = True


def parse_smtp_from(raw: str) -> Tuple[Optional[str], str]:
    """Extrae (name, email) del formato legacy ``smtp_from``.

    Examples:
        "FULKRO <noreply@fulkro.es>" → ("FULKRO", "noreply@fulkro.es")
        "noreply@fulkro.es"          → (None, "noreply@fulkro.es")
        ""                           → (None, "noreply@fulkro.es")  # default fallback
    """
    if not raw:
        return (None, "noreply@fulkro.es")

    match = re.match(r"^\s*(.*?)\s*<([^>]+)>\s*$", raw)
    if match:
        name = match.group(1).strip()
        email = match.group(2).strip()
        return (name or None, email)

    return (None, raw.strip())


async def get_smtp_config(
    db: AsyncSession,
    override: Optional[dict] = None,
) -> SmtpConfig:
    """Resuelve SMTP config con prioridad override > AdminSettings > Settings env.

    Args:
        db: AsyncSession para query AdminSettings singleton.
        override: dict opcional con cualquier subset de
            ``{host, port, username, password}``. Tiene prioridad máxima
            (no persiste — usado por endpoint /smtp/test).

    Returns:
        SmtpConfig listo para uso por EmailSender._send_smtp.
    """
    settings = get_settings()

    from_name, from_email = parse_smtp_from(settings.smtp_from)

    env_host = settings.smtp_host or ""
    env_port = settings.smtp_port or 587
    env_username = settings.smtp_user or None
    env_password = settings.smtp_password.get_secret_value() or None

    admin_host: Optional[str] = None
    admin_port: Optional[int] = None
    admin_username: Optional[str] = None
    admin_password: Optional[str] = None

    try:
        admin_settings_obj = await admin_settings_service.get_settings(db)
        smtp_custom = admin_settings_obj.smtp or {}

        if smtp_custom.get("host"):
            admin_host = smtp_custom["host"]
        if smtp_custom.get("port"):
            admin_port = smtp_custom["port"]
        if smtp_custom.get("username"):
            admin_username = smtp_custom["username"]
        if smtp_custom.get("password"):
            # S24: el password se persiste cifrado con prefijo enc:v1: · se
            # descifra para uso. Rows legacy en claro (sin prefijo) siguen
            # funcionando (backward-compat) hasta el próximo guardado.
            raw_pwd = str(smtp_custom["password"])
            if raw_pwd.startswith("enc:v1:"):
                try:
                    from backend.app.motors.m16_onboarding.token_encryption import (
                        decrypt_str,
                    )
                    admin_password = decrypt_str(raw_pwd[len("enc:v1:"):])
                except Exception as dexc:  # noqa: BLE001
                    logger.warning(
                        "SMTP password cifrado no descifrable (%s) · fallback env",
                        dexc,
                    )
                    admin_password = None
            else:
                admin_password = raw_pwd
    except Exception as exc:
        logger.warning(
            "AdminSettings.smtp lookup failed: %s. Using env defaults.", exc,
        )

    if override:
        if override.get("host"):
            admin_host = override["host"]
        if override.get("port"):
            admin_port = override["port"]
        if override.get("username"):
            admin_username = override["username"]
        if override.get("password"):
            admin_password = override["password"]

    return SmtpConfig(
        host=admin_host or env_host,
        port=admin_port or env_port,
        username=admin_username or env_username,
        password=admin_password or env_password,
        from_email=from_email,
        from_name=from_name,
        use_tls=settings.smtp_use_tls,
    )
