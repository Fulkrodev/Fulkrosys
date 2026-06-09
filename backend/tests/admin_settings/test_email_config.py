"""Tests EmailSender ↔ AdminSettings.smtp integration (4.A.3.b).

Cobertura:
- ``parse_smtp_from`` parametrizado 5 casos formato legacy.
- ``get_smtp_config`` fallback Settings env cuando AdminSettings.smtp vacío.
- ``get_smtp_config`` override AdminSettings.smtp cuando host populated.
- ``get_smtp_config`` con override dict prioridad máxima.

Pattern: ``ensure_seeded(db)`` + ``update_section`` para PATCH directo
(no HTTP client). Coherente con tests/admin_settings/test_settings_service.py.
"""
from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.admin_settings.email_config import (
    SmtpConfig,
    get_smtp_config,
    parse_smtp_from,
)
from backend.app.admin_settings.schemas import SmtpSettings
from backend.app.admin_settings.service import ensure_seeded, update_section


# ─────────────────────────────────────────────────────────────────
# parse_smtp_from (formato legacy "Name <email>")
# ─────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("FULKRO <noreply@fulkro.es>", ("FULKRO", "noreply@fulkro.es")),
        ("noreply@fulkro.es", (None, "noreply@fulkro.es")),
        ("", (None, "noreply@fulkro.es")),
        (
            "FULKRO Tech <support@fulkro.es>",
            ("FULKRO Tech", "support@fulkro.es"),
        ),
        ("<bracket-only@x.com>", (None, "bracket-only@x.com")),
    ],
)
def test_parse_smtp_from_cases(raw, expected):
    """parse_smtp_from extrae correctamente formato legacy."""
    assert parse_smtp_from(raw) == expected


# ─────────────────────────────────────────────────────────────────
# get_smtp_config (resolver con prioridad)
# ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_smtp_config_returns_smtp_config_dataclass(
    db: AsyncSession,
):
    """Smoke: get_smtp_config devuelve SmtpConfig con shape correcto."""
    await ensure_seeded(db)
    config = await get_smtp_config(db)
    assert isinstance(config, SmtpConfig)
    assert config.from_email is not None
    assert isinstance(config.use_tls, bool)


@pytest.mark.asyncio
async def test_get_smtp_config_uses_admin_when_host_populated(
    db: AsyncSession,
    make_user,
):
    """AdminSettings.smtp.host populated → override Settings env."""
    await ensure_seeded(db)
    owner = await make_user(role="owner", email="test-smtp-cfg@example.com")

    await update_section(
        db=db,
        section="smtp",
        payload=SmtpSettings(
            host="custom-smtp.example.com",
            port=2525,
            username="custom_user",
        ),
        user=owner,
    )

    config = await get_smtp_config(db)
    assert config.host == "custom-smtp.example.com"
    assert config.port == 2525
    assert config.username == "custom_user"
    # use_tls SIEMPRE de Settings (NO override AdminSettings)
    assert isinstance(config.use_tls, bool)


@pytest.mark.asyncio
async def test_get_smtp_config_with_override_dict_max_priority(
    db: AsyncSession,
    make_user,
):
    """override dict prioridad máxima sobre AdminSettings + env."""
    await ensure_seeded(db)
    owner = await make_user(role="owner", email="test-smtp-ovr@example.com")

    # AdminSettings con custom host
    await update_section(
        db=db,
        section="smtp",
        payload=SmtpSettings(host="admin.example.com", port=1025),
        user=owner,
    )

    # Override dict debe ganarle
    override = {
        "host": "override.example.com",
        "port": 465,
        "username": "override_user",
        "password": "override_pass",
    }

    config = await get_smtp_config(db, override=override)
    assert config.host == "override.example.com"
    assert config.port == 465
    assert config.username == "override_user"
    assert config.password == "override_pass"
