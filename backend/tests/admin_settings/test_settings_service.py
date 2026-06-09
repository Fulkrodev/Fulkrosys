"""Tests baseline service layer admin_settings (plan v4.2 tarea 4.15).

8 tests cubriendo el contrato de
``backend/app/admin_settings/service.py`` + integración trigger
``tg_audit_admin_settings`` (sub-bloque 4.A.2.d):

Service contract (5):
    1. get_settings devuelve singleton tras seed
    2. get_settings raises AdminSettingsNotFoundError sin seed
    3. ensure_seeded idempotente (no duplica si existe)
    4. update_section branding persiste cambios
    5. update_section parcial merges fields no enviados (exclude_unset)

Defensa runtime (1):
    6. update_section raises ValueError si payload schema mismatch

Integration trigger audit_log (2):
    7. update_section genera audit_log entry con usuario=user.email
    8. update_section audit_log captura payload_old/payload_new diff

Pattern transaccional: fixture ``db`` (top-level conftest) bind a
connection con ``trans.begin()`` que rollback al final del test.
``service.update_section`` hace ``db.commit()`` que en este contexto
opera como savepoint dentro de la transacción outer — los efectos
(UPDATE admin_settings + INSERT audit_log via trigger) son visibles
dentro del test pero rolled back tras él. Aislamiento perfecto.

audit_log integration end-to-end (tests 7+8) usa la BD real con
los triggers aplicados (migración ``8e02b4ed6004``) — no es mock.
Dentro del transaction scope se ven las entries; rollback las
elimina junto con todo lo demás.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.admin_settings.schemas import (
    BrandingSettings,
    NotificationsSettings,
)
from backend.app.admin_settings.service import (
    AdminSettingsNotFoundError,
    ensure_seeded,
    get_settings,
    update_section,
)
from backend.app.models.admin import ADMIN_SETTINGS_ID, AdminSettings
from backend.tests.conftest import _admin_setup


# ─────────────────────────────────────────────────────────────────
# Service contract (5 tests)
# ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_settings_returns_singleton_after_seed(db: AsyncSession):
    """get_settings devuelve singleton row con id correcto.

    Solo asertamos id y types: el contenido JSONB puede tener valores
    de smoke commits previos (BD compartida con dev). El contrato de
    get_settings es "devuelve la fila singleton", no "branding está
    vacía".
    """
    settings = await ensure_seeded(db)
    assert settings.id == ADMIN_SETTINGS_ID

    fetched = await get_settings(db)
    assert fetched.id == ADMIN_SETTINGS_ID
    # JSONB columns presentes con tipo dict (puede contener data)
    assert isinstance(fetched.branding, dict)
    assert isinstance(fetched.notifications, dict)
    assert isinstance(fetched.smtp, dict)
    assert isinstance(fetched.general, dict)
    assert isinstance(fetched.analytics_prefs, dict)


@pytest.mark.asyncio
async def test_get_settings_raises_when_singleton_missing(db: AsyncSession):
    """get_settings raises AdminSettingsNotFoundError sin seed."""
    # Eliminar singleton dentro de esta transacción (rollback restora)
    async with _admin_setup(db):
        await db.execute(text("DELETE FROM admin_settings"))

    with pytest.raises(AdminSettingsNotFoundError) as exc_info:
        await get_settings(db)

    assert "singleton" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_ensure_seeded_idempotent(db: AsyncSession):
    """ensure_seeded llamado N veces NO duplica row (singleton)."""
    first = await ensure_seeded(db)
    second = await ensure_seeded(db)
    third = await ensure_seeded(db)

    assert first.id == second.id == third.id == ADMIN_SETTINGS_ID

    # Verificar count = 1 (CheckConstraint enforce, pero check explícito)
    count_result = await db.execute(
        select(AdminSettings).where(AdminSettings.id == ADMIN_SETTINGS_ID)
    )
    rows = count_result.scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_update_section_branding_persists(
    db: AsyncSession, make_user,
):
    """update_section branding persiste cambios + GET refleja UPDATE."""
    await ensure_seeded(db)
    owner = await make_user(role="owner", email="test-owner-branding@example.com")

    updated = await update_section(
        db=db,
        section="branding",
        payload=BrandingSettings(
            primary_color="#3b82f6",
            footer_text="Test Branding",
        ),
        user=owner,
    )

    assert updated.branding["primary_color"] == "#3b82f6"
    assert updated.branding["footer_text"] == "Test Branding"

    # Verify persisted via fresh GET
    fetched = await get_settings(db)
    assert fetched.branding["primary_color"] == "#3b82f6"
    assert fetched.branding["footer_text"] == "Test Branding"


@pytest.mark.asyncio
async def test_update_section_partial_merges_preserves_other_fields(
    db: AsyncSession, make_user,
):
    """PATCH parcial preserva fields no enviados (exclude_unset merge)."""
    await ensure_seeded(db)
    owner = await make_user(role="owner", email="test-owner-merge@example.com")

    # Setup: PATCH inicial con varios fields
    await update_section(
        db=db,
        section="branding",
        payload=BrandingSettings(
            logo_url="https://example.com/logo.png",
            primary_color="#000000",
            footer_text="Initial",
        ),
        user=owner,
    )

    # PATCH parcial: solo primary_color
    updated = await update_section(
        db=db,
        section="branding",
        payload=BrandingSettings(primary_color="#ff0000"),
        user=owner,
    )

    # primary_color updated
    assert updated.branding["primary_color"] == "#ff0000"
    # logo_url + footer_text preserved (no enviados, merge mantuvo)
    assert updated.branding["logo_url"] == "https://example.com/logo.png"
    assert updated.branding["footer_text"] == "Initial"


# ─────────────────────────────────────────────────────────────────
# Defensa runtime (1 test)
# ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_section_raises_value_error_on_schema_mismatch(
    db: AsyncSession, make_user,
):
    """update_section raises ValueError si payload schema != section esperado."""
    await ensure_seeded(db)
    owner = await make_user(role="owner", email="test-owner-mismatch@example.com")

    # Pasar NotificationsSettings a section="branding" → mismatch
    wrong_payload = NotificationsSettings(client_messages_forward_enabled=False)

    with pytest.raises(ValueError) as exc_info:
        await update_section(
            db=db,
            section="branding",
            payload=wrong_payload,
            user=owner,
        )

    assert "no coincide" in str(exc_info.value).lower()


# ─────────────────────────────────────────────────────────────────
# Integration trigger audit_log (2 tests)
# ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_section_writes_audit_log_entry_with_user_email(
    db: AsyncSession, make_user,
):
    """Trigger tg_audit_admin_settings genera entry con usuario=user.email."""
    await ensure_seeded(db)
    owner = await make_user(
        role="owner", email="audit-trace@fulkro.test",
    )

    await update_section(
        db=db,
        section="branding",
        payload=BrandingSettings(footer_text="audit trace"),
        user=owner,
    )

    # Query audit_log dentro del transaction scope (visible por trigger)
    result = await db.execute(
        text(
            "SELECT tabla, accion, usuario "
            "FROM audit_log "
            "WHERE tabla = 'admin_settings' "
            "ORDER BY timestamp DESC LIMIT 1"
        )
    )
    row = result.first()
    assert row is not None, "audit_log entry NO creado por trigger"
    assert row.tabla == "admin_settings"
    assert row.accion == "UPDATE"
    assert row.usuario == "audit-trace@fulkro.test"


@pytest.mark.asyncio
async def test_update_section_audit_log_captures_payload_diff(
    db: AsyncSession, make_user,
):
    """Trigger captura payload_old / payload_new con el diff de la fila.

    Diseño robusto: un único update_section con valor único +
    asertar diff (payload_new contiene lo que se envió; payload_old
    difiere de payload_new). No asume estado inicial específico
    de admin_settings (BD compartida con dev/smoke previos).
    """
    await ensure_seeded(db)
    owner = await make_user(
        role="owner", email="audit-diff@fulkro.test",
    )

    test_color = "#1a2b3c"  # valor único para aislar este test

    await update_section(
        db=db,
        section="branding",
        payload=BrandingSettings(primary_color=test_color),
        user=owner,
    )

    # Última entry audit_log con esta usuario (única en este test)
    result = await db.execute(
        text(
            "SELECT payload_old, payload_new "
            "FROM audit_log "
            "WHERE tabla = 'admin_settings' "
            "AND usuario = 'audit-diff@fulkro.test' "
            "ORDER BY timestamp DESC LIMIT 1"
        )
    )
    row = result.first()
    assert row is not None, "Trigger no escribió audit_log entry"

    # payload_new captura la fila tras UPDATE (incluye nuestro color)
    assert row.payload_new["branding"]["primary_color"] == test_color

    # payload_old captura la fila ANTES del UPDATE — debe diferir del new
    # (diff capturado, sin asumir valor exacto previo)
    old_color = row.payload_old["branding"].get("primary_color")
    assert old_color != test_color, (
        f"payload_old.primary_color ({old_color}) NO debería igualar "
        f"payload_new ({test_color}) — el diff no se capturó"
    )
