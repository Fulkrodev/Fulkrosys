"""Tests core/pricing Apendice M v2.2 — Paso 6.

Precios base alineados a la FUENTE ÚNICA (BÁSICA 3.200 · MEDIA 10.700 · ALTA
22.800) · retainer R_MICRO 150 / R_LITE 300 / R_STD 700 / R_PLUS 1.200 /
R_CRITICAL 3.000. Ver backend/app/core/pricing/rules.py.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from backend.app.core.pricing import (
    BASE_PRICES,
    EXTRAS_IMPLANTACION_MEDIA,
    HITOS_BASICA,
    HITOS_MEDIA,
    HITOS_ALTA,
    PricingCalculator,
    PricingError,
    RETAINER_TIERS,
    SECTORES_REGULADOS,
    URGENCY_SURCHARGE_PCT,
    URGENCY_THRESHOLD_DAYS,
)


@pytest.fixture
def calc() -> PricingCalculator:
    return PricingCalculator()


# ══════════════════════════════════════════════════════════════════════
# Base prices + extras
# ══════════════════════════════════════════════════════════════════════


class TestImplantacionBase:
    def test_basica_base(self, calc):
        r = calc.calculate_implantacion("BASICA")
        assert r.total == Decimal("3200.00")
        assert r.extras == []

    def test_media_base(self, calc):
        r = calc.calculate_implantacion("MEDIA")
        assert r.total == Decimal("10700.00")
        assert r.extras == []

    def test_alta_base(self, calc):
        r = calc.calculate_implantacion("ALTA")
        assert r.total == Decimal("22800.00")

    def test_categoria_invalida_raises(self, calc):
        with pytest.raises(PricingError, match="categoria invalida"):
            calc.calculate_implantacion("foo")

    def test_categoria_case_insensitive(self, calc):
        r = calc.calculate_implantacion("media")
        assert r.total == Decimal("10700.00")


class TestMediaExtras:
    def test_sector_regulado_sanidad(self, calc):
        r = calc.calculate_implantacion("MEDIA", sector="sanidad")
        assert r.total == Decimal("12700.00")
        assert any(e.code == "sector_regulado" for e in r.extras)

    def test_sector_regulado_banca(self, calc):
        r = calc.calculate_implantacion("MEDIA", sector="banca")
        assert r.total == Decimal("12700.00")

    def test_sector_no_regulado(self, calc):
        r = calc.calculate_implantacion("MEDIA", sector="tecnologia")
        assert r.total == Decimal("10700.00")

    def test_multi_ubicacion_3_sedes(self, calc):
        r = calc.calculate_implantacion("MEDIA", sedes=3)
        assert r.total == Decimal("12200.00")
        assert any(e.code == "multi_ubicacion" for e in r.extras)

    def test_madurez_l0_l1(self, calc):
        r = calc.calculate_implantacion("MEDIA", madurez_pct=20)
        assert r.total == Decimal("13200.00")
        assert any(e.code == "madurez_l0_l1" for e in r.extras)

    def test_sistemas_adicionales_3(self, calc):
        r = calc.calculate_implantacion("MEDIA", sistemas_en_alcance=3)
        # base 10700 + 2 sistemas adicionales × 1200 = 13100
        assert r.total == Decimal("13100.00")

    def test_all_extras_combined(self, calc):
        r = calc.calculate_implantacion(
            "MEDIA",
            sector="sanidad",       # +2000
            sedes=2,                # +1500
            madurez_pct=15,         # +2500
            sistemas_en_alcance=2,  # +1200
        )
        # 10700 + 2000 + 1500 + 2500 + 1200 = 17900
        assert r.total == Decimal("17900.00")

    def test_basica_no_extras_applied(self, calc):
        r = calc.calculate_implantacion(
            "BASICA", sector="sanidad", sedes=3, madurez_pct=15,
        )
        # Extras no aplican a Basica segun Apendice M
        assert r.total == Decimal("3200.00")
        assert r.extras == []


# ══════════════════════════════════════════════════════════════════════
# Hitos oficiales
# ══════════════════════════════════════════════════════════════════════


class TestMilestones:
    def test_basica_tiene_3_hitos(self, calc):
        r = calc.calculate_implantacion("BASICA")
        assert len(r.hitos) == 3

    def test_basica_hito_1_30_pct(self, calc):
        r = calc.calculate_implantacion("BASICA")
        assert r.hitos[0].pct == Decimal("0.30")
        assert r.hitos[0].amount == Decimal("960.00")  # 3200 × 0.30

    def test_basica_hito_2_40_pct(self, calc):
        r = calc.calculate_implantacion("BASICA")
        assert r.hitos[1].amount == Decimal("1280.00")  # 3200 × 0.40

    def test_basica_hitos_suman_total(self, calc):
        r = calc.calculate_implantacion("BASICA")
        total = sum((h.amount for h in r.hitos), start=Decimal("0"))
        assert total == r.total

    def test_media_tiene_5_hitos(self, calc):
        r = calc.calculate_implantacion("MEDIA")
        assert len(r.hitos) == 5

    def test_media_hitos_pct(self, calc):
        r = calc.calculate_implantacion("MEDIA")
        pcts = [h.pct for h in r.hitos]
        assert pcts == [
            Decimal("0.26"), Decimal("0.21"), Decimal("0.21"),
            Decimal("0.21"), Decimal("0.11"),
        ]

    def test_media_hitos_suman_total_con_extras(self, calc):
        r = calc.calculate_implantacion("MEDIA", sector="sanidad")
        total = sum((h.amount for h in r.hitos), start=Decimal("0"))
        assert total == r.total  # 12700

    def test_media_ultimo_hito_11_pct_absorbe_redondeo(self, calc):
        # 10700 × 0.11 = 1177.00 exacto
        r = calc.calculate_implantacion("MEDIA")
        assert r.hitos[-1].amount == Decimal("1177.00")

    def test_alta_tiene_7_hitos(self, calc):
        r = calc.calculate_implantacion("ALTA")
        assert len(r.hitos) == 7

    def test_get_milestones_standalone(self, calc):
        mp = calc.get_milestones("MEDIA", Decimal("20000.00"))
        assert mp.contract_total == Decimal("20000.00")
        assert len(mp.milestones) == 5
        total = sum((h.amount for h in mp.milestones), start=Decimal("0"))
        assert total == Decimal("20000.00")

    def test_calculate_milestone_amount_by_code(self, calc):
        h = calc.calculate_milestone_amount(
            "BASICA", Decimal("3200.00"), "hito_1_firma",
        )
        assert h.amount == Decimal("960.00")

    def test_calculate_milestone_invalid_code_raises(self, calc):
        with pytest.raises(PricingError, match="milestone_code invalido"):
            calc.calculate_milestone_amount(
                "BASICA", Decimal("3200.00"), "hito_99_fake",
            )


# ══════════════════════════════════════════════════════════════════════
# Urgencia +30%
# ══════════════════════════════════════════════════════════════════════


class TestUrgencia:
    def test_urgencia_detectada_menos_42d(self, calc):
        is_u, days = calc.detect_urgency(
            firma_date=date(2026, 4, 22),
            plazo_date=date(2026, 5, 15),  # 23 dias
        )
        assert is_u is True and days == 23

    def test_no_urgencia_mas_42d(self, calc):
        is_u, days = calc.detect_urgency(
            firma_date=date(2026, 4, 22),
            plazo_date=date(2026, 7, 10),  # 79 dias
        )
        assert is_u is False and days == 79

    def test_apply_urgency_surcharge_30_pct(self, calc):
        result = calc.apply_urgency_surcharge(
            Decimal("3200.00"), is_urgent=True,
        )
        assert result == Decimal("4160.00")

    def test_no_surcharge_if_not_urgent(self, calc):
        result = calc.apply_urgency_surcharge(
            Decimal("3200.00"), is_urgent=False,
        )
        assert result == Decimal("3200.00")

    def test_implantacion_basica_urgente_integrated(self, calc):
        r = calc.calculate_implantacion("BASICA", dias_hasta_plazo=28)
        assert r.urgency_surcharge == Decimal("960.00")
        assert r.total == Decimal("4160.00")


# ══════════════════════════════════════════════════════════════════════
# Bolsa flex
# ══════════════════════════════════════════════════════════════════════


class TestBolsaFlex:
    def test_30h_sin_descuento(self, calc):
        b = calc.calculate_bolsa_flex(30)
        assert b.price_per_hour == Decimal("75.00")
        assert b.subtotal == Decimal("2250.00")
        assert b.discount_pct == Decimal("0.00")

    def test_50h_10_pct_discount(self, calc):
        b = calc.calculate_bolsa_flex(50)
        assert b.price_per_hour == Decimal("67.50")
        assert b.subtotal == Decimal("3375.00")

    def test_99h_still_10_pct(self, calc):
        b = calc.calculate_bolsa_flex(99)
        assert b.discount_pct == Decimal("0.10")

    def test_100h_15_pct_discount(self, calc):
        b = calc.calculate_bolsa_flex(100)
        assert b.price_per_hour == Decimal("63.75")
        assert b.subtotal == Decimal("6375.00")
        assert b.discount_pct == Decimal("0.15")
        assert b.discount_amount == Decimal("1125.00")

    def test_150h_15_pct(self, calc):
        b = calc.calculate_bolsa_flex(150)
        assert b.subtotal == Decimal("9562.50")
        assert b.price_per_hour == Decimal("63.75")

    def test_below_minimum_raises(self, calc):
        with pytest.raises(PricingError, match="minima"):
            calc.calculate_bolsa_flex(5)


# ══════════════════════════════════════════════════════════════════════
# Retainer tiers
# ══════════════════════════════════════════════════════════════════════


class TestRetainer:
    def test_r_std(self, calc):
        r = calc.calculate_retainer("R_STD")
        assert r.cuota_mensual == Decimal("700.00")
        assert r.total_mensual == Decimal("700.00")

    def test_r_plus_sla_24h(self, calc):
        r = calc.calculate_retainer("R_PLUS")
        assert "24 horas" in r.sla_urgente

    def test_r_critical_sla_8h(self, calc):
        r = calc.calculate_retainer("R_CRITICAL")
        assert "8 horas" in r.sla_urgente

    def test_sector_regulado_extra_r_plus(self, calc):
        r = calc.calculate_retainer("R_PLUS", sector_regulado=True)
        assert r.sector_regulado_extra == Decimal("300.00")
        assert r.total_mensual == Decimal("1500.00")

    def test_sector_regulado_no_extra_r_std(self, calc):
        # R_STD no tiene extra sector regulado
        r = calc.calculate_retainer("R_STD", sector_regulado=True)
        assert r.sector_regulado_extra == Decimal("0.00")

    def test_tier_invalido_raises(self, calc):
        with pytest.raises(PricingError, match="tier invalido"):
            calc.calculate_retainer("R_FAKE")


# ══════════════════════════════════════════════════════════════════════
# Quick scan + audit
# ══════════════════════════════════════════════════════════════════════


class TestQuickScanAndAudit:
    def test_quick_scan_1500(self, calc):
        r = calc.calculate_quick_scan()
        assert r["price"] == Decimal("1500.00")

    def test_quick_scan_with_discount_note(self, calc):
        r = calc.calculate_quick_scan(discount_if_implantation=True)
        assert "Descontable" in r["description"]
        assert r["discount_window_days"] == 30

    def test_audit_basica_2500(self, calc):
        r = calc.calculate_audit_interna("BASICA")
        assert r["price"] == Decimal("2500.00")
        assert "1 semana" in r["duration"]

    def test_audit_media_5500(self, calc):
        r = calc.calculate_audit_interna("MEDIA")
        assert r["price"] == Decimal("5500.00")


# ══════════════════════════════════════════════════════════════════════
# AAPP detection integrada
# ══════════════════════════════════════════════════════════════════════


class TestAAPPIntegration:
    def test_basica_aapp_plazo_60d(self, calc):
        r = calc.calculate_implantacion(
            "BASICA",
            cliente={"cif": "P12345678", "razon_social": "Ayto test"},
        )
        assert r.is_aapp is True
        assert r.payment_days == 60

    def test_basica_privado_plazo_30d(self, calc):
        r = calc.calculate_implantacion(
            "BASICA",
            cliente={"cif": "B12345678", "razon_social": "SL Priv"},
        )
        assert r.is_aapp is False
        assert r.payment_days == 30


# ══════════════════════════════════════════════════════════════════════
# Rules constants
# ══════════════════════════════════════════════════════════════════════


class TestRulesConstants:
    def test_base_prices_3_categories(self):
        assert set(BASE_PRICES.keys()) == {"BASICA", "MEDIA", "ALTA"}

    def test_extras_media_4_items(self):
        assert set(EXTRAS_IMPLANTACION_MEDIA.keys()) == {
            "sector_regulado", "multi_ubicacion",
            "madurez_l0_l1", "sistemas_adicionales",
        }

    def test_hitos_basica_sum_1_0(self):
        total = sum((h.pct for h in HITOS_BASICA), start=Decimal("0"))
        assert total == Decimal("1.00")

    def test_hitos_media_sum_1_0(self):
        total = sum((h.pct for h in HITOS_MEDIA), start=Decimal("0"))
        assert total == Decimal("1.00")

    def test_hitos_alta_sum_1_0(self):
        total = sum((h.pct for h in HITOS_ALTA), start=Decimal("0"))
        assert total == Decimal("1.00")

    def test_retainer_tiers_5(self):
        assert len(RETAINER_TIERS) == 5
        assert set(RETAINER_TIERS.keys()) == {
            "R_MICRO", "R_LITE", "R_STD", "R_PLUS", "R_CRITICAL",
        }

    def test_urgency_pct_30(self):
        assert URGENCY_SURCHARGE_PCT == Decimal("0.30")

    def test_urgency_threshold_42d(self):
        assert URGENCY_THRESHOLD_DAYS == 42

    def test_sectores_regulados_coverage(self):
        assert "sanidad" in SECTORES_REGULADOS
        assert "banca" in SECTORES_REGULADOS
        assert "fintech" in SECTORES_REGULADOS
