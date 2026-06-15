"""Tests del módulo de precios LLM (§4.5 audit-2026-06-15).

Garantiza que compute_cost_usd produce un coste > 0 para interacciones reales
(antes cost_usd quedaba None → el cap mensual de coste nunca acumulaba).
"""
from backend.app.core.ai.pricing import compute_cost_usd, price_for_model


def test_price_for_model_by_family():
    assert price_for_model("claude-haiku-4-5-20251001") == (0.80, 4.00)
    assert price_for_model("claude-sonnet-4-6") == (3.00, 15.00)
    assert price_for_model("claude-opus-4-8") == (15.00, 75.00)
    # desconocido → fallback Sonnet (conservador)
    assert price_for_model("modelo-raro") == (3.00, 15.00)
    assert price_for_model(None) == (3.00, 15.00)


def test_compute_cost_usd_positive():
    # Haiku · 1000 in + 500 out = 1000*0.80/1e6 + 500*4.00/1e6
    cost = compute_cost_usd("claude-haiku-4-5", 1000, 500)
    assert cost > 0
    assert abs(cost - (1000 * 0.80 + 500 * 4.00) / 1_000_000) < 1e-9


def test_compute_cost_usd_opus_more_expensive_than_haiku():
    haiku = compute_cost_usd("claude-haiku-4-5", 10_000, 5_000)
    opus = compute_cost_usd("claude-opus-4-8", 10_000, 5_000)
    assert opus > haiku


def test_compute_cost_usd_cache_read_cheaper():
    """La lectura de caché se cobra al factor reducido (10% del input)."""
    full = compute_cost_usd("claude-sonnet-4-6", 10_000, 0, cache_read_tokens=0)
    cached = compute_cost_usd("claude-sonnet-4-6", 10_000, 0, cache_read_tokens=10_000)
    assert cached < full
    assert cached > 0


def test_compute_cost_usd_zero_tokens():
    assert compute_cost_usd("claude-haiku-4-5", 0, 0) == 0.0
