"""Tests WhatsAppInfoFormatter modo informativo (MB-16.3 ADR-039 fix)."""
from __future__ import annotations

import pytest

from backend.app.config import get_settings
from backend.app.notifications import WhatsAppInfoFormatter


@pytest.fixture(autouse=True)
def _reset_settings(monkeypatch):
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_format_returns_none_when_unset(monkeypatch):
    monkeypatch.setenv("MARCOS_WHATSAPP_NUMBER", "")
    get_settings.cache_clear()
    assert WhatsAppInfoFormatter().format() is None


def test_format_with_plus_prefix_es(monkeypatch):
    monkeypatch.setenv("MARCOS_WHATSAPP_NUMBER", "+34666123456")
    get_settings.cache_clear()
    info = WhatsAppInfoFormatter().format()
    assert info is not None
    assert info.number == "+34 666 123 456"
    assert info.hours == "de 9:00 a 18:00 L-V"


def test_format_with_plus_prefix_3digits(monkeypatch):
    monkeypatch.setenv("MARCOS_WHATSAPP_NUMBER", "+351912345678")
    get_settings.cache_clear()
    info = WhatsAppInfoFormatter().format()
    assert info is not None
    assert info.number == "+351 912 345 678"


def test_format_no_plus_kept_as_digits(monkeypatch):
    monkeypatch.setenv("MARCOS_WHATSAPP_NUMBER", "34666123456")
    get_settings.cache_clear()
    info = WhatsAppInfoFormatter().format()
    assert info is not None
    assert "34666123456" in info.number


def test_format_strips_whitespace(monkeypatch):
    monkeypatch.setenv("MARCOS_WHATSAPP_NUMBER", "  +34666123456  ")
    get_settings.cache_clear()
    info = WhatsAppInfoFormatter().format()
    assert info is not None
    assert info.number.startswith("+34 ")


def test_format_custom_hours(monkeypatch):
    monkeypatch.setenv("MARCOS_WHATSAPP_NUMBER", "+34666123456")
    monkeypatch.setenv(
        "MARCOS_WHATSAPP_HOURS", "lunes a viernes 8h-20h CET",
    )
    get_settings.cache_clear()
    info = WhatsAppInfoFormatter().format()
    assert info is not None
    assert info.hours == "lunes a viernes 8h-20h CET"


def test_render_text_block_empty_when_unset(monkeypatch):
    monkeypatch.setenv("MARCOS_WHATSAPP_NUMBER", "")
    get_settings.cache_clear()
    assert WhatsAppInfoFormatter().render_text_block() == ""


def test_render_text_block_format(monkeypatch):
    monkeypatch.setenv("MARCOS_WHATSAPP_NUMBER", "+34666123456")
    get_settings.cache_clear()
    block = WhatsAppInfoFormatter().render_text_block()
    assert "📞 ¿Prefieres WhatsApp?" in block
    assert "+34 666 123 456" in block
    assert "(de 9:00 a 18:00 L-V)" in block
    assert "wa.me" not in block
    assert "https://" not in block


def test_render_html_block_empty_when_unset(monkeypatch):
    monkeypatch.setenv("MARCOS_WHATSAPP_NUMBER", "")
    get_settings.cache_clear()
    assert WhatsAppInfoFormatter().render_html_block() == ""


def test_render_html_block_no_link_no_target(monkeypatch):
    """Directiva Marcos: NO link · NO href · NO target_blank."""
    monkeypatch.setenv("MARCOS_WHATSAPP_NUMBER", "+34666123456")
    get_settings.cache_clear()
    block = WhatsAppInfoFormatter().render_html_block()
    assert "<strong>+34 666 123 456</strong>" in block
    assert "<hr>" in block
    assert "color:#666" in block
    assert "<a " not in block
    assert "href=" not in block
    assert "wa.me" not in block
    assert "target=" not in block
    assert "onclick=" not in block


def test_render_text_block_starts_with_separator(monkeypatch):
    """Bloque texto plano comienza con --- separator."""
    monkeypatch.setenv("MARCOS_WHATSAPP_NUMBER", "+34666123456")
    get_settings.cache_clear()
    block = WhatsAppInfoFormatter().render_text_block()
    assert block.startswith("\n---\n")
