"""Cálculo intereses morosidad Ley 3/2004 · SAN-C MB-11.3.

Spec legal: Ley 3/2004 de medidas de lucha contra la morosidad en las
operaciones comerciales (modificada por Ley 11/2013 + Ley 18/2022):
- Plazo pago AAPP: 30 días desde conformidad de factura
- Si AAPP paga después del plazo: interés legal aplicable
- Tipo: BCE rate + 8 puntos porcentuales (norma vigente 2024+)
- Cómputo diario sobre amount_eur de la factura

BCE rate fuente oficial: ECB Monetary Policy Decisions (semestral).
``get_bce_rate()`` devuelve tipo de referencia más reciente conocido
(actualizable via override env var FULKRO_BCE_RATE_OVERRIDE).
"""
from __future__ import annotations

import os
from datetime import date
from decimal import Decimal


# Tipo BCE actualizado periódicamente (BCE pubica semestral).
# Default conservador: tipo de referencia BCE Q1 2026 ~ 4.50%
_DEFAULT_BCE_RATE_PCT = Decimal("4.50")
_LEY_3_2004_PUNTOS_ADICIONALES = Decimal("8.00")
_DAYS_IN_YEAR = Decimal("365")


def get_bce_rate_pct() -> Decimal:
    """Tipo BCE en porcentaje. Override vía env var para tests/calibración."""
    override = os.environ.get("FULKRO_BCE_RATE_OVERRIDE")
    if override:
        try:
            return Decimal(override)
        except (ValueError, ArithmeticError):
            pass
    return _DEFAULT_BCE_RATE_PCT


def calculate_late_interest(
    *,
    amount_eur: Decimal,
    payment_due_date: date,
    paid_at: date | None = None,
    today: date | None = None,
) -> Decimal:
    """Calcula intereses morosidad Ley 3/2004 (BCE + 8 puntos).

    Args:
        amount_eur: Importe factura.
        payment_due_date: Fecha límite pago (30 días desde conformidad).
        paid_at: Fecha pago real (None si aún no pagada).
        today: Fecha referencia cálculo (default date.today() · permite
            override para tests deterministic).

    Returns:
        Intereses owed en euros (Decimal 2 decimales). 0 si no
        excedido plazo o si paid_at <= payment_due_date.
    """
    ref_date = paid_at or today or date.today()
    if ref_date <= payment_due_date:
        return Decimal("0.00")

    days_late = (ref_date - payment_due_date).days
    annual_rate_pct = get_bce_rate_pct() + _LEY_3_2004_PUNTOS_ADICIONALES
    # interés = amount * rate% * days/365
    interest = (
        amount_eur * (annual_rate_pct / Decimal("100")) * Decimal(days_late)
        / _DAYS_IN_YEAR
    )
    return interest.quantize(Decimal("0.01"))
