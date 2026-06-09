"""M13 Commercial — Discount service (Paso 7 final 7.8).

Gestiona el ciclo de vida de descuentos comerciales:

- Auto-creacion cuando se emite factura quick scan
  (M15.generate_quick_scan_invoice dispara este flujo).
- Auto-aplicacion cuando se firma C-001 dentro de ventana 30d.
- Expiracion diaria via Celery beat.
- CRUD manual (Marcos crea referral/campaign/loyalty).
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.commercial_paso7 import CommercialDiscount

logger = logging.getLogger(__name__)


QUICK_SCAN_DISCOUNT_WINDOW_DAYS = 30
QUICK_SCAN_AMOUNT = Decimal("1500.00")


class DiscountError(Exception):
    pass


class DiscountService:
    """Servicio transversal de descuentos comerciales."""

    async def create_quick_scan_discount(
        self,
        db: AsyncSession,
        *,
        client_id: uuid.UUID,
        source_invoice_id: uuid.UUID | None = None,
        amount: Decimal = QUICK_SCAN_AMOUNT,
        window_days: int = QUICK_SCAN_DISCOUNT_WINDOW_DAYS,
    ) -> CommercialDiscount:
        """Crea discount auto al emitir factura quick scan.

        ``source_invoice_id`` nullable para tests y casos donde Marcos
        otorga el descuento manualmente sin factura previa.
        """
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=window_days)
        reason = (
            f"Descuento 100% quick scan pre-auditoria ref factura "
            f"{source_invoice_id}"
            if source_invoice_id
            else "Descuento 100% quick scan pre-auditoria (sin factura origen)"
        )
        discount = CommercialDiscount(
            client_id=client_id,
            discount_type="quick_scan_to_implantacion",
            amount=float(amount),
            amount_pct=None,
            applicable_to="c001_implantacion",
            granted_at=now,
            granted_by="auto",
            granted_reason=reason,
            expires_at=expires_at,
            status="available",
            source_invoice_id=source_invoice_id,
            metadata_jsonb={
                "auto_created": True,
                "window_days": window_days,
            },
            created_at=now,
        )
        await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
        try:
            db.add(discount)
            await db.flush()
        finally:
            await db.execute(sa_text("RESET ROLE"))
        return discount

    async def create_manual_discount(
        self,
        db: AsyncSession,
        *,
        client_id: uuid.UUID,
        discount_type: str,
        applicable_to: str,
        amount: Decimal | None = None,
        amount_pct: Decimal | None = None,
        granted_reason: str | None = None,
        expires_at: datetime | None = None,
        granted_by: str = "marcos",
    ) -> CommercialDiscount:
        """Marcos crea manual (referral_bonus / campaign_special / loyalty_retainer)."""
        if amount is None and amount_pct is None:
            raise DiscountError("Debe especificar amount o amount_pct")
        valid_types = {
            "quick_scan_to_implantacion", "referral_bonus",
            "campaign_special", "loyalty_retainer",
        }
        if discount_type not in valid_types:
            raise DiscountError(
                f"discount_type invalido. Validos: {sorted(valid_types)}"
            )
        now = datetime.now(timezone.utc)
        discount = CommercialDiscount(
            client_id=client_id,
            discount_type=discount_type,
            amount=float(amount) if amount else None,
            amount_pct=float(amount_pct) if amount_pct else None,
            applicable_to=applicable_to,
            granted_at=now,
            granted_by=granted_by,
            granted_reason=granted_reason,
            expires_at=expires_at,
            status="available",
            created_at=now,
        )
        await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
        try:
            db.add(discount)
            await db.flush()
        finally:
            await db.execute(sa_text("RESET ROLE"))
        return discount

    async def list_available_discounts(
        self,
        db: AsyncSession,
        *,
        client_id: uuid.UUID,
        applicable_to: str | None = None,
    ) -> list[CommercialDiscount]:
        now = datetime.now(timezone.utc)
        await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
        try:
            stmt = select(CommercialDiscount).where(
                CommercialDiscount.client_id == client_id,
                CommercialDiscount.status == "available",
            ).order_by(CommercialDiscount.expires_at.asc().nulls_last())
            if applicable_to:
                stmt = stmt.where(
                    CommercialDiscount.applicable_to.in_(
                        (applicable_to, "any", "any_implantacion")
                    )
                )
            rows = (await db.execute(stmt)).scalars().all()
            # Filter expired in-memory (tolera expires_at NULL = no expira)
            return [
                d for d in rows
                if d.expires_at is None or d.expires_at > now
            ]
        finally:
            await db.execute(sa_text("RESET ROLE"))

    async def apply_discount_to_contract(
        self,
        db: AsyncSession,
        *,
        discount_id: uuid.UUID,
        contract_id: uuid.UUID,
    ) -> CommercialDiscount:
        """Marca discount como usado vinculado a un contrato."""
        await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
        try:
            res = await db.execute(
                select(CommercialDiscount).where(
                    CommercialDiscount.id == discount_id,
                )
            )
            discount = res.scalar_one_or_none()
            if discount is None:
                raise DiscountError(
                    f"Discount {discount_id} no existe"
                )
            if discount.status != "available":
                raise DiscountError(
                    f"Discount {discount_id} no esta disponible "
                    f"(status={discount.status})"
                )
            if (
                discount.expires_at
                and discount.expires_at < datetime.now(timezone.utc)
            ):
                raise DiscountError(
                    f"Discount {discount_id} expiro el "
                    f"{discount.expires_at.isoformat()}"
                )
            discount.used_at = datetime.now(timezone.utc)
            discount.used_in_contract_id = contract_id
            discount.status = "used"
            await db.flush()
        finally:
            await db.execute(sa_text("RESET ROLE"))
        return discount

    async def revoke_discount(
        self,
        db: AsyncSession,
        *,
        discount_id: uuid.UUID,
        reason: str | None = None,
    ) -> CommercialDiscount:
        await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
        try:
            res = await db.execute(
                select(CommercialDiscount).where(
                    CommercialDiscount.id == discount_id,
                )
            )
            discount = res.scalar_one_or_none()
            if discount is None:
                raise DiscountError(f"Discount {discount_id} no existe")
            if discount.status != "available":
                raise DiscountError(
                    f"Solo se revocan discounts disponibles "
                    f"(actual: {discount.status})"
                )
            discount.status = "revoked"
            meta = dict(discount.metadata_jsonb or {})
            meta["revoke_reason"] = reason or ""
            meta["revoked_at"] = datetime.now(timezone.utc).isoformat()
            discount.metadata_jsonb = meta
            await db.flush()
        finally:
            await db.execute(sa_text("RESET ROLE"))
        return discount

    async def expire_old_discounts(
        self,
        db: AsyncSession,
        *,
        today: datetime | None = None,
    ) -> dict[str, Any]:
        """Celery daily task: marca expired los con expires_at <= today."""
        today = today or datetime.now(timezone.utc)
        await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
        try:
            res = await db.execute(
                select(CommercialDiscount).where(
                    CommercialDiscount.status == "available",
                    CommercialDiscount.expires_at.is_not(None),
                    CommercialDiscount.expires_at <= today,
                )
            )
            expired = list(res.scalars().all())
            for d in expired:
                d.status = "expired"
            await db.flush()
        finally:
            await db.execute(sa_text("RESET ROLE"))
        return {
            "expired_count": len(expired),
            "expired_ids": [str(d.id) for d in expired],
        }
