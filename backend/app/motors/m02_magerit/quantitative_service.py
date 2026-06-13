"""Capa cuantitativa MAGERIT (económica · Libro III sec 2.3).

feat/fulkro-100 Ola D. Deriva el ALE (Annual Loss Expectancy) en € a partir de la
valoración económica del activo + las valoraciones de amenaza CUALITATIVAS ya
existentes (degradación + probabilidad). Determinista (R1 · sin LLM). Coexiste con
el modelo cualitativo (backward-compat · sin valor económico = solo cualitativo).

    SLE_dim = asset_value_eur × exposure_factor × (degradation_dim / 100)
    ARO     = FREQUENCY_MAP[probability]        (MB=0.01 … MA=365)
    ALE_dim = SLE_dim × ARO
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m02_magerit.models import (
    MageritEconomicValue,
    MageritThreatAssessment,
)
from backend.app.motors.m02_magerit.service import FREQUENCY_MAP

_DIMS = ("d", "i", "c", "a", "t")


class QuantitativeError(ValueError):
    """Error de validación de la valoración económica."""


async def set_economic_value(
    db: AsyncSession,
    *,
    analysis_id: uuid.UUID,
    asset_id: uuid.UUID,
    asset_value_eur: Decimal,
    exposure_factor: Decimal = Decimal("1.0"),
) -> MageritEconomicValue:
    """Upsert de la valoración económica de un activo (1 fila por activo)."""
    if asset_value_eur < 0:
        raise QuantitativeError("asset_value_eur no puede ser negativo")
    if not (Decimal("0") <= exposure_factor <= Decimal("1")):
        raise QuantitativeError("exposure_factor debe estar entre 0 y 1")

    existing = (await db.execute(
        select(MageritEconomicValue).where(
            MageritEconomicValue.analysis_id == analysis_id,
            MageritEconomicValue.asset_id == asset_id,
        )
    )).scalar_one_or_none()

    if existing is None:
        row = MageritEconomicValue(
            analysis_id=analysis_id,
            asset_id=asset_id,
            asset_value_eur=asset_value_eur,
            exposure_factor=exposure_factor,
        )
        db.add(row)
        await db.flush()
        return row

    existing.asset_value_eur = asset_value_eur
    existing.exposure_factor = exposure_factor
    await db.flush()
    return existing


async def compute_quantitative_risk(
    db: AsyncSession, analysis_id: uuid.UUID,
) -> dict[str, Any]:
    """Calcula el ALE económico del análisis (on-query · determinista).

    Devuelve total anual + desglose por activo + por dimensión. Si no hay valores
    económicos, devuelve estructura vacía (total 0) sin romper (backward-compat).
    """
    eco_rows = (await db.execute(
        select(MageritEconomicValue).where(
            MageritEconomicValue.analysis_id == analysis_id,
        )
    )).scalars().all()
    eco_by_asset: dict[uuid.UUID, tuple[float, float]] = {
        r.asset_id: (float(r.asset_value_eur), float(r.exposure_factor))
        for r in eco_rows
    }

    if not eco_by_asset:
        return {
            "has_quantitative_data": False,
            "total_ale_annual": 0.0,
            "by_asset": [],
            "by_dimension": {d.upper(): 0.0 for d in _DIMS},
        }

    threats = (await db.execute(
        select(MageritThreatAssessment).where(
            MageritThreatAssessment.analysis_id == analysis_id,
        )
    )).scalars().all()

    per_asset: dict[uuid.UUID, float] = {a: 0.0 for a in eco_by_asset}
    per_dim: dict[str, float] = {d.upper(): 0.0 for d in _DIMS}

    for t in threats:
        eco = eco_by_asset.get(t.asset_id)
        if eco is None:
            continue  # amenaza sobre activo sin valoración económica
        value_eur, exposure = eco
        aro = FREQUENCY_MAP.get(t.probability, 0.0)
        if aro == 0.0:
            continue
        for dim in _DIMS:
            degradation = getattr(t, f"degradation_{dim}", None)
            if not degradation:
                continue
            sle = value_eur * exposure * (degradation / 100.0)
            ale = sle * aro
            per_asset[t.asset_id] += ale
            per_dim[dim.upper()] += ale

    by_asset = [
        {
            "asset_id": str(asset_id),
            "asset_value_eur": round(eco_by_asset[asset_id][0], 2),
            "total_ale": round(ale, 2),
        }
        for asset_id, ale in sorted(
            per_asset.items(), key=lambda kv: kv[1], reverse=True,
        )
    ]
    total = round(sum(per_asset.values()), 2)

    return {
        "has_quantitative_data": True,
        "total_ale_annual": total,
        "by_asset": by_asset,
        "by_dimension": {k: round(v, 2) for k, v in per_dim.items()},
    }
