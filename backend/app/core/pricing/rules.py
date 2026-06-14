"""Reglas deterministas del pricing oficial FULKRO Apendice M v2.2.

Separar reglas de calculo (calculator.py) para facilitar tests y
reutilizacion. Todos los importes son ``Decimal`` para evitar errores
de redondeo en facturacion fiscal.

FUENTE ÚNICA DE PRECIOS (2026-06-11 · unificación): existe UN solo juego de
precios de implantación en todo el sistema, los valores vigentes de Marcos
(BÁSICA 3.200 · MEDIA 10.700 · ALTA 22.800). Estos constants son el default de
código y coinciden EXACTAMENTE con:
  - la tabla ``pricing_config`` (BD · editable desde /admin/settings/pricing),
  - el catálogo comercial ``m13_commercial/pricing_service.py`` (deriva de aquí),
  - el seed ``m23_retainer/pricing_catalog_seed.py``.
Al arranque, ``repository.refresh_pricing_from_db`` recarga ``pricing_config``
sobre estas constantes vía ``apply_pricing_overrides`` (mutación IN-PLACE), de
modo que editar el precio en la UI lo propaga a TODOS los consumidores
(calculator, catálogo m13, agents 19/20, propuesta, factura) sin tocar
call-sites. No quedan precios "sombra" divergentes.
"""
from __future__ import annotations

from decimal import Decimal
from typing import NamedTuple


# ══════════════════════════════════════════════════════════════════════
# Precios base por categoria ENS · FUENTE ÚNICA (2026-06-11)
# ══════════════════════════════════════════════════════════════════════
# Valores vigentes de Marcos · coinciden con pricing_config (BD), el catálogo
# m13 (deriva de aquí) y el seed m23. ``BASE_PRICES`` == ``BASE_PRICES_CANONICAL``:
# un solo número por categoría en todo el sistema. ``apply_pricing_overrides``
# recarga pricing_config sobre estas constantes al arranque y tras cada edición
# admin, propagando el cambio a todos los consumidores.
BASE_PRICES: dict[str, Decimal] = {
    "BASICA": Decimal("3200.00"),
    "MEDIA": Decimal("10700.00"),
    "ALTA": Decimal("22800.00"),
}

# Alias canónico (mismos valores · preservado para call-sites existentes).
BASE_PRICES_CANONICAL: dict[str, Decimal] = {
    "BASICA": Decimal("3200.00"),
    "MEDIA": Decimal("10700.00"),
    "ALTA": Decimal("22800.00"),
}

# Ceiling sector complejo (sanidad/finanzas/AAPP critica · multiplier 1.2-1.4x)
BASE_PRICES_CEILING_CANONICAL: dict[str, Decimal] = {
    "BASICA": Decimal("4500.00"),
    "MEDIA": Decimal("13000.00"),
    "ALTA": Decimal("28000.00"),
}


def apply_pricing_overrides(prices: dict) -> None:
    """Sobre-escribe IN-PLACE los precios base con los de pricing_config (BD).

    FIX P4-1: fuente única editable. Llamado al arranque y tras cada edición
    admin. Muta BASE_PRICES + BASE_PRICES_CANONICAL en el sitio para que los
    consumidores que hacen ``BASE_PRICES[cat]`` reflejen el valor vigente sin
    cambiar sus call-sites. Solo claves válidas (BASICA/MEDIA/ALTA).
    """
    for cat in ("BASICA", "MEDIA", "ALTA"):
        v = prices.get(cat) if hasattr(prices, "get") else None
        if v is not None:
            dv = Decimal(str(v))
            BASE_PRICES[cat] = dv
            BASE_PRICES_CANONICAL[cat] = dv


def get_base_prices() -> dict[str, Decimal]:
    """Copia de los precios base vigentes (post-overrides)."""
    return dict(BASE_PRICES)


