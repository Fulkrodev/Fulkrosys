"""Pricing catalog (Apéndice M spec v2.1) — modelos económicos deterministas.

5 modelos precargados para calcular propuestas en segundos.
Importes calculados vía fórmula determinista. El LLM nunca inventa precios.
"""
from __future__ import annotations

from typing import Any

from decimal import Decimal

from backend.app.core.pricing.calculator import PricingCalculator
from backend.app.core.pricing.rules import (
    BASE_PRICES_CEILING_CANONICAL,
    RETAINER_SECTOR_REGULADO_EXTRA,
    RETAINER_TIERS,
    get_base_prices,
)


# Los modelos NO llevan formula propia. Hasta 2026-09-23 la llevaban (recargos
# por empleado, sistemas a partir del 3º/4º/6º, CPDs, bonus de exito, pentest
# continuo) y daban un precio distinto del de la tarifa canonica para el mismo
# cliente: MEDIA con 30 empleados, 4 sistemas y sector regulado salia a 14.650 €
# aqui y a 16.300 € en docs/pricing/CANONICAL_PRICING.md. Ahora base, extras,
# rangos e hitos salen de ``core/pricing`` (PricingCalculator), la misma
# calculadora que usa el resto del sistema. Lo que queda aqui es solo el
# nombre comercial de cada modelo.
PRICING_CATALOG: list[dict[str, Any]] = [
    {
        "id": "basica_fijo",
        "nombre": "Básica — Precio fijo",
        "descripcion": "Ideal para clientes ENS categoría BÁSICA sin alcance complejo.",
        "aplicable_categoria": ["BASICA"],
    },
    {
        "id": "media_hitos",
        "nombre": "Media — Por hitos",
        "descripcion": "Para ENS categoría MEDIA. Pago por hitos entregables.",
        "aplicable_categoria": ["MEDIA"],
    },
    {
        "id": "alta_fases_exito",
        "nombre": "Alta — Por fases",
        "descripcion": "Para ENS categoría ALTA. Pago por fases hasta la certificación.",
        "aplicable_categoria": ["ALTA"],
    },
    {
        "id": "retainer_basico",
        "nombre": "Retainer Básico post-certificación",
        "descripcion": "Mantenimiento mensual post-certificación.",
        "aplicable_categoria": ["BASICA", "MEDIA"],
    },
    {
        "id": "retainer_premium",
        "nombre": "Retainer Premium",
        "descripcion": "Mantenimiento con pentest anual incluido.",
        "aplicable_categoria": ["MEDIA", "ALTA"],
    },
]


IVA_DEFAULT = 21.0

_CALC = PricingCalculator()


# ── FUENTE ÚNICA DE PRECIOS (2026-06-11) ──────────────────────────────
# El catálogo comercial NO tiene precios base propios: los DERIVA de la fuente
# única (``rules.get_base_prices`` = pricing_config en runtime) para implantación
# y de ``RETAINER_TIERS`` para retainer. Así, editar el precio en
# /admin/settings/pricing se propaga también a este catálogo (antes media_hitos
# tenía 22.000 "sombra" hardcoded · ahora imposible).
_PROJECT_MODEL_CATEGORY = {
    "basica_fijo": "BASICA",
    "media_hitos": "MEDIA",
    "alta_fases_exito": "ALTA",
}
_RETAINER_MODEL_TIER = {
    "retainer_basico": "R_STD",
    "retainer_premium": "R_PLUS",
}


def _hitos_canonicos(categoria: str, total: Decimal) -> list[dict]:
    """Hitos de pago de la tarifa canonica, con las dos familias de claves.

    ``nombre``/``importe``/``pct`` (0-100) son las que ya leian las propuestas;
    ``code``/``description``/``amount`` son las que exige la facturacion por
    codigo de hito (m15 ``billing_service``). Antes las propuestas de m13 solo
    traian las primeras y no se podian facturar por codigo.
    """
    salida = []
    for h in _CALC._compute_milestones(categoria, total):
        salida.append({
            "nombre": h.code,
            "code": h.code,
            "description": h.description,
            "pct": float(h.pct_display),
            "importe": float(h.amount),
            "amount": float(h.amount),
        })
    return salida


