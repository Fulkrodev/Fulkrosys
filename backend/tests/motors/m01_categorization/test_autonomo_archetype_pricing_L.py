"""FRENTE L · perfil INDIVIDUAL/autónomo · arquetipo (L-4) + pricing (L-7).

Dimensión ortogonal a la categoría ENS (NO nueva categoría · respeta 1=1).
Sin migración (reusa tamano_empleados/n_empleados existentes).
"""
from __future__ import annotations

from decimal import Decimal

from backend.app.core.pricing.rules import (
    BASE_PRICES_CANONICAL,
    calculate_for_autonomo,
)
from backend.app.motors.m01_categorization.pyme_archetypes import (
    PymeArquetipo,
    classify_archetype,
)


# ── L-4 · arquetipo AUTONOMO_INDIVIDUAL ──────────────────────────────

def test_l4_autonomo_by_n_empleados():
    r = classify_archetype({"n_empleados": 1, "infrastructure_type": "saas_only"})
    # infra saas_only tiene prioridad (regla 5) → SAAS_ONLY, no autónomo.
    # Para aislar el arquetipo autónomo usamos infra híbrida/desconocida:
    r2 = classify_archetype({"n_empleados": 3})
    assert r2.arquetipo == PymeArquetipo.AUTONOMO_INDIVIDUAL
    assert r2.confidence == Decimal("0.80")


def test_l4_autonomo_by_tamano_micro():
    r = classify_archetype({"tamano_empleados": "micro"})
    assert r.arquetipo == PymeArquetipo.AUTONOMO_INDIVIDUAL


def test_l4_autonomo_excluded_when_on_premise():
    r = classify_archetype({"n_empleados": 2, "infrastructure_type": "on_prem"})
    # con infra on-premise NO es autónomo cloud-ligero → fallback genérico
    assert r.arquetipo == PymeArquetipo.GENERICO


def test_l4_sector_takes_priority_over_autonomo():
    # un autónomo del sector salud → SECTOR_SALUD (sector tiene prioridad)
    r = classify_archetype({"n_empleados": 1, "cnae_code": "8690"})
    assert r.arquetipo == PymeArquetipo.SECTOR_SALUD


def test_l4_large_company_not_autonomo():
    r = classify_archetype({"n_empleados": 80})
    assert r.arquetipo != PymeArquetipo.AUTONOMO_INDIVIDUAL


# ── L-7 · pricing autónomo (descuento sobre canonical · ENAC externo aparte) ──

def test_l7_basica_discount_25_no_enac_disclaimer():
    p = calculate_for_autonomo("BASICA")
    assert p.discount_pct == Decimal("0.25")
    assert p.final_price == BASE_PRICES_CANONICAL["BASICA"] * Decimal("0.75")
    assert p.perfil_autonomo_discount_applied is True
    assert p.enac_external_disclaimer is None  # BÁSICA = autodeclaración, sin ENAC


def test_l7_media_discount_35_with_enac_disclaimer():
    p = calculate_for_autonomo("MEDIA")
    assert p.discount_pct == Decimal("0.35")
    assert p.final_price == BASE_PRICES_CANONICAL["MEDIA"] * Decimal("0.65")
    assert p.perfil_autonomo_discount_applied is True
    assert p.enac_external_disclaimer is not None
    assert "ENAC" in p.enac_external_disclaimer


def test_l7_alta_no_discount_but_disclaimer():
    p = calculate_for_autonomo("ALTA")
    assert p.discount_pct == Decimal("0.00")
    assert p.final_price == BASE_PRICES_CANONICAL["ALTA"]  # ALTA sin descuento
    assert p.perfil_autonomo_discount_applied is False
    assert p.enac_external_disclaimer is not None


def test_l7_canonical_prices_untouched():
    # el descuento NO modifica el pricing canónico (additive)
    assert BASE_PRICES_CANONICAL["BASICA"] == Decimal("3200.00")
    assert BASE_PRICES_CANONICAL["MEDIA"] == Decimal("10700.00")
    assert BASE_PRICES_CANONICAL["ALTA"] == Decimal("22800.00")