# ══════════════════════════════════════════════════════════════════════
# L-7 (FRENTE L) · descuento perfil AUTÓNOMO / microempresa
# ══════════════════════════════════════════════════════════════════════
# Dimensión ORTOGONAL a la categoría ENS (NO nueva categoría · respeta 1=1).
# Marco documental ligero + menor dedicación → descuento sobre el canonical.
# BÁSICA -25% · MEDIA -35% · ALTA 0% (ENS ALTA para un autónomo es anómalo ·
# sin descuento · requiere revisión Marcos). El auditor ENAC externo NUNCA va
# incluido (coste del cliente) · disclaimer obligatorio en MEDIA/ALTA.
SIZE_DISCOUNT_MICRO: dict[str, Decimal] = {
    "BASICA": Decimal("0.25"),
    "MEDIA": Decimal("0.35"),
    "ALTA": Decimal("0.00"),
}

AUTONOMO_ENAC_DISCLAIMER = (
    "El auditor ENAC externo NO está incluido en el precio (coste a cargo del "
    "cliente · 600-2.000 € según alcance)."
)


class AutonomoPricing(NamedTuple):
    categoria: str
    base_price: Decimal
    discount_pct: Decimal
    discount_amount: Decimal
    final_price: Decimal
    enac_external_disclaimer: str | None
    perfil_autonomo_discount_applied: bool


def calculate_for_autonomo(categoria: str) -> AutonomoPricing:
    """L-7 · precio para perfil autónomo/microempresa sobre BASE_PRICES_CANONICAL.

    Aplica ``SIZE_DISCOUNT_MICRO``. NO modifica el pricing canónico (additive ·
    es un cálculo aparte). Trazabilidad: ``perfil_autonomo_discount_applied`` =
    True sólo cuando hay descuento real (>0). En MEDIA/ALTA añade el disclaimer
    de auditor ENAC externo no incluido.
    """
    cat = (categoria or "").upper().strip()
    if cat not in BASE_PRICES_CANONICAL:
        raise ValueError(f"Categoría desconocida para pricing autónomo: {categoria}")
    base = BASE_PRICES_CANONICAL[cat]
    pct = SIZE_DISCOUNT_MICRO.get(cat, Decimal("0.00"))
    discount = (base * pct).quantize(Decimal("0.01"))
    final = base - discount
    disclaimer = AUTONOMO_ENAC_DISCLAIMER if cat in {"MEDIA", "ALTA"} else None
    return AutonomoPricing(
        categoria=cat,
        base_price=base,
        discount_pct=pct,
        discount_amount=discount,
        final_price=final,
        enac_external_disclaimer=disclaimer,
        perfil_autonomo_discount_applied=pct > 0,
    )

# Rango horas estimado de dedicacion Marcos por categoria
HOURS_RANGE: dict[str, tuple[int, int]] = {
    "BASICA": (30, 40),
    "MEDIA": (80, 110),
    "ALTA": (150, 200),  # co-consultoria con partner senior
}


# ══════════════════════════════════════════════════════════════════════
# Extras implantacion MEDIA
# ══════════════════════════════════════════════════════════════════════


EXTRAS_IMPLANTACION_MEDIA: dict[str, Decimal] = {
    "sector_regulado": Decimal("2000.00"),
    "multi_ubicacion": Decimal("1500.00"),
    "madurez_l0_l1": Decimal("2500.00"),
    "sistemas_adicionales": Decimal("1200.00"),  # por sistema extra
}

EXTRAS_DESCRIPTIONS: dict[str, str] = {
    "sector_regulado": "Sector regulado (sanidad, banca, fintech, energia critica)",
    "multi_ubicacion": "Multi-ubicacion (>1 sede en alcance)",
    "madurez_l0_l1": "Madurez inicial L0/L1 (diagnostico <30%)",
    "sistemas_adicionales": "Sistemas adicionales en alcance (>1 sistema)",
}

SECTORES_REGULADOS: frozenset[str] = frozenset({
    "sanidad",
    "sanidad_publica",
    "sanidad_privada",
    "banca",
    "fintech",
    "seguros",
    "energia",
    "energia_critica",
    "transporte_critico",
    "infraestructuras_criticas",
    "defensa",
    "nuclear",
    "telecomunicaciones_criticas",
})

MADUREZ_L0_L1_THRESHOLD_PCT = 30  # M22 diagnosis_score < 30 → L0/L1


# ══════════════════════════════════════════════════════════════════════
# Hitos de facturacion
# ══════════════════════════════════════════════════════════════════════


class MilestoneSpec(NamedTuple):
    code: str
    pct: Decimal
    description: str