def _refresh_model_from_single_source(model: dict) -> dict:
    """Copia el modelo con base, rangos e hitos de la fuente unica.

    NO muta el ``PRICING_CATALOG`` module-level (copia defensiva). Proyecto:
    base = ``get_base_prices`` (pricing_config en runtime), rango hasta el
    techo canonico, hitos oficiales de la categoria. Retainer: cuota del tier.
    """
    m = dict(model)
    cat = _PROJECT_MODEL_CATEGORY.get(m["id"])
    if cat:
        base = Decimal(str(get_base_prices()[cat]))
        m["categoria"] = cat
        m["base"] = float(base)
        m["rango_min"] = float(base)
        m["rango_max"] = float(BASE_PRICES_CEILING_CANONICAL[cat])
        m["hitos_pago"] = _hitos_canonicos(cat, base)
        return m
    tier = _RETAINER_MODEL_TIER[m["id"]]
    mensual = float(RETAINER_TIERS[tier].cuota_mensual)
    m["tier"] = tier
    m["mensual"] = mensual
    m["rango_min"] = mensual
    m["rango_max"] = mensual + float(RETAINER_SECTOR_REGULADO_EXTRA) if tier in (
        "R_PLUS", "R_CRITICAL",
    ) else mensual
    m["hitos_pago"] = [{"nombre": "mensual", "pct": 100.0}]
    return m


class PricingModelNotFoundError(ValueError):
    pass


class PricingService:
    """Calcula importes de propuestas desde modelos in-memory (Apéndice M).

    Los precios base se derivan de la FUENTE ÚNICA (pricing_config → BASE_PRICES /
    RETAINER_TIERS) en cada instanciación, de modo que reflejan el valor vigente
    editado por Marcos sin precios "sombra" divergentes.
    """

    def __init__(self):
        self._catalog = [_refresh_model_from_single_source(m) for m in PRICING_CATALOG]
        self._by_id = {m["id"]: m for m in self._catalog}

    def get_model(self, model_id: str) -> dict:
        if model_id not in self._by_id:
            raise PricingModelNotFoundError(f"Pricing model '{model_id}' no existe")
        return self._by_id[model_id]

    def get_models_for_categoria(self, categoria: str) -> list[dict]:
        cat = (categoria or "").upper()
        return [m for m in self._catalog if cat in m["aplicable_categoria"]]

    def list_all(self) -> list[dict]:
        return list(self._catalog)

    def calculate_price(
        self,
        model_id: str,
        empleados: int = 0,
        sistemas: int = 0,
        ubicaciones: int = 1,
        sector_regulado: bool = False,
        cpds: int = 0,
        meses_retainer: int = 1,
        pentest_continuo: bool = False,
        iva_percent: float = IVA_DEFAULT,
    ) -> dict:
        """Importe total + desglose + hitos + IVA, calculados por la tarifa canonica.

        Determinista: mismos inputs, mismos outputs. Delega en
        ``PricingCalculator`` (core/pricing): la tarifa tiene UN solo camino.

        ``empleados``, ``cpds`` y ``pentest_continuo`` se siguen aceptando (van
        al alcance de la propuesta) pero NO mueven el precio: la tarifa canonica
        no cobra por ellos. En proyecto solo MEDIA lleva extras (sector
        regulado, mas de una sede, sistemas a partir del 2º); en retainer, el
        extra de sector regulado desde R_PLUS.
        """
        model = self.get_model(model_id)
        extras: list[dict] = []

        if model_id in _RETAINER_MODEL_TIER:
            ret = _CALC.calculate_retainer(
                _RETAINER_MODEL_TIER[model_id], sector_regulado=sector_regulado,
            )
            meses = max(1, int(meses_retainer))
            base = float(ret.cuota_mensual)
            if ret.sector_regulado_extra > 0:
                extras.append({
                    "concepto": "Recargo sector regulado (mensual)",
                    "importe": float(ret.sector_regulado_extra) * meses,
                })
            if meses > 1:
                extras.append({
                    "concepto": f"Retainer mensual (×{meses} meses)",
                    "importe": base * (meses - 1),
                })
            total_sin_iva = float(ret.total_mensual) * meses
            hitos = [{"nombre": "mensual", "pct": 100.0, "importe": total_sin_iva}]
        else:
            imp = _CALC.calculate_implantacion(
                _PROJECT_MODEL_CATEGORY[model_id],
                sistemas_en_alcance=max(1, int(sistemas)),
                sedes=max(1, int(ubicaciones)),
                sector_regulado=sector_regulado,
            )
            base = float(imp.base)
            extras = [
                {"concepto": e.description, "importe": float(e.amount)}
                for e in imp.extras
            ]
            total_sin_iva = float(imp.total)
            hitos = _hitos_canonicos(imp.categoria, imp.total)

        total_sin_iva = round(total_sin_iva, 2)
        iva_importe = round(total_sin_iva * iva_percent / 100, 2)
        total_con_iva = round(total_sin_iva + iva_importe, 2)

        return {
            "model_id": model_id,
            "model_nombre": model["nombre"],
            "base": base,
            "extras": extras,
            "total": total_sin_iva,
            "iva_percent": iva_percent,
            "iva_importe": iva_importe,
            "total_con_iva": total_con_iva,
            "hitos": hitos,
            "rango_min": model["rango_min"],
            "rango_max": model["rango_max"],
        }
