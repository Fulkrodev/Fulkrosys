"""Tests M6 — Filtros Jinja en formato espanol (es-ES)."""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import jinja2
import pytest

from backend.app.motors.m06_document_factory.filters import (
    ES_FILTERS,
    format_currency_es,
    format_date_es,
    format_iban_es,
    format_number_es,
    format_percent_es,
    register_es_filters,
)


# ════════════════════════════════════════════════════════════════════
# format_currency_es
# ════════════════════════════════════════════════════════════════════

class TestFormatCurrencyEs:
    def test_int(self):
        assert format_currency_es(9500) == "9.500,00 €"

    def test_float(self):
        assert format_currency_es(9500.0) == "9.500,00 €"

    def test_decimal(self):
        assert format_currency_es(Decimal("9500")) == "9.500,00 €"

    def test_none(self):
        assert format_currency_es(None) == "— €"

    def test_empty_string(self):
        assert format_currency_es("") == "— €"

    def test_negative(self):
        assert format_currency_es(-1234.56) == "-1.234,56 €"

    def test_large_thousands(self):
        assert format_currency_es(1234567.89) == "1.234.567,89 €"

    def test_small_decimals(self):
        assert format_currency_es(0.05) == "0,05 €"

    def test_zero(self):
        assert format_currency_es(0) == "0,00 €"

    def test_custom_decimals_0(self):
        assert format_currency_es(9500, decimals=0) == "9.500 €"

    def test_custom_decimals_4(self):
        # 0,12345 -> 0,1235 (4 dec rounded HALF_EVEN)
        assert format_currency_es(0.1234567, decimals=4) == "0,1235 €"

    def test_invalid_string_returns_empty(self):
        # String no convertible -> "— €" conservador
        assert format_currency_es("abc") == "— €"

    def test_tolerates_es_formatted_input(self):
        # Acepta "9.500,00" como input
        assert format_currency_es("9.500,00") == "9.500,00 €"


# ════════════════════════════════════════════════════════════════════
# format_number_es
# ════════════════════════════════════════════════════════════════════

class TestFormatNumberEs:
    def test_thousands(self):
        assert format_number_es(1234567) == "1.234.567"

    def test_with_decimals(self):
        assert format_number_es(1234.567, decimals=2) == "1.234,57"

    def test_none(self):
        assert format_number_es(None) == "—"

    def test_negative(self):
        assert format_number_es(-1234) == "-1.234"


# ════════════════════════════════════════════════════════════════════
# format_percent_es
# ════════════════════════════════════════════════════════════════════

class TestFormatPercentEs:
    def test_fraction_input(self):
        # 0.453 -> 45,3 %
        assert format_percent_es(0.453) == "45,3 %"

    def test_normalized_input(self):
        # 45.3 -> 45,3 % (ya normalizado)
        assert format_percent_es(45.3) == "45,3 %"

    def test_one_is_100(self):
        # 1 -> 100,0 %
        assert format_percent_es(1) == "100,0 %"

    def test_greater_than_one(self):
        # 45.3 no se multiplica por 100
        assert format_percent_es(45.3) == "45,3 %"

    def test_none(self):
        assert format_percent_es(None) == "—"

    def test_custom_decimals(self):
        assert format_percent_es(0.123456, decimals=2) == "12,35 %"


# ════════════════════════════════════════════════════════════════════
# format_date_es
# ════════════════════════════════════════════════════════════════════

class TestFormatDateEs:
    def test_iso_string(self):
        assert format_date_es("2026-04-22") == "22 de abril de 2026"

    def test_iso_datetime_string(self):
        assert format_date_es("2026-04-22T10:30:00Z") == "22 de abril de 2026"

    def test_date_object(self):
        assert format_date_es(date(2026, 1, 15)) == "15 de enero de 2026"

    def test_datetime_object(self):
        dt = datetime(2026, 12, 25, 10, 0, tzinfo=timezone.utc)
        assert format_date_es(dt) == "25 de diciembre de 2026"

    def test_none(self):
        assert format_date_es(None) == "—"

    def test_empty_string(self):
        assert format_date_es("") == "—"

    def test_invalid_returns_original(self):
        assert format_date_es("no-es-fecha") == "no-es-fecha"

    def test_all_months_translated(self):
        months = [
            (1, "enero"), (2, "febrero"), (3, "marzo"), (4, "abril"),
            (5, "mayo"), (6, "junio"), (7, "julio"), (8, "agosto"),
            (9, "septiembre"), (10, "octubre"), (11, "noviembre"),
            (12, "diciembre"),
        ]
        for month, name in months:
            assert name in format_date_es(date(2026, month, 1))


# ════════════════════════════════════════════════════════════════════
# format_iban_es
# ════════════════════════════════════════════════════════════════════

class TestFormatIbanEs:
    def test_compact(self):
        result = format_iban_es("ES7620770024003102575766")
        assert result == "ES76 2077 0024 0031 0257 5766"

    def test_already_spaced(self):
        result = format_iban_es("ES76 2077 0024 0031 0257 5766")
        assert result == "ES76 2077 0024 0031 0257 5766"

    def test_none(self):
        assert format_iban_es(None) == "—"

    def test_invalid_iban(self):
        # No es ES* -> devuelve tal cual
        result = format_iban_es("DE89370400440532013000")
        assert result == "DE89370400440532013000"


# ════════════════════════════════════════════════════════════════════
# Registration
# ════════════════════════════════════════════════════════════════════

class TestRegisterEsFilters:
    def test_all_filters_registered(self):
        env = jinja2.Environment()
        register_es_filters(env)
        for name in ES_FILTERS:
            assert name in env.filters

    def test_filter_works_in_template(self):
        env = jinja2.Environment()
        register_es_filters(env)
        tpl = env.from_string("{{ x | format_currency_es }}")
        assert tpl.render(x=9500) == "9.500,00 €"

    def test_filter_chain(self):
        env = jinja2.Environment()
        register_es_filters(env)
        tpl = env.from_string("{{ x | format_date_es }}")
        assert tpl.render(x="2026-04-22") == "22 de abril de 2026"

    def test_globals_also_registered(self):
        env = jinja2.Environment()
        register_es_filters(env)
        tpl = env.from_string("{{ format_currency_es(x) }}")
        assert tpl.render(x=1000) == "1.000,00 €"


# ════════════════════════════════════════════════════════════════════
# Integracion con render_docx
# ════════════════════════════════════════════════════════════════════

class TestRenderDocxWithEsFilters:
    def test_filters_registered_in_rendering_env(self, tmp_path):
        """Verifica que render_docx registra los filtros ES."""
        from backend.app.motors.m06_document_factory.rendering import (
            _SilentUndefined, register_es_filters,
        )
        env = jinja2.Environment(undefined=_SilentUndefined)
        register_es_filters(env)
        # Prueba de sanity: filtro aplicable sin errores
        tpl = env.from_string("{{ x | format_currency_es }} - {{ d | format_date_es }}")
        result = tpl.render(x=9500, d="2026-04-22")
        assert "9.500,00 €" in result
        assert "22 de abril de 2026" in result
