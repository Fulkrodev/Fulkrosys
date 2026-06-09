"""Repositorio de la fuente única editable de precios (FIX P4-1).

La tabla ``pricing_config`` es la fuente de verdad editable. Este módulo la
carga en ``rules.apply_pricing_overrides`` (mutación in-place de BASE_PRICES) al
arranque y tras cada edición admin, de modo que TODOS los consumidores
(calculator, agents 19/20, propuesta, factura) reflejan el valor vigente sin
cambiar sus call-sites.

Nota multi-worker: cada worker uvicorn mantiene su propia copia en memoria. Una
edición refresca el worker que la atiende; los demás se sincronizan en su
próximo arranque. El valor queda PERSISTIDO en BD de inmediato (fuente de
verdad). Para propagación inmediata cross-worker, reiniciar el backend tras
editar precios (aceptable para el piloto · edición infrecuente).
"""
from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


logger = logging.getLogger(__name__)

_VALID = ("BASICA", "MEDIA", "ALTA")


async def refresh_pricing_from_db(db: AsyncSession) -> dict[str, Decimal]:
    """Carga pricing_config → apply_pricing_overrides. Best-effort.

    Si la tabla no existe todavía (entorno sin migrar), no falla: los
    consumidores siguen con el default de código.
    """
    try:
        rows = (await db.execute(
            text("SELECT categoria, precio_proyecto FROM pricing_config")
        )).all()
    except Exception as exc:  # pragma: no cover — tabla ausente / arranque
        logger.warning("refresh_pricing_from_db: %s", exc)
        return {}
    prices = {r[0]: Decimal(str(r[1])) for r in rows}
    if prices:
        from backend.app.core.pricing.rules import apply_pricing_overrides
        apply_pricing_overrides(prices)
    return prices


async def get_pricing_config(db: AsyncSession) -> list[dict]:
    """Devuelve la config de precios para el endpoint admin GET."""
    rows = (await db.execute(text(
        "SELECT categoria, precio_proyecto, updated_at, updated_by "
        "FROM pricing_config ORDER BY "
        "CASE categoria WHEN 'BASICA' THEN 1 WHEN 'MEDIA' THEN 2 ELSE 3 END"
    ))).all()
    return [
        {
            "categoria": r[0],
            "precio_proyecto": float(r[1]),
            "updated_at": r[2].isoformat() if r[2] else None,
            "updated_by": r[3],
        }
        for r in rows
    ]


async def set_pricing_config(
    db: AsyncSession, prices: dict[str, float], updated_by: str,
) -> dict[str, Decimal]:
    """Actualiza pricing_config + refresca el override en memoria (PUT admin)."""
    applied: dict[str, Decimal] = {}
    for cat, val in prices.items():
        c = (cat or "").upper()
        if c not in _VALID or val is None:
            continue
        dv = Decimal(str(val))
        if dv <= 0:
            continue
        await db.execute(
            text(
                "UPDATE pricing_config SET precio_proyecto = :v, "
                "updated_at = now(), updated_by = :by WHERE categoria = :c"
            ),
            {"v": dv, "by": updated_by, "c": c},
        )
        applied[c] = dv
    from backend.app.core.pricing.rules import apply_pricing_overrides
    apply_pricing_overrides(applied)
    return applied
