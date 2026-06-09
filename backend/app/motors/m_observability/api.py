"""LLM observability admin API · MB-7 Q3.A.

Admin-only endpoints reading from llm_interaction_log. NO cliente access.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db

from backend.app.motors.m_observability.llm_observability_service import (
    PERIODS,
    get_agent_cache_stats,
    get_anomaly_alerts,
    get_cost_summary,
    get_interactions_paginated,
    get_project_token_usage,
    get_top_consumers,
)


router = APIRouter(
    prefix="/admin/llm-observability",
    tags=["admin - LLM observability"],
    dependencies=[Depends(require_owner)],
)


@router.get("/cost-summary")
async def admin_cost_summary(
    period: str = Query("today", description="today|week|month|all"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if period not in PERIODS:
        raise HTTPException(
            status_code=400, detail=f"period must be one of {list(PERIODS)}",
        )
    return await get_cost_summary(db, period)


@router.get("/interactions")
async def admin_interactions(
    feature: Optional[str] = None,
    model: Optional[str] = None,
    status_filter: Optional[str] = None,
    project_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await get_interactions_paginated(
        db,
        feature=feature,
        model=model,
        status_filter=status_filter,
        project_id=project_id,
        limit=limit,
        offset=offset,
    )


@router.get("/top-consumers")
async def admin_top_consumers(
    limit: int = Query(10, ge=1, le=50),
    period: str = Query("month"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if period not in PERIODS:
        raise HTTPException(
            status_code=400, detail=f"period must be one of {list(PERIODS)}",
        )
    items = await get_top_consumers(db, limit=limit, period=period)
    return {"period": period, "items": items}


@router.get("/projects/{project_id}/token-usage")
async def admin_project_token_usage(
    project_id: str,
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Aggregate token usage per agent for a project over last N days.

    Reads from canonical ``llm_interaction_log`` (ADR-025 sostenido firmísimo
    · NO duplicate table). Includes cached_input_tokens + cache_hit_rate.
    """
    return await get_project_token_usage(db, project_id=project_id, days=days)


@router.get("/agents/{agent_name}/cache-stats")
async def admin_agent_cache_stats(
    agent_name: str,
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Cache hit-rate stats for a single agent (feature) over last N days."""
    return await get_agent_cache_stats(db, agent_name=agent_name, days=days)


@router.get("/anomalies")
async def admin_anomalies(
    threshold_usd: float = Query(10.0, ge=0.0),
    threshold_latency_ms: int = Query(60_000, ge=0),
    period: str = Query("today"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if period not in PERIODS:
        raise HTTPException(
            status_code=400, detail=f"period must be one of {list(PERIODS)}",
        )
    items = await get_anomaly_alerts(
        db,
        threshold_usd=threshold_usd,
        threshold_latency_ms=threshold_latency_ms,
        period=period,
    )
    return {
        "period": period,
        "threshold_usd": threshold_usd,
        "threshold_latency_ms": threshold_latency_ms,
        "items": items,
    }
