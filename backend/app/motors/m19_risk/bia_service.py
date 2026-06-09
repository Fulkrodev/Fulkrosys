"""BIA (Business Impact Analysis) service · SAN-C MB-11.5.

Calcula y persiste BIA estructurado per servicio crítico:
RTO (Recovery Time Objective) + RPO (Recovery Point Objective) +
impact financial diario + stakeholders + recursos mínimos para reanudar.

Decisión técnica: BIA estructura el análisis pero el cliente provee
inputs via UI — no inferimos automáticamente desde motors (LLM-vs-
determinismo principle · trazabilidad ENAC primary).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.bia import BiaAnalysis


async def create_bia_entry(
    session: AsyncSession,
    project_id: uuid.UUID,
    service_name: str,
    rto_hours: int,
    rpo_hours: int,
    daily_impact_eur: Optional[Decimal] = None,
    stakeholders: Optional[list[str]] = None,
    minimum_resources: Optional[dict] = None,
) -> BiaAnalysis:
    """Crea entrada BIA per servicio crítico (no upsert · permite versioning)."""
    entry = BiaAnalysis(
        project_id=project_id,
        service_name=service_name,
        rto_hours=rto_hours,
        rpo_hours=rpo_hours,
        daily_impact_eur=daily_impact_eur,
        stakeholders=stakeholders or [],
        minimum_resources=minimum_resources or {},
        last_reviewed_at=datetime.now(timezone.utc),
    )
    session.add(entry)
    await session.flush()
    return entry


async def list_bia_entries(
    session: AsyncSession,
    project_id: uuid.UUID,
) -> list[BiaAnalysis]:
    """Lista BIA entries del proyecto ordenadas por servicio."""
    result = await session.execute(
        select(BiaAnalysis)
        .where(BiaAnalysis.project_id == project_id)
        .order_by(BiaAnalysis.service_name)
    )
    return list(result.scalars().all())


async def aggregate_bia_summary(
    session: AsyncSession,
    project_id: uuid.UUID,
) -> dict:
    """Agregado BIA proyecto: max RTO/RPO + total daily impact + count servicios."""
    entries = await list_bia_entries(session, project_id)
    if not entries:
        return {
            "services_count": 0,
            "max_rto_hours": None,
            "max_rpo_hours": None,
            "total_daily_impact_eur": None,
        }
    return {
        "services_count": len(entries),
        "max_rto_hours": max(e.rto_hours for e in entries),
        "max_rpo_hours": max(e.rpo_hours for e in entries),
        "total_daily_impact_eur": sum(
            (e.daily_impact_eur or Decimal("0") for e in entries),
            Decimal("0"),
        ),
    }
