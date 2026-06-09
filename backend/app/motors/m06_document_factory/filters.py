"""Filtros Jinja2 en formato espanol (es-ES) para templates DOCX.

Se registran en el Environment de `render_docx` para que plantillas de
cliente-final puedan usar sintaxis `{{ value | format_currency_es }}`,
`{{ date | format_date_es }}`, etc.

Todos los filtros manejan `None` y valores vacios sin lanzar excepcion,
para que trabajen bien con `_SilentUndefined`.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any


_ES_MONTHS = [
    "", "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def _coerce_number(value: Any) -> Decimal | None:
    """Normaliza a Decimal. Devuelve None si no convertible."""
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        try:
            return Decimal(str(value))
        except Exception:
            return None
    if isinstance(value, str):
        cleaned = value.strip().replace(" ", "").replace("\u00a0", "")
        # Tolerar formato ES: "9.500,00 €" -> "9500.00"
        cleaned = cleaned.replace("€", "").replace("$", "").strip()
        if "," in cleaned and "." in cleaned:
            # formato ES: "1.234,56" → "1234.56"
            cleaned = cleaned.replace(".", "").replace(",", ".")
        elif "," in cleaned:
            cleaned = cleaned.replace(",", ".")
        try:
            return Decimal(cleaned)
        except Exception:
            return None
    return None


def _format_number_base(
    value: Any, decimals: int = 0, keep_sign: bool = True,
) -> str | None:
    """Formatea como numero ES con puntos de miles y coma decimal."""
    n = _coerce_number(value)
    if n is None:
        return None
    neg = n < 0
    abs_n = -n if neg else n
    q = Decimal(10) ** -decimals if decimals > 0 else Decimal(1)
    rounded = abs_n.quantize(q)
    entero, _, decimal_part = str(rounded).partition(".")
    # Miles: reverse + insert puntos cada 3 + reverse
    rev = entero[::-1]
    groups = [rev[i:i + 3] for i in range(0, len(rev), 3)]
    entero_es = ".".join(groups)[::-1]
    out = entero_es
    if decimals > 0:
        dec = (decimal_part or "").ljust(decimals, "0")[:decimals]
        out = f"{entero_es},{dec}"
    if neg and keep_sign:
        out = f"-{out}"
    return out


# ════════════════════════════════════════════════════════════════════
# Filtros publicos
# ════════════════════════════════════════════════════════════════════

def format_currency_es(value: Any, decimals: int = 2) -> str:
    """Formato moneda ES: `9.500,00 €`, `-1.234,56 €`, `— €` si None."""
    formatted = _format_number_base(value, decimals=decimals, keep_sign=True)
    if formatted is None:
        return "— €"
    return f"{formatted} €"


def format_number_es(value: Any, decimals: int = 0) -> str:
    """Formato numero ES: `1.234.567` o `1.234,56`."""
    formatted = _format_number_base(value, decimals=decimals, keep_sign=True)
    if formatted is None:
        return "—"
    return formatted


def format_percent_es(value: Any, decimals: int = 1) -> str:
    """Formato porcentaje ES: `45,3 %`. Acepta 0.453 o 45.3.

    Si el valor es <= 1 se asume fraccion (0.453 → 45,3 %).
    Si > 1 se asume porcentaje ya normalizado (45.3 → 45,3 %).
    """
    n = _coerce_number(value)
    if n is None:
        return "—"
    if abs(n) <= 1:
        n = n * Decimal(100)
    formatted = _format_number_base(n, decimals=decimals)
    if formatted is None:
        return "—"
    return f"{formatted} %"


def format_date_es(value: Any, with_day_name: bool = False) -> str:
    """Formato fecha ES: `22 de abril de 2026`."""
    if value is None or value == "":
        return "—"
    if isinstance(value, str):
        try:
            if "T" in value:
                dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                d = dt.date()
            else:
                d = date.fromisoformat(value[:10])
        except Exception:
            return str(value)
    elif isinstance(value, datetime):
        d = value.date()
    elif isinstance(value, date):
        d = value
    else:
        return str(value)
    return f"{d.day} de {_ES_MONTHS[d.month]} de {d.year}"


def format_iban_es(value: Any) -> str:
    """Agrupa IBAN en bloques de 4: `ES1234567890123456789012` →
    `ES12 3456 7890 1234 5678 9012`. Si no es IBAN ES valido devuelve
    el valor tal cual.
    """
    if value is None:
        return "—"
    s = str(value).replace(" ", "").replace("-", "").upper()
    if not re.match(r"^ES\d{22}$", s):
        return str(value)
    return " ".join(s[i:i + 4] for i in range(0, len(s), 4))


def _coerce_date(value: Any) -> date | None:
    """Convierte ``date`` / ``datetime`` / 'YYYY-MM-DD' / 'DD/MM/YYYY' a ``date``."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        s = value.strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                continue
    return None


def add_days_es(value: Any, days: int) -> str:
    """Suma ``days`` dias a la fecha y devuelve en formato ES ``DD/MM/YYYY``.

    Tolera None / valor invalido devolviendo cadena vacia. Paso 5.5:
    usada en P-001 para calcular la fecha de caducidad de la oferta.
    """
    from datetime import timedelta
    d = _coerce_date(value)
    if d is None:
        return ""
    return (d + timedelta(days=int(days))).strftime("%d/%m/%Y")


# ════════════════════════════════════════════════════════════════════
# Registration helper
# ════════════════════════════════════════════════════════════════════

ES_FILTERS: dict[str, Any] = {
    "format_currency_es": format_currency_es,
    "format_number_es": format_number_es,
    "format_percent_es": format_percent_es,
    "format_date_es": format_date_es,
    "format_iban_es": format_iban_es,
    "add_days_es": add_days_es,
}


def register_es_filters(env) -> None:
    """Registra los 5 filtros ES en un Jinja Environment."""
    for name, fn in ES_FILTERS.items():
        env.filters[name] = fn
        # Tambien disponibles como globals para uso `{{ format_currency_es(x) }}`
        env.globals[name] = fn


__all__ = [
    "format_currency_es", "format_number_es", "format_percent_es",
    "format_date_es", "format_iban_es", "add_days_es",
    "ES_FILTERS", "register_es_filters",
]
