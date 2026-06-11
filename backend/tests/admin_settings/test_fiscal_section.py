"""Tests categoría fiscal AdminSettings + accessor get_fiscal_identity (#44).

Cubre la FUNDACIÓN del punto #44 (datos fiscales del consultor):

Service / persistencia (3):
    1. update_section('fiscal') persiste + GET refleja (régimen autónomo real)
    2. update_section('fiscal') genera audit_log entry (trigger · R6/R13)
    3. update_section('fiscal') extra="forbid" rechaza campos no esperados

Accessor core.fiscal_identity (4):
    4. get_fiscal_identity vacío → degrada SIN placeholder (anti-falso-verde R12)
    5. get_fiscal_identity tras setear → devuelve datos reales + propiedades
    6. get_fiscal_identity banca fiscal-first; fallback Settings.marcos_bank_*
    7. config bugfix: marcos_bank_holder == "Marcos Mata García" (no "Vega")

Pattern transaccional: fixture ``db`` rollback al final; ``update_section``
hace commit que opera como savepoint dentro de la transacción outer.
El accessor lee la misma sesión → ve los cambios antes del rollback.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.admin_settings.schemas import FiscalSettings
from backend.app.admin_settings.service import ensure_seeded, get_settings, update_section
from backend.app.core.fiscal_identity import get_fiscal_identity
from backend.tests.conftest import _admin_setup


# Datos fiscales reales de Marcos (autónomo persona física · decisión #44).
_MARCOS_FISCAL = dict(
    nif="77171140E",
    nombre_fiscal="Marcos Mata García",
    nombre_comercial="FULKRO",
    tipo_persona="F",
    domicilio_via="Paseo de la Dirección, 46",
    domicilio_municipio="Madrid",
    domicilio_provincia="Madrid",
    iva_pct=21.0,
    sujeto_irpf=True,
    irpf_pct=15.0,
    iban="ES34 1465 0260 6317 5549 5007",
)


async def _reset_fiscal_empty(db: AsyncSession) -> None:
    """Deja admin_settings.fiscal = '{}' (estado degradado limpio)."""
    async with _admin_setup(db):
        await db.execute(text("UPDATE admin_settings SET fiscal = '{}'::jsonb"))


# ─────────────────────────────────────────────────────────────────
# Service / persistencia
# ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_section_fiscal_persists(db: AsyncSession, make_user):
    """update_section('fiscal') persiste la identidad fiscal real."""
    await ensure_seeded(db)
    owner = await make_user(role="owner", email="test-fiscal-persist@example.com")

    updated = await update_section(
        db=db, section="fiscal",
        payload=FiscalSettings(**_MARCOS_FISCAL),
        user=owner,
    )

    assert updated.fiscal["nif"] == "77171140E"
    assert updated.fiscal["nombre_fiscal"] == "Marcos Mata García"
    assert updated.fiscal["tipo_persona"] == "F"

    fetched = await get_settings(db)
    assert fetched.fiscal["iban"] == "ES34 1465 0260 6317 5549 5007"
    assert fetched.fiscal["domicilio_via"] == "Paseo de la Dirección, 46"


@pytest.mark.asyncio
async def test_update_section_fiscal_writes_audit_log(db: AsyncSession, make_user):
    """El trigger tg_audit_admin_settings deja rastro al tocar fiscal (R6)."""
    await ensure_seeded(db)
    # Parte de fiscal vacío para observar un cambio limpio (la migración
    # unify_pricing_fiscal_rls_001 pre-puebla el NIF en el seed/build).
    await _reset_fiscal_empty(db)
    owner = await make_user(role="owner", email="audit-fiscal@fulkro.test")

    await update_section(
        db=db, section="fiscal",
        payload=FiscalSettings(nif="77171140E", nombre_fiscal="Marcos Mata García"),
        user=owner,
    )

    row = (await db.execute(text(
        "SELECT tabla, accion, usuario, payload_new FROM audit_log "
        "WHERE tabla = 'admin_settings' AND usuario = 'audit-fiscal@fulkro.test' "
        "ORDER BY timestamp DESC LIMIT 1"
    ))).first()
    assert row is not None, "audit_log entry NO creado por trigger"
    assert row.tabla == "admin_settings"
    assert row.accion == "UPDATE"
    assert row.payload_new["fiscal"]["nif"] == "77171140E"


@pytest.mark.asyncio
async def test_fiscal_settings_forbids_extra_fields():
    """extra='forbid': payload con campo no esperado → ValidationError."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        FiscalSettings(nif="77171140E", campo_inventado="x")


# ─────────────────────────────────────────────────────────────────
# Accessor core.fiscal_identity
# ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_fiscal_identity_empty_degrades_no_placeholder(db: AsyncSession):
    """Anti-falso-verde (R12): fiscal vacío → cadenas vacías, NUNCA placeholder.

    El bug original era emitir "__CONSULTOR_NIF__". El accessor debe
    devolver "" para que el consumidor degrade, jamás el placeholder.
    """
    await ensure_seeded(db)
    await _reset_fiscal_empty(db)

    fi = await get_fiscal_identity(db)

    assert fi.nif == ""
    assert fi.has_nif is False
    assert fi.has_identity is False
    assert fi.display_name == ""
    # El pecado capital: que el placeholder se cuele.
    assert "__CONSULTOR_NIF__" not in (fi.nif, fi.nombre_fiscal, fi.display_name)
    # Régimen por defecto autónomo coherente aunque vacío.
    assert fi.tipo_persona == "F"
    assert fi.person_type_code == "F"


@pytest.mark.asyncio
async def test_get_fiscal_identity_reads_persisted(db: AsyncSession, make_user):
    """Tras setear la identidad real, el accessor la devuelve + propiedades."""
    await ensure_seeded(db)
    owner = await make_user(role="owner", email="test-fiscal-read@example.com")
    await update_section(
        db=db, section="fiscal",
        payload=FiscalSettings(**_MARCOS_FISCAL),
        user=owner,
    )

    fi = await get_fiscal_identity(db)

    assert fi.nif == "77171140E"
    assert fi.has_nif is True
    assert fi.has_identity is True
    assert fi.nombre_fiscal == "Marcos Mata García"
    # display_name usa el comercial cuando existe
    assert fi.display_name == "FULKRO"
    assert fi.person_type_code == "F"
    assert fi.has_iban is True
    assert "Paseo de la Dirección, 46" in fi.domicilio_completo
    assert "Madrid" in fi.domicilio_completo
    assert "España" in fi.domicilio_completo


@pytest.mark.asyncio
async def test_get_fiscal_identity_banking_env_fallback(
    db: AsyncSession, patched_settings,
):
    """Banca: si fiscal no tiene IBAN, cae a Settings.marcos_bank_* (env)."""
    await ensure_seeded(db)
    await _reset_fiscal_empty(db)
    # IBAN solo en env (no en fiscal) → el accessor debe exponerlo.
    patched_settings(marcos_bank_iban="ES9900112233445566778899")

    fi = await get_fiscal_identity(db)

    assert fi.iban == "ES9900112233445566778899"
    # holder cae al default fijado en config.py (bug "Vega" corregido)
    assert fi.bank_holder == "Marcos Mata García"


def test_config_bank_holder_bug_fixed():
    """Bugfix #44: marcos_bank_holder default == 'Marcos Mata García'."""
    from backend.app.config import get_settings as get_env_settings

    assert get_env_settings().marcos_bank_holder == "Marcos Mata García"
