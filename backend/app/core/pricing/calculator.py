"""FULKRO pricing calculator — Apendice M v2.2.

Funciones puras (no tocan BD) que devuelven estructuras dataclass con
desglose, totales y texto human-readable. Usado por:

- M13 Agente 19 Redactor Propuestas para rellenar P-001.
- M14 ContractService para generar C-001 con hitos oficiales.
- M15 BillingService para facturar hitos, bolsa, quick scan, audit.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from backend.app.core.legal import is_aapp
from backend.app.core.pricing.rules import (
    AUDIT_INTERNA_DURATIONS,
    AUDIT_INTERNA_PRICES,
    BASE_PRICES,
    BOLSA_FLEX_BASE_PRICE,
    BOLSA_FLEX_MIN_HOURS,
    BOLSA_FLEX_TIERS,
    EXTRAS_DESCRIPTIONS,
    EXTRAS_IMPLANTACION_MEDIA,
    GARANTIAS_COMERCIALES,
    HITOS_BY_CATEGORIA,
    HOURS_RANGE,
    MADUREZ_L0_L1_THRESHOLD_PCT,
    PAYMENT_DAYS_AAPP,
    PAYMENT_DAYS_PRIVATE,
    QUICK_SCAN_DISCOUNT_WINDOW_DAYS,
    QUICK_SCAN_PRICE,
    RETAINER_SECTOR_REGULADO_EXTRA,
    RETAINER_TIERS,
    SECTORES_REGULADOS,
    URGENCY_SURCHARGE_PCT,
    URGENCY_THRESHOLD_DAYS,
)


class PricingError(ValueError):
    """Error de calculo de pricing (categoria invalida, tier invalido, etc.)."""


# ══════════════════════════════════════════════════════════════════════
# Dataclasses de salida
# ══════════════════════════════════════════════════════════════════════


@dataclass
class ExtraItem:
    code: str
    description: str
    amount: Decimal


@dataclass
class MilestoneBreakdown:
    code: str
    pct: Decimal          # 0..1
    pct_display: Decimal  # 0..100
    description: str
    amount: Decimal


@dataclass
class ImplantacionPricing:
    categoria: str
    base: Decimal
    extras: list[ExtraItem] = field(default_factory=list)
    urgency_surcharge: Decimal = Decimal("0.00")
    total: Decimal = Decimal("0.00")
    hitos: list[MilestoneBreakdown] = field(default_factory=list)
    garantia: str = ""
    hours_range: tuple[int, int] = (0, 0)
    breakdown_text: str = ""
    payment_days: int = PAYMENT_DAYS_PRIVATE
    is_aapp: bool = False


@dataclass
class RetainerPricing:
    tier: str
    cuota_mensual: Decimal
    horas_mensuales: int
    horas_anuales: int
    sla_urgente: str
    sla_ordinario: str
    tarifa_hora_adicional: Decimal
    sector_regulado_extra: Decimal = Decimal("0.00")
    total_mensual: Decimal = Decimal("0.00")


@dataclass
class BolsaPricing:
    hours: int
    price_per_hour: Decimal
    discount_pct: Decimal
    base_amount: Decimal
    discount_amount: Decimal
    subtotal: Decimal
    description: str


@dataclass
class MilestonePricing:
    contract_total: Decimal
    categoria: str
    milestones: list[MilestoneBreakdown]


# ══════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════


def _q(val: Decimal | int | float | str) -> Decimal:
    """Cuantiza a 2 decimales (centimos EUR)."""
    return Decimal(str(val)).quantize(Decimal("0.01"))


def _normalize_categoria(cat: str | None) -> str:
    if not cat:
        raise PricingError("categoria vacia")
    c = cat.strip().upper()
    if c not in BASE_PRICES:
        raise PricingError(f"categoria invalida: {cat!r}. Validas: BASICA/MEDIA/ALTA")
    return c


# ══════════════════════════════════════════════════════════════════════
# Calculator
# ══════════════════════════════════════════════════════════════════════


class PricingCalculator:
    """Calculadora pricing Apendice M. Todas las funciones son puras."""

    # ── Implantacion ────────────────────────────────────────────────

    def calculate_implantacion(
        self,
        categoria: str,
        *,
        cliente: Any = None,
        sistemas_en_alcance: int = 1,
        sedes: int = 1,
        madurez_pct: int | None = None,
        sector: str | None = None,
        dias_hasta_plazo: int | None = None,
    ) -> ImplantacionPricing:
        """Calcula pricing de implantacion desde categoria + metadata cliente/proyecto.

        Los parametros individuales permiten que el caller tenga control total
        sin depender del ORM. ``cliente`` es opcional; si se pasa, extrae
        sector / is_aapp automaticamente.
        """
        cat = _normalize_categoria(categoria)
        base = BASE_PRICES[cat]
        extras: list[ExtraItem] = []

        # Resolucion de sector y is_aapp desde el objeto cliente si se pasa
        cliente_sector = sector
        aapp = False
        if cliente is not None:
            if isinstance(cliente, dict):
                cliente_sector = cliente_sector or cliente.get("sector")
            else:
                cliente_sector = cliente_sector or getattr(cliente, "sector", None)
            aapp = is_aapp(cliente)

        cliente_sector_norm = (cliente_sector or "").lower().strip()

        # Extras solo aplican a MEDIA (spec Apendice M)
        if cat == "MEDIA":
            if cliente_sector_norm in SECTORES_REGULADOS:
                extras.append(ExtraItem(
                    "sector_regulado",
                    EXTRAS_DESCRIPTIONS["sector_regulado"],
                    EXTRAS_IMPLANTACION_MEDIA["sector_regulado"],
                ))
            if sedes > 1:
                extras.append(ExtraItem(
                    "multi_ubicacion",
                    EXTRAS_DESCRIPTIONS["multi_ubicacion"],
                    EXTRAS_IMPLANTACION_MEDIA["multi_ubicacion"],
                ))
            if (
                madurez_pct is not None
                and madurez_pct < MADUREZ_L0_L1_THRESHOLD_PCT
            ):
                extras.append(ExtraItem(
                    "madurez_l0_l1",
                    EXTRAS_DESCRIPTIONS["madurez_l0_l1"],
                    EXTRAS_IMPLANTACION_MEDIA["madurez_l0_l1"],
                ))
            if sistemas_en_alcance > 1:
                extra_sistemas = sistemas_en_alcance - 1
                extras.append(ExtraItem(
                    "sistemas_adicionales",
                    f"{extra_sistemas} sistema(s) adicional(es) en alcance",
                    EXTRAS_IMPLANTACION_MEDIA["sistemas_adicionales"] * extra_sistemas,
                ))

        subtotal_without_urgency = base + sum(
            (e.amount for e in extras), start=Decimal("0")
        )

        # Urgencia si plazo <6 semanas
        urgency_surcharge = Decimal("0.00")
        if dias_hasta_plazo is not None and dias_hasta_plazo < URGENCY_THRESHOLD_DAYS:
            urgency_surcharge = _q(subtotal_without_urgency * URGENCY_SURCHARGE_PCT)

        total = _q(subtotal_without_urgency + urgency_surcharge)

        # Hitos oficiales por categoria
        hitos = self._compute_milestones(cat, total)

        # Texto legible
        breakdown_lines = [f"{cat} base: {base:.2f} EUR"]
        for e in extras:
            breakdown_lines.append(f"+ {e.description}: {e.amount:.2f} EUR")
        if urgency_surcharge > 0:
            breakdown_lines.append(
                f"+ Recargo urgencia (plazo <{URGENCY_THRESHOLD_DAYS}d): "
                f"{urgency_surcharge:.2f} EUR (+{int(URGENCY_SURCHARGE_PCT * 100)}%)"
            )
        breakdown_lines.append(f"= TOTAL: {total:.2f} EUR")

        return ImplantacionPricing(
            categoria=cat,
            base=_q(base),
            extras=extras,
            urgency_surcharge=urgency_surcharge,
            total=total,
            hitos=hitos,
            garantia=GARANTIAS_COMERCIALES[cat],
            hours_range=HOURS_RANGE[cat],
            breakdown_text="\n".join(breakdown_lines),
            payment_days=PAYMENT_DAYS_AAPP if aapp else PAYMENT_DAYS_PRIVATE,
            is_aapp=aapp,
        )

    def _compute_milestones(
        self, categoria: str, total: Decimal,
    ) -> list[MilestoneBreakdown]:
        specs = HITOS_BY_CATEGORIA[categoria]
        results: list[MilestoneBreakdown] = []
        accumulated = Decimal("0.00")
        for idx, spec in enumerate(specs):
            if idx == len(specs) - 1:
                # Ultimo hito absorbe residuos de redondeo para suma exacta
                amount = _q(total - accumulated)
            else:
                amount = _q(total * spec.pct)
                accumulated += amount
            results.append(MilestoneBreakdown(
                code=spec.code,
                pct=spec.pct,
                pct_display=_q(spec.pct * 100),
                description=spec.description,
                amount=amount,
            ))
        return results

    def calculate_milestone_amount(
        self, categoria: str, contract_total: Decimal, milestone_code: str,
    ) -> MilestoneBreakdown:
        cat = _normalize_categoria(categoria)
        hitos = self._compute_milestones(cat, _q(contract_total))
        for h in hitos:
            if h.code == milestone_code:
                return h
        valid = ", ".join(h.code for h in hitos)
        raise PricingError(
            f"milestone_code invalido: {milestone_code!r}. Validos: {valid}"
        )

    def get_milestones(
        self, categoria: str, contract_total: Decimal,
    ) -> MilestonePricing:
        cat = _normalize_categoria(categoria)
        return MilestonePricing(
            contract_total=_q(contract_total),
            categoria=cat,
            milestones=self._compute_milestones(cat, _q(contract_total)),
        )

    # ── Retainer ────────────────────────────────────────────────────

    def calculate_retainer(
        self, tier: str, *, sector_regulado: bool = False,
    ) -> RetainerPricing:
        tier_up = (tier or "").upper()
        if tier_up not in RETAINER_TIERS:
            raise PricingError(
                f"tier invalido: {tier!r}. Validos: {list(RETAINER_TIERS)}"
            )
        t = RETAINER_TIERS[tier_up]
        sector_extra = Decimal("0.00")
        # Extra sector regulado solo para R_PLUS / R_CRITICAL
        if sector_regulado and tier_up in ("R_PLUS", "R_CRITICAL"):
            sector_extra = RETAINER_SECTOR_REGULADO_EXTRA
        total_mensual = _q(t.cuota_mensual + sector_extra)
        return RetainerPricing(
            tier=t.code,
            cuota_mensual=_q(t.cuota_mensual),
            horas_mensuales=t.horas_mensuales,
            horas_anuales=t.horas_anuales,
            sla_urgente=t.sla_urgente,
            sla_ordinario=t.sla_ordinario,
            tarifa_hora_adicional=_q(t.tarifa_hora_adicional),
            sector_regulado_extra=sector_extra,
            total_mensual=total_mensual,
        )

    # ── Bolsa flex ──────────────────────────────────────────────────

    def calculate_bolsa_flex(self, hours: int) -> BolsaPricing:
        if hours < BOLSA_FLEX_MIN_HOURS:
            raise PricingError(
                f"Bolsa flex minima de {BOLSA_FLEX_MIN_HOURS}h. Recibido: {hours}"
            )
        for tier in BOLSA_FLEX_TIERS:
            if hours <= tier.max_hours:
                break
        else:  # pragma: no cover
            tier = BOLSA_FLEX_TIERS[-1]

        base_amount = _q(BOLSA_FLEX_BASE_PRICE * hours)
        subtotal = _q(tier.price_per_hour * hours)
        discount_amount = _q(base_amount - subtotal)
        return BolsaPricing(
            hours=hours,
            price_per_hour=_q(tier.price_per_hour),
            discount_pct=tier.discount_pct,
            base_amount=base_amount,
            discount_amount=discount_amount,
            subtotal=subtotal,
            description=(
                f"Bolsa flex {hours}h consultoria ENS "
                f"({int(tier.discount_pct * 100)}% descuento volumen)"
                if tier.discount_pct > 0
                else f"Bolsa flex {hours}h consultoria ENS"
            ),
        )

    # ── Quick scan ──────────────────────────────────────────────────

    def calculate_quick_scan(
        self, *, discount_if_implantation: bool = False,
    ) -> dict[str, Any]:
        return {
            "price": _q(QUICK_SCAN_PRICE),
            "discount_if_implantation": discount_if_implantation,
            "discount_window_days": QUICK_SCAN_DISCOUNT_WINDOW_DAYS,
            "description": (
                f"Quick scan pre-auditoria ENS (1 semana)"
                + (
                    f". Descontable 100% si contrata implantacion "
                    f"en los proximos {QUICK_SCAN_DISCOUNT_WINDOW_DAYS} dias"
                    if discount_if_implantation else ""
                )
            ),
        }

    # ── Auditoria interna ──────────────────────────────────────────

    def calculate_audit_interna(self, categoria: str) -> dict[str, Any]:
        cat = _normalize_categoria(categoria)
        price = AUDIT_INTERNA_PRICES.get(cat)
        if price is None:
            raise PricingError(f"No hay precio de auditoria para categoria {cat}")
        return {
            "categoria": cat,
            "price": _q(price),
            "duration": AUDIT_INTERNA_DURATIONS[cat],
            "description": (
                f"Auditoria interna independiente {cat} "
                f"({AUDIT_INTERNA_DURATIONS[cat]}) — conforme CCN-STIC 808"
            ),
        }

    # ── Urgencia ────────────────────────────────────────────────────

    def detect_urgency(
        self, *, firma_date: date, plazo_date: date,
    ) -> tuple[bool, int]:
        days = (plazo_date - firma_date).days
        return days < URGENCY_THRESHOLD_DAYS, days

    def apply_urgency_surcharge(
        self, base_amount: Decimal, *, is_urgent: bool,
    ) -> Decimal:
        if not is_urgent:
            return _q(base_amount)
        return _q(Decimal(str(base_amount)) * (Decimal("1") + URGENCY_SURCHARGE_PCT))
