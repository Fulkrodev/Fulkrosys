"""API admin de la capa cuantitativa MAGERIT (económica · Libro III sec 2.3).

feat/fulkro-100 Ola D. Marcos (require_owner) carga la valoración económica de los
activos y obtiene el informe de riesgo cuantitativo (ALE en €). ADR-013.
"""
from __future__ import annotations

import logging
import uuid
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db
from backend.app.models.auth import User
from backend.app.motors.m02_magerit.models import MageritAnalysis
from backend.app.motors.m02_magerit.quantitative_service import (
    QuantitativeError,
    compute_quantitative_risk,
    set_economic_value,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/magerit",
    tags=["Motor 2 - MAGERIT · Cuantitativo (Libro III 2.3)"],
    dependencies=[Depends(require_owner)],
)


# ════════════════════════════════════════════════════════════════════
# Schemas
# ════════════════════════════════════════════════════════════════════


class EconomicValueIn(BaseModel):
    asset_id: uuid.UUID
    asset_value_eur: Decimal = Field(..., ge=0)
    exposure_factor: Decimal = Field(Decimal("1.0"), ge=0, le=1)


class EconomicValuesRequest(BaseModel):
    values: list[EconomicValueIn] = Field(..., min_length=1)


class QuantitativeAssetOut(BaseModel):
    asset_id: str
    asset_value_eur: float
    total_ale: float


class QuantitativeReportOut(BaseModel):
    has_quantitative_data: bool
    total_ale_annual: float
    by_asset: list[QuantitativeAssetOut]
    by_dimension: dict[str, float]


# ════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════


async def _ensure_analysis_rls(
    db: AsyncSession, analysis_id: uuid.UUID,
) -> MageritAnalysis:
    analysis = await db.get(MageritAnalysis, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Análisis no encontrado")
    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": str(analysis.project_id)},
    )
    return analysis


# ════════════════════════════════════════════════════════════════════
# Endpoints
# ════════════════════════════════════════════════════════════════════


@router.post(
    "/analysis/{analysis_id}/economic-values",
    response_model=QuantitativeReportOut,
)
async def set_economic_values(
    analysis_id: uuid.UUID,
    body: EconomicValuesRequest,
    owner: User = Depends(require_owner),
    db: AsyncSession = Depends(get_db),
) -> QuantitativeReportOut:
    """Carga la valoración económica de N activos y devuelve el informe ALE."""
    await _ensure_analysis_rls(db, analysis_id)
    try:
        for v in body.values:
            await set_economic_value(
                db,
                analysis_id=analysis_id,
                asset_id=v.asset_id,
                asset_value_eur=v.asset_value_eur,
                exposure_factor=v.exposure_factor,
            )
    except QuantitativeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await db.commit()
    report = await compute_quantitative_risk(db, analysis_id)
    return QuantitativeReportOut(**report)


@router.get(
    "/analysis/{analysis_id}/quantitative-report",
    response_model=QuantitativeReportOut,
)
async def quantitative_report(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> QuantitativeReportOut:
    """Informe de riesgo cuantitativo (ALE €) del análisis."""
    await _ensure_analysis_rls(db, analysis_id)
    report = await compute_quantitative_risk(db, analysis_id)
    return QuantitativeReportOut(**report)
