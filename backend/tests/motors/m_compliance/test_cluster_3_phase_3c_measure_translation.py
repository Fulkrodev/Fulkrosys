"""CLUSTER 3 Phase 3C · Measure Translation canonical service tests.

Sesión 3B-2B.8 CLUSTER 3 Phase 3C · pure functional translation service
deterministic R1 · canonical function reusable cross-motors.

Coverage:
- translate_measure_to_cliente_friendly returns None cuando NO existe
- translate_measure_to_cliente_friendly returns curated override cuando
  measure_code en TRANSLATION_OVERRIDES (has_curated_override=True)
- translate_measure_to_cliente_friendly fallback cuando NO override
  (has_curated_override=False · build desde ens_measures + familia hint)
- Curated overrides 100% cliente-friendly Spanish (NO admin lingo plain)
- to_admin_dict full detail vs to_cliente_dict NO leak admin_technical_detail
- Familia hint applied cuando NO descripcion + override
- Empty/whitespace measure_code returns None

Pattern 20 cumulative formalized: canonical translation + curated overrides +
graceful fallback + dual UX same source data.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m_compliance.measure_translation_service import (
    FAMILIA_HINTS_CLIENTE,
    MeasureTranslation,
    TRANSLATION_OVERRIDES,
    translate_measure_to_cliente_friendly,
)
from backend.tests.conftest import _admin_setup


# ════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════


async def _insert_ens_measure(
    db: AsyncSession,
    *,
    codigo: str,
    nombre: str,
    descripcion: str | None = None,
    familia: str | None = None,
    categoria_minima: str | None = None,
    fuente_oficial: str | None = None,
) -> uuid.UUID:
    """Insert/upsert test EnsMeasure row · returns id.

    ON CONFLICT updates ALL fields (codigo unique constraint) so tests can
    override existing seed data deterministically.
    """
    measure_id = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO ens_measures "
            "(id, codigo, nombre, marco, descripcion, familia, "
            "categoria_minima, fuente_oficial, aplica_basica, aplica_media, "
            "aplica_alta, created_at) "
            "VALUES (:id, :codigo, :nombre, 'ENS', :desc, :fam, "
            ":catmin, :src, true, true, true, now()) "
            "ON CONFLICT (codigo) DO UPDATE SET "
            "nombre = EXCLUDED.nombre, "
            "descripcion = EXCLUDED.descripcion, "
            "familia = EXCLUDED.familia, "
            "categoria_minima = EXCLUDED.categoria_minima, "
            "fuente_oficial = EXCLUDED.fuente_oficial"
        ), {
            "id": str(measure_id),
            "codigo": codigo,
            "nombre": nombre,
            "desc": descripcion,
            "fam": familia,
            "catmin": categoria_minima,
            "src": fuente_oficial,
        })
    return measure_id


# ════════════════════════════════════════════════════════════════════
# Phase 3C · None when measure_code not found / empty
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_translate_returns_none_when_codigo_not_exists(
    db: AsyncSession,
) -> None:
    """translate_measure_to_cliente_friendly returns None cuando measure NO existe."""
    result = await translate_measure_to_cliente_friendly(
        db, "non.existent.code.xyz",
    )
    assert result is None


@pytest.mark.asyncio
async def test_translate_returns_none_empty_codigo(
    db: AsyncSession,
) -> None:
    """Empty/whitespace measure_code returns None."""
    assert await translate_measure_to_cliente_friendly(db, "") is None
    assert await translate_measure_to_cliente_friendly(db, "   ") is None


# ════════════════════════════════════════════════════════════════════
# Phase 3C · Curated override scenarios
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_translate_uses_curated_override_for_op_acc_6(
    db: AsyncSession,
) -> None:
    """op.acc.6 (Autenticación MFA) returns curated override."""
    await _insert_ens_measure(
        db,
        codigo="op.acc.6",
        nombre="Autenticación · MFA",
        descripcion="Multi-factor authentication required",
        familia="op.acc",
        categoria_minima="MEDIA",
        fuente_oficial="RD 311/2022 Anexo II",
    )

    result = await translate_measure_to_cliente_friendly(db, "op.acc.6")

    assert result is not None
    assert result.has_curated_override is True
    assert result.cliente_friendly_title == "Inicio de sesión seguro (MFA)"
    assert "segundo paso" in result.cliente_friendly_explanation
    assert result.familia == "op.acc"
    assert result.categoria_minima == "MEDIA"


@pytest.mark.asyncio
async def test_translate_uses_curated_override_for_org_4(
    db: AsyncSession,
) -> None:
    """org.4 returns curated override · sin prisa R29 firmísimo."""
    await _insert_ens_measure(
        db,
        codigo="org.4",
        nombre="Política de seguridad",
        familia="org",
    )

    result = await translate_measure_to_cliente_friendly(db, "org.4")

    assert result is not None
    assert result.has_curated_override is True
    assert "Política de seguridad firmada" == result.cliente_friendly_title
    assert "sin prisa" in result.cliente_friendly_explanation.lower()


# ════════════════════════════════════════════════════════════════════
# Phase 3C · Fallback safe (non-curated)
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_translate_fallback_when_no_override(
    db: AsyncSession,
) -> None:
    """Sin override · fallback desde ens_measures.nombre + descripcion."""
    await _insert_ens_measure(
        db,
        codigo="mp.eq.99",  # NOT en TRANSLATION_OVERRIDES
        nombre="Protección de equipos · Bloqueo de puertos",
        descripcion=(
            "Bloquea físicamente los puertos USB en equipos críticos para "
            "evitar conexión de dispositivos no autorizados."
        ),
        familia="mp.eq",
        categoria_minima="ALTA",
    )

    result = await translate_measure_to_cliente_friendly(db, "mp.eq.99")

    assert result is not None
    assert result.has_curated_override is False
    assert "Bloqueo de puertos" in result.cliente_friendly_title
    assert "puertos USB" in result.cliente_friendly_explanation
    assert result.familia == "mp.eq"


@pytest.mark.asyncio
async def test_translate_fallback_no_descripcion_uses_familia_hint(
    db: AsyncSession,
) -> None:
    """Sin override + sin descripcion · usa familia hint friendly."""
    await _insert_ens_measure(
        db,
        codigo="mp.com.99",
        nombre="Comunicaciones · custom",
        descripcion=None,
        familia="mp.com",
    )

    result = await translate_measure_to_cliente_friendly(db, "mp.com.99")

    assert result is not None
    assert result.has_curated_override is False
    expected_hint = FAMILIA_HINTS_CLIENTE.get("mp.com", "")
    assert expected_hint in result.cliente_friendly_explanation
    assert "marco ENS aplica" in result.cliente_friendly_explanation


# ════════════════════════════════════════════════════════════════════
# Phase 3C · admin vs cliente dual UX
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_to_admin_dict_includes_technical_detail(
    db: AsyncSession,
) -> None:
    """to_admin_dict includes admin_technical_detail field."""
    await _insert_ens_measure(
        db,
        codigo="op.acc.5",
        nombre="Autenticación · Mecanismos",
        descripcion="Mecanismos de autenticación robustos",
        familia="op.acc",
        categoria_minima="BASICA",
        fuente_oficial="RD 311/2022",
    )

    result = await translate_measure_to_cliente_friendly(db, "op.acc.5")
    assert result is not None

    admin_d = result.to_admin_dict()
    assert "admin_technical_detail" in admin_d
    assert "ENS codigo: op.acc.5" in admin_d["admin_technical_detail"]
    assert "Familia: op.acc" in admin_d["admin_technical_detail"]
    assert "Categoría mínima: BASICA" in admin_d["admin_technical_detail"]
    assert admin_d["fuente_oficial"] == "RD 311/2022"


@pytest.mark.asyncio
async def test_to_cliente_dict_no_leak_admin_technical(
    db: AsyncSession,
) -> None:
    """to_cliente_dict NO leak admin_technical_detail (filosofía cliente-mínimo)."""
    await _insert_ens_measure(
        db,
        codigo="op.acc.5",
        nombre="Autenticación · Mecanismos",
        familia="op.acc",
    )

    result = await translate_measure_to_cliente_friendly(db, "op.acc.5")
    assert result is not None

    cliente_d = result.to_cliente_dict()
    assert "admin_technical_detail" not in cliente_d
    assert "familia" not in cliente_d  # admin-only field
    assert "fuente_oficial" not in cliente_d  # admin-only field
    assert "nombre" not in cliente_d  # ENS official name admin-only

    # Cliente fields ALWAYS present R29
    assert "cliente_friendly_title" in cliente_d
    assert "cliente_friendly_explanation" in cliente_d
    assert "categoria_minima" in cliente_d  # cliente puede ver categoría


# ════════════════════════════════════════════════════════════════════
# Phase 3C · Curated overrides 100% cliente-friendly enforcement
# ════════════════════════════════════════════════════════════════════


def test_curated_overrides_100_percent_cliente_friendly_spanish():
    """TRANSLATION_OVERRIDES: NO contienen ENS codigo directly visible
    (cliente-friendly title NUNCA plain codigo · explanation always primer
    principios Spanish R29)."""
    for measure_code, override in TRANSLATION_OVERRIDES.items():
        cliente_title = override["cliente_friendly_title"]
        cliente_explanation = override["cliente_friendly_explanation"]

        # NO debería mostrar plain ENS codigo en title
        # (excepto en parens · ej "Inicio de sesión seguro (MFA)" OK · pero NO "op.acc.6")
        assert measure_code not in cliente_title, (
            f"Override {measure_code} title leaks raw ENS code: {cliente_title!r}"
        )
        # NO codes ENS técnicos plain en explanation
        assert measure_code not in cliente_explanation, (
            f"Override {measure_code} explanation leaks raw ENS code: "
            f"{cliente_explanation!r}"
        )

        # Cliente-friendly tone enforcement
        assert len(cliente_title) <= 80, "Title too long for friendly UX"
        assert len(cliente_explanation) >= 30, "Explanation too short"


def test_translation_overrides_high_value_measures_present():
    """Initial seed overrides incluye high-frequency measures Marcos expertise."""
    must_have = [
        "op.acc.5",   # Cuentas seguras
        "op.acc.6",   # MFA
        "mp.s.4",     # Antivirus
        "org.4",      # Política
        "mp.info.6",  # Backup
        "op.cont.2",  # Continuidad
    ]
    for code in must_have:
        assert code in TRANSLATION_OVERRIDES, (
            f"High-frequency measure {code} missing in TRANSLATION_OVERRIDES "
            "seed (Marcos curated)"
        )


def test_measure_translation_dataclass_frozen():
    """MeasureTranslation dataclass frozen (R1 immutability)."""
    t = MeasureTranslation(
        measure_code="op.acc.6",
        nombre="Auth · MFA",
        cliente_friendly_title="Inicio de sesión seguro",
        cliente_friendly_explanation="Test",
        admin_technical_detail="Test",
    )
    with pytest.raises(Exception):
        t.measure_code = "different"  # frozen dataclass · raises