HITOS_BASICA: tuple[MilestoneSpec, ...] = (
    MilestoneSpec("hito_1_firma", Decimal("0.30"), "Firma del contrato"),
    MilestoneSpec(
        "hito_2_dda_politicas", Decimal("0.40"),
        "DdA + Politicas aprobadas (semana 3)",
    ),
    MilestoneSpec(
        "hito_3_dossier_entregado", Decimal("0.30"),
        "Dossier entregado (semana 5-6)",
    ),
)

HITOS_MEDIA: tuple[MilestoneSpec, ...] = (
    MilestoneSpec("hito_1_firma", Decimal("0.26"), "Firma del contrato"),
    MilestoneSpec(
        "hito_2_diagnostico_ar", Decimal("0.21"),
        "Diagnostico + AR MAGERIT completado (semana 3)",
    ),
    MilestoneSpec(
        "hito_3_dda_sgsi", Decimal("0.21"),
        "DdA + SGSI aprobado (semana 5)",
    ),
    MilestoneSpec(
        "hito_4_dossier_auditor", Decimal("0.21"),
        "Dossier entregado al auditor ENAC (semana 8-10)",
    ),
    MilestoneSpec(
        "hito_5_certificacion", Decimal("0.11"),
        "Certificacion ENAC obtenida",
    ),
)

HITOS_ALTA: tuple[MilestoneSpec, ...] = (
    MilestoneSpec("hito_1_firma", Decimal("0.15"), "Firma del contrato"),
    MilestoneSpec(
        "hito_2_diagnostico", Decimal("0.15"),
        "Diagnostico inicial (semana 3)",
    ),
    MilestoneSpec(
        "hito_3_magerit_dda", Decimal("0.15"),
        "MAGERIT + DdA aprobados (semana 6)",
    ),
    MilestoneSpec(
        "hito_4_politicas_procedimientos", Decimal("0.15"),
        "Politicas + procedimientos firmados (semana 10)",
    ),
    MilestoneSpec(
        "hito_5_implantacion_tecnica", Decimal("0.15"),
        "Implantacion tecnica completada (semana 16)",
    ),
    MilestoneSpec(
        "hito_6_dossier_auditor", Decimal("0.15"),
        "Dossier entregado al auditor ENAC (semana 20)",
    ),
    MilestoneSpec(
        "hito_7_certificacion", Decimal("0.10"),
        "Certificacion ENAC obtenida",
    ),
)

HITOS_BY_CATEGORIA: dict[str, tuple[MilestoneSpec, ...]] = {
    "BASICA": HITOS_BASICA,
    "MEDIA": HITOS_MEDIA,
    "ALTA": HITOS_ALTA,
}


# ══════════════════════════════════════════════════════════════════════
# Garantias comerciales por categoria
# ══════════════════════════════════════════════════════════════════════


GARANTIAS_COMERCIALES: dict[str, str] = {
    "BASICA": (
        "Remediacion de no conformidades gratuita: si tras la "
        "autoevaluacion Basica se detectan no conformidades imputables "
        "al consultor, su subsanacion se realizara sin coste adicional "
        "para el cliente."
    ),
    "MEDIA": (
        "Garantia de certificacion: si no se obtiene la certificacion "
        "ENAC por razon imputable exclusivamente al consultor, el "
        "importe del ultimo hito de certificacion no se cobrara. El "
        "consultor continuara prestando los servicios necesarios hasta "
        "obtener la certificacion sin coste adicional."
    ),
    "ALTA": (
        "Alianza con partner senior: el proyecto se ejecuta en "
        "co-consultoria con partner con experiencia ENAC contrastada "
        "(50/50 o 60/40 segun alcance), garantizando capacidad tecnica "
        "y cobertura durante todo el proyecto."
    ),
}


# ══════════════════════════════════════════════════════════════════════
# Bolsa flex horas consultoria
# ══════════════════════════════════════════════════════════════════════


class BolsaFlexTier(NamedTuple):
    max_hours: int | float   # inclusive
    price_per_hour: Decimal
    discount_pct: Decimal


