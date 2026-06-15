"""Precios LLM canónicos (USD por millón de tokens) + cálculo de coste.

§4.5 audit-2026-06-15 · fuente ÚNICA del coste por interacción. Antes cada agente
duplicaba sus constantes de precio y `cost_usd` NUNCA se persistía en
`LLMInteractionLog` → el cap mensual de coste (`copilot_rate_limit` ·
`SUM(cost_usd)`) sumaba 0 y NUNCA disparaba (el tope de dinero estaba muerto).

Match por familia (substring del id de modelo · robusto a sufijos de versión):
Anthropic Haiku 4.5 / Sonnet 4.6 / Opus 4.x.
"""
from __future__ import annotations

# (input_usd_per_mtok, output_usd_per_mtok) por familia de modelo.
MODEL_PRICE_USD: dict[str, tuple[float, float]] = {
    "haiku": (0.80, 4.00),
    "sonnet": (3.00, 15.00),
    "opus": (15.00, 75.00),
}
# Fallback conservador (Sonnet) si el id de modelo no casa ninguna familia.
_DEFAULT_PRICE: tuple[float, float] = (3.00, 15.00)

# Lectura de caché de prompt Anthropic ≈ 10% del precio de input.
_CACHE_READ_FACTOR = 0.10


def price_for_model(model: str | None) -> tuple[float, float]:
    m = (model or "").lower()
    for key, price in MODEL_PRICE_USD.items():
        if key in m:
            return price
    return _DEFAULT_PRICE


def compute_cost_usd(
    model: str | None,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0,
) -> float:
    """Coste USD de una interacción (input no-cacheado + lectura de caché + output).

    ``input_tokens`` puede o no incluir ``cache_read_tokens`` según el SDK; se
    descuenta el caché del input facturable y se cobra al factor reducido — un
    pequeño sobre/infra-conteo es aceptable (es un TOPE protector, no facturación).
    """
    in_price, out_price = price_for_model(model)
    billable_in = max(0, int(input_tokens) - int(cache_read_tokens))
    cost = (
        billable_in * in_price
        + int(cache_read_tokens) * in_price * _CACHE_READ_FACTOR
        + int(output_tokens) * out_price
    ) / 1_000_000
    return round(cost, 6)
