"""M23 <-> M15 integration: facturacion recurrente de retainers.

generate_retainer_invoice:
    - Calcula monto (base_price del tier + extras opcionales)
    - Invoca BillingService.generate_invoice con concepto estandar
    - Crea RetainerBillingEvent vinculando la invoice
    - Mantiene hash chain SHA-256 + QR Verifactu heredado de M15

run_retainer_billing_cycle:
    - Para todos los retainers active con billing_cycle aplicable
    - Calcula period (mensual por defecto) y genera factura si no existe
    - Idempotente: skip si ya hay event para ese period
"""
from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.retainer import (
    PricingCatalog, RetainerBillingEvent, RetainerContract,
)
from backend.app.motors.m15_billing.billing_service import (
    BillingError, BillingService, IVA_DEFAULT, IRPF_DEFAULT,
)

logger = logging.getLogger(__name__)


def _month_bounds(reference: date) -> tuple[date, date]:
    """Primer y ultimo dia del mes que contiene `reference`."""
    from calendar import monthrange
    first = reference.replace(day=1)
    last_day = monthrange(reference.year, reference.month)[1]
    last = reference.replace(day=last_day)
    return first, last


async def _get_tier_price(db: AsyncSession, tier_code: str) -> Decimal:
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    r = await db.execute(
        select(PricingCatalog).where(
            PricingCatalog.category == "retainer",
            PricingCatalog.tier_code == tier_code,
            PricingCatalog.is_active.is_(True),
            PricingCatalog.deleted_at.is_(None),
        ).order_by(PricingCatalog.effective_from.desc()).limit(1)
    )
    entry = r.scalar_one_or_none()
    if entry is None:
        raise BillingError(
            f"pricing_catalog sin entrada retainer {tier_code}. "
            f"Ejecuta seed_pricing_catalog primero."
        )
    return Decimal(str(entry.base_price))


async def generate_retainer_invoice(
    db: AsyncSession,
    retainer_contract_id: uuid.UUID,
    period_start: date | None = None,
    period_end: date | None = None,
    *,
    extras_applied: dict[str, Decimal] | None = None,
    apply_irpf: bool = True,
) -> RetainerBillingEvent:
    """Genera factura recurrente para el retainer en el periodo dado.

    Idempotente: si ya existe RetainerBillingEvent para ese periodo,
    devuelve el existente sin duplicar factura.
    """
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    rc = await db.get(RetainerContract, retainer_contract_id)
    if rc is None:
        raise BillingError(f"RetainerContract {retainer_contract_id} no existe")
    if rc.estado != "active":
        raise BillingError(
            f"Retainer {retainer_contract_id} no esta active ({rc.estado})"
        )

    ref = period_start or date.today()
    start, end = _month_bounds(ref)
    if period_end:
        end = period_end

    # Idempotencia: buscar event existente
    r = await db.execute(
        select(RetainerBillingEvent).where(
            RetainerBillingEvent.retainer_contract_id == rc.id,
            RetainerBillingEvent.billing_period_start == start,
            RetainerBillingEvent.billing_period_end == end,
            RetainerBillingEvent.deleted_at.is_(None),
        )
    )
    existing = r.scalar_one_or_none()
    if existing:
        logger.info(
            "generate_retainer_invoice idempotent skip: event %s",
            existing.id,
        )
        return existing

    base = await _get_tier_price(db, rc.perfil or "R_STD")
    extras_total = Decimal("0")
    lineas = [{
        "descripcion": (
            f"Servicio de mantenimiento ENS - {rc.perfil or 'R_STD'} - "
            f"{start.isoformat()} a {end.isoformat()}"
        ),
        "cantidad": 1,
        # §4.4 · Decimal directo (create_invoice lo re-cuantiza) · sin round-trip float.
        "precio_unitario": base,
    }]
    for key, value in (extras_applied or {}).items():
        amount = Decimal(str(value))
        extras_total += amount
        lineas.append({
            "descripcion": f"Extra retainer: {key}",
            "cantidad": 1,
            "precio_unitario": amount,
        })

    svc = BillingService()
    invoice = await svc.generate_invoice(
        db=db,
        client_id=rc.client_id,
        project_id=rc.project_id,
        contract_id=rc.contract_id,
        concepto=(
            f"Retainer ENS ({rc.perfil or 'R_STD'}) - "
            f"{start.strftime('%B %Y')}"
        ),
        lineas=lineas,
        tipo="ordinaria",
        aplicar_irpf=apply_irpf,
        iva_percent=IVA_DEFAULT,
        irpf_percent=IRPF_DEFAULT,
        fecha_emision=end,
    )

    event = RetainerBillingEvent(
        retainer_contract_id=rc.id,
        invoice_id=invoice.id,
        billing_period_start=start,
        billing_period_end=end,
        amount=invoice.total,
        status="emitted",
        notes=(
            f"Generada automaticamente. Base {float(base)} EUR "
            f"+ extras {float(extras_total)} EUR + IVA {IVA_DEFAULT}% "
            f"- IRPF {IRPF_DEFAULT if apply_irpf else 0}%."
        ),
    )
    db.add(event)
    await db.flush()
    return event


async def run_retainer_billing_cycle(
    db: AsyncSession, reference_date: date | None = None,
) -> dict[str, Any]:
    """Ejecuta ciclo de facturacion para todos los retainers active.

    Llamado desde Celery beat el 1 de cada mes a las 06:00.
    """
    ref = reference_date or date.today()
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    r = await db.execute(
        select(RetainerContract).where(
            RetainerContract.estado == "active",
            RetainerContract.deleted_at.is_(None),
        )
    )
    retainers = list(r.scalars().all())
    generated: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []

    for rc in retainers:
        try:
            event = await generate_retainer_invoice(
                db, rc.id, period_start=ref,
            )
            if event.created_at and (
                datetime.now(timezone.utc) - event.created_at
            ).total_seconds() < 60:
                generated.append({
                    "retainer_id": str(rc.id),
                    "invoice_id": str(event.invoice_id),
                    "amount": float(event.amount),
                })
            else:
                skipped.append({
                    "retainer_id": str(rc.id),
                    "reason": "already_generated_this_period",
                })
        except Exception as exc:  # pragma: no cover
            logger.exception("billing_cycle failed for %s", rc.id)
            failed.append({"retainer_id": str(rc.id), "error": str(exc)})

    return {
        "reference_date": ref.isoformat(),
        "retainers_total": len(retainers),
        "generated": generated,
        "skipped": skipped,
        "failed": failed,
    }


__all__ = [
    "generate_retainer_invoice",
    "run_retainer_billing_cycle",
    "_month_bounds",
]