BOLSA_FLEX_TIERS: tuple[BolsaFlexTier, ...] = (
    BolsaFlexTier(49, Decimal("75.00"), Decimal("0.00")),
    BolsaFlexTier(99, Decimal("67.50"), Decimal("0.10")),
    BolsaFlexTier(float("inf"), Decimal("63.75"), Decimal("0.15")),
)

BOLSA_FLEX_MIN_HOURS = 10  # minimo contratable
BOLSA_FLEX_BASE_PRICE = Decimal("75.00")  # precio sin descuento


# ══════════════════════════════════════════════════════════════════════
# Urgencia
# ══════════════════════════════════════════════════════════════════════


URGENCY_SURCHARGE_PCT: Decimal = Decimal("0.30")  # +30%
URGENCY_THRESHOLD_DAYS: int = 42                   # <6 semanas


# ══════════════════════════════════════════════════════════════════════
# Quick scan pre-auditoria
# ══════════════════════════════════════════════════════════════════════


QUICK_SCAN_PRICE: Decimal = Decimal("1500.00")
QUICK_SCAN_DISCOUNT_WINDOW_DAYS = 30  # descuento si firma en 30d


# ══════════════════════════════════════════════════════════════════════
# Auditoria interna independiente
# ══════════════════════════════════════════════════════════════════════


AUDIT_INTERNA_PRICES: dict[str, Decimal] = {
    "BASICA": Decimal("2500.00"),
    "MEDIA": Decimal("5500.00"),
    "ALTA": Decimal("9500.00"),
}

AUDIT_INTERNA_DURATIONS: dict[str, str] = {
    "BASICA": "1 semana",
    "MEDIA": "2 semanas",
    "ALTA": "3-4 semanas",
}


# ══════════════════════════════════════════════════════════════════════
# Retainer tiers post-certificacion
# ══════════════════════════════════════════════════════════════════════


class RetainerTier(NamedTuple):
    code: str
    cuota_mensual: Decimal
    horas_mensuales: int
    horas_anuales: int
    sla_urgente: str
    sla_ordinario: str
    tarifa_hora_adicional: Decimal


RETAINER_TIERS: dict[str, RetainerTier] = {
    "R_MICRO": RetainerTier(
        code="R_MICRO",
        cuota_mensual=Decimal("150.00"),
        horas_mensuales=1,
        horas_anuales=12,
        sla_urgente="best effort",
        sla_ordinario="120 horas habiles",
        tarifa_hora_adicional=Decimal("90.00"),
    ),
    "R_LITE": RetainerTier(
        code="R_LITE",
        cuota_mensual=Decimal("300.00"),
        horas_mensuales=2,
        horas_anuales=25,
        sla_urgente="72 horas habiles",
        sla_ordinario="72 horas habiles",
        tarifa_hora_adicional=Decimal("85.00"),
    ),
    "R_STD": RetainerTier(
        code="R_STD",
        cuota_mensual=Decimal("700.00"),
        horas_mensuales=3,
        horas_anuales=40,
        sla_urgente="48 horas habiles",
        sla_ordinario="48 horas habiles",
        tarifa_hora_adicional=Decimal("80.00"),
    ),
    "R_PLUS": RetainerTier(
        code="R_PLUS",
        cuota_mensual=Decimal("1200.00"),
        horas_mensuales=6,
        horas_anuales=80,
        sla_urgente="24 horas habiles",
        sla_ordinario="24 horas habiles",
        tarifa_hora_adicional=Decimal("75.00"),
    ),
    "R_CRITICAL": RetainerTier(
        code="R_CRITICAL",
        cuota_mensual=Decimal("3000.00"),
        horas_mensuales=12,
        horas_anuales=150,
        sla_urgente="8 horas habiles (24/7)",
        sla_ordinario="8 horas habiles",
        tarifa_hora_adicional=Decimal("70.00"),
    ),
}

# Extra +300 EUR/mes si cliente es sector regulado y tier >= R_PLUS
RETAINER_SECTOR_REGULADO_EXTRA: Decimal = Decimal("300.00")


# ══════════════════════════════════════════════════════════════════════
# Plazos pago
# ══════════════════════════════════════════════════════════════════════


PAYMENT_DAYS_PRIVATE = 30
PAYMENT_DAYS_AAPP = 60  # Art. 198.4 LCSP (+ DA 32 hasta 60d)
