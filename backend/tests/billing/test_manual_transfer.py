"""Tests ManualTransferProvider info-mode (MB-18.2 ADR-040)."""
from __future__ import annotations

from decimal import Decimal

import pytest

from backend.app.billing.manual_transfer import (
    ManualTransferProvider,
    _format_iban_humano,
)
from backend.app.config import get_settings


@pytest.fixture(autouse=True)
def _reset_settings(monkeypatch):
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_format_iban_humano_es():
    assert _format_iban_humano("ES1212345678901234567890") == (
        "ES12 1234 5678 9012 3456 7890"
    )


def test_format_iban_humano_strips_spaces():
    raw = "ES12 1234 5678 9012 3456 7890"
    assert _format_iban_humano(raw) == "ES12 1234 5678 9012 3456 7890"


def test_format_iban_humano_uppercase():
    assert _format_iban_humano("es121234567890") == "ES12 1234 5678 90"


def test_format_iban_humano_short_returns_as_is():
    assert _format_iban_humano("es1234") == "ES1234"


def test_build_instructions_returns_none_when_iban_empty(monkeypatch):
    monkeypatch.setenv("MARCOS_BANK_IBAN", "")
    get_settings.cache_clear()
    info = ManualTransferProvider().build_instructions(
        invoice_number="FACT-2026-001",
        amount_eur=Decimal("100"),
    )
    assert info is None


def test_build_instructions_returns_data_when_iban_set(monkeypatch):
    monkeypatch.setenv("MARCOS_BANK_IBAN", "ES1212345678901234567890")
    monkeypatch.setenv("MARCOS_BANK_HOLDER", "Marcos Mata Vega")
    monkeypatch.setenv("MARCOS_BANK_INSTITUTION", "Banco Santander")
    get_settings.cache_clear()
    info = ManualTransferProvider().build_instructions(
        invoice_number="FACT-2026-042",
        amount_eur=Decimal("1500.00"),
        payment_due_date="2026-06-01",
    )
    assert info is not None
    assert info.iban == "ES12 1234 5678 9012 3456 7890"
    assert info.holder == "Marcos Mata Vega"
    assert info.institution == "Banco Santander"
    assert info.amount_eur == "1500.00"
    assert info.reference == "FACT-2026-042"
    assert info.concept == "Factura FACT-2026-042"
    assert info.payment_due_date == "2026-06-01"


def test_render_text_block_empty_when_unconfigured(monkeypatch):
    monkeypatch.setenv("MARCOS_BANK_IBAN", "")
    get_settings.cache_clear()
    block = ManualTransferProvider().render_text_block(
        invoice_number="X",
        amount_eur=Decimal("100"),
    )
    assert block == ""


def test_render_text_block_format(monkeypatch):
    monkeypatch.setenv("MARCOS_BANK_IBAN", "ES1212345678901234567890")
    get_settings.cache_clear()
    block = ManualTransferProvider().render_text_block(
        invoice_number="FACT-2026-100",
        amount_eur=Decimal("750.00"),
    )
    assert "INSTRUCCIONES PARA LA TRANSFERENCIA" in block
    assert "ES12 1234 5678 9012 3456 7890" in block
    assert "750.00 EUR" in block
    assert "FACT-2026-100" in block
    # Directiva: NO link · NO botón clipboard
    assert "<a " not in block
    assert "clipboard" not in block
    assert "https://" not in block


def test_render_html_block_no_link_no_clipboard(monkeypatch):
    monkeypatch.setenv("MARCOS_BANK_IBAN", "ES1212345678901234567890")
    get_settings.cache_clear()
    block = ManualTransferProvider().render_html_block(
        invoice_number="FACT-2026-200",
        amount_eur=Decimal("999.99"),
    )
    assert "<strong>ES12 1234 5678 9012 3456 7890</strong>" in block
    assert "<strong>FACT-2026-200</strong>" in block
    assert "<strong>999.99 EUR</strong>" in block
    # Directiva Marcos: cero link · cero botón · cero JS clipboard
    assert "<a " not in block
    assert "href=" not in block
    assert "onclick=" not in block
    assert "clipboard" not in block
    assert "navigator." not in block
    assert "target=" not in block


def test_render_html_block_includes_due_date_when_provided(monkeypatch):
    monkeypatch.setenv("MARCOS_BANK_IBAN", "ES1212345678901234567890")
    get_settings.cache_clear()
    block = ManualTransferProvider().render_html_block(
        invoice_number="X",
        amount_eur=Decimal("100"),
        payment_due_date="2026-06-15",
    )
    assert "2026-06-15" in block


def test_render_html_block_includes_bic_when_set(monkeypatch):
    monkeypatch.setenv("MARCOS_BANK_IBAN", "ES1212345678901234567890")
    monkeypatch.setenv("MARCOS_BANK_BIC", "BSCHESMM")
    get_settings.cache_clear()
    block = ManualTransferProvider().render_html_block(
        invoice_number="X",
        amount_eur=Decimal("100"),
    )
    assert "BSCHESMM" in block
