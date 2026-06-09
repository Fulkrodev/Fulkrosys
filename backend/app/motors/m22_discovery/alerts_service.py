"""DiscoveryAlert queries (M22)."""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.discovery import DiscoveryAlert


async def list_alerts(
    session: AsyncSession,
    project_id: uuid.UUID,
    severidad: Optional[str] = None,
    modulo: Optional[str] = None,
    discovery_run_id: Optional[uuid.UUID] = None,
) -> list[DiscoveryAlert]:
    stmt = select(DiscoveryAlert).where(DiscoveryAlert.project_id == project_id)
    if severidad:
        stmt = stmt.where(DiscoveryAlert.severidad == severidad)
    if modulo:
        stmt = stmt.where(DiscoveryAlert.modulo == modulo)
    if discovery_run_id:
        stmt = stmt.where(DiscoveryAlert.discovery_run_id == discovery_run_id)
    r = await session.execute(stmt.order_by(DiscoveryAlert.created_at.desc()))
    return list(r.scalars().all())


async def alerts_summary(session: AsyncSession, project_id: uuid.UUID) -> dict:
    total = (await session.execute(
        select(func.count(DiscoveryAlert.id)).where(DiscoveryAlert.project_id == project_id)
    )).scalar_one() or 0

    by_severidad: dict[str, int] = {}
    r = await session.execute(
        select(DiscoveryAlert.severidad, func.count(DiscoveryAlert.id))
        .where(DiscoveryAlert.project_id == project_id)
        .group_by(DiscoveryAlert.severidad)
    )
    for sev, count in r.all():
        by_severidad[sev] = count

    by_modulo: dict[str, int] = {}
    r = await session.execute(
        select(DiscoveryAlert.modulo, func.count(DiscoveryAlert.id))
        .where(DiscoveryAlert.project_id == project_id)
        .group_by(DiscoveryAlert.modulo)
    )
    for mod, count in r.all():
        by_modulo[mod] = count

    return {
        "total": total,
        "by_severidad": by_severidad,
        "by_modulo": by_modulo,
    }


def alert_to_dict(alert: DiscoveryAlert) -> dict:
    return {
        "id": str(alert.id),
        "project_id": str(alert.project_id),
        "discovery_run_id": str(alert.discovery_run_id),
        "modulo": alert.modulo,
        "severidad": alert.severidad,
        "codigo": alert.codigo,
        "titulo": alert.titulo,
        "descripcion": alert.descripcion,
        "entity_type": alert.entity_type,
        "entity_id": str(alert.entity_id),
        "medidas_ens_afectadas": alert.medidas_ens_afectadas or [],
        "gap_volcado": alert.gap_volcado,
        "created_at": alert.created_at.isoformat() if alert.created_at else None,
    }
