"""Service · legal_obligations_catalog read-only queries.

4 query patterns:
- by regulation (RGPD/LOPDGDD/NIS2/DORA/AI_Act)
- by ENS Anexo II measure (cross-mapping reverse lookup)
- by sector
- by ENS category (B/M/A)

Sub-atom 1.C.0.C.expand v3.9.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m_legal.orm import LegalObligationCatalog


VALID_REGULATIONS = frozenset({"RGPD", "LOPDGDD", "NIS2", "DORA", "AI_Act"})
VALID_CATEGORIES = frozenset({"B", "M", "A"})


async def get_by_codigo(
    db: AsyncSession, codigo: str
) -> Optional[LegalObligationCatalog]:
    """Lookup single obligation by canonical codigo (e.g., RGPD-ART-32)."""
    stmt = select(LegalObligationCatalog).where(
        LegalObligationCatalog.codigo == codigo
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_by_regulation(
    db: AsyncSession, regulacion: str
) -> list[LegalObligationCatalog]:
    """List all obligations for a specific regulation (RGPD/LOPDGDD/NIS2/DORA/AI_Act)."""
    if regulacion not in VALID_REGULATIONS:
        return []
    stmt = (
        select(LegalObligationCatalog)
        .where(LegalObligationCatalog.regulacion == regulacion)
        .order_by(LegalObligationCatalog.codigo)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_by_ens_measure(
    db: AsyncSession, ens_measure_id: str
) -> list[LegalObligationCatalog]:
    """Reverse lookup: all obligations that cross-map to a given ENS Anexo II measure.

    Uses JSONB containment query (vinculo_medida_ens @> '[ens_measure_id]').
    """
    stmt = (
        select(LegalObligationCatalog)
        .where(
            text(
                "vinculo_medida_ens @> CAST(:ens_id_json AS jsonb)"
            ).bindparams(ens_id_json=f'["{ens_measure_id}"]')
        )
        .order_by(LegalObligationCatalog.codigo)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_by_sector(
    db: AsyncSession, sector: str
) -> list[LegalObligationCatalog]:
    """List obligations applicable to a sector (e.g., fintech, salud, todos).

    Uses JSONB containment on sector_aplica column.
    """
    stmt = (
        select(LegalObligationCatalog)
        .where(
            text(
                "sector_aplica @> CAST(:sector_json AS jsonb)"
            ).bindparams(sector_json=f'["{sector}"]')
        )
        .order_by(LegalObligationCatalog.codigo)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_by_ens_category(
    db: AsyncSession, category: str
) -> list[LegalObligationCatalog]:
    """List obligations applicable to a given ENS category (B/M/A)."""
    if category not in VALID_CATEGORIES:
        return []
    stmt = (
        select(LegalObligationCatalog)
        .where(
            text(
                "ens_categoria_aplica @> CAST(:cat_json AS jsonb)"
            ).bindparams(cat_json=f'["{category}"]')
        )
        .order_by(LegalObligationCatalog.codigo)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def count_all(db: AsyncSession) -> int:
    """Total count entries · used for smoke verification."""
    stmt = select(LegalObligationCatalog)
    result = await db.execute(stmt)
    return len(list(result.scalars().all()))
