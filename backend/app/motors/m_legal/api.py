"""API · legal_obligations_catalog read-only endpoints.

5 endpoints lookup catalog (250 entries · RGPD/LOPDGDD/NIS2/DORA/AI_Act):
- GET /api/v1/legal-obligations/catalog?regulacion=RGPD
- GET /api/v1/legal-obligations/catalog?ens_measure=op.exp.5
- GET /api/v1/legal-obligations/catalog?sector=fintech
- GET /api/v1/legal-obligations/catalog?ens_category=M
- GET /api/v1/legal-obligations/catalog/{codigo}

Auth: require_marcos_or_client (admin + client_user · read-only catalog).

Sub-atom 1.C.0.C.expand v3.9.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_marcos_or_client
from backend.app.database import get_db

from backend.app.motors.m_legal.schemas import (
    LegalObligationCatalogList,
    LegalObligationCatalogRead,
)
from backend.app.motors.m_legal.service import (
    VALID_CATEGORIES,
    VALID_REGULATIONS,
    get_by_codigo,
    list_by_ens_category,
    list_by_ens_measure,
    list_by_regulation,
    list_by_sector,
)


router = APIRouter(
    prefix="/legal-obligations",
    tags=["legal-obligations"],
    dependencies=[Depends(require_marcos_or_client)],
)


@router.get("/catalog", response_model=LegalObligationCatalogList)
async def list_catalog(
    regulacion: Optional[str] = Query(
        None, description="RGPD | LOPDGDD | NIS2 | DORA | AI_Act"
    ),
    ens_measure: Optional[str] = Query(
        None, description="ENS Anexo II measure id (e.g., op.exp.5)"
    ),
    sector: Optional[str] = Query(
        None, description="Sector code (e.g., fintech, salud, todos)"
    ),
    ens_category: Optional[str] = Query(
        None, description="ENS category (B | M | A)"
    ),
    db: AsyncSession = Depends(get_db),
) -> LegalObligationCatalogList:
    """List catalog entries · optional filters.

    Mutually exclusive filters (use 1 at a time for predictable results).
    If no filter provided · returns empty (use specific filter to query).
    """
    filters_provided = [
        bool(regulacion),
        bool(ens_measure),
        bool(sector),
        bool(ens_category),
    ]
    if sum(filters_provided) == 0:
        raise HTTPException(
            status_code=400,
            detail=(
                "At least one filter required: regulacion, ens_measure, "
                "sector, or ens_category"
            ),
        )
    if sum(filters_provided) > 1:
        raise HTTPException(
            status_code=400,
            detail=(
                "Only one filter allowed at a time · choose regulacion OR "
                "ens_measure OR sector OR ens_category"
            ),
        )

    if regulacion:
        if regulacion not in VALID_REGULATIONS:
            raise HTTPException(
                status_code=400,
                detail=f"regulacion must be one of {sorted(VALID_REGULATIONS)}",
            )
        rows = await list_by_regulation(db, regulacion)
    elif ens_measure:
        rows = await list_by_ens_measure(db, ens_measure)
    elif sector:
        rows = await list_by_sector(db, sector)
    elif ens_category:
        if ens_category not in VALID_CATEGORIES:
            raise HTTPException(
                status_code=400,
                detail=f"ens_category must be one of {sorted(VALID_CATEGORIES)}",
            )
        rows = await list_by_ens_category(db, ens_category)
    else:
        rows = []

    return LegalObligationCatalogList(
        total=len(rows),
        items=[LegalObligationCatalogRead.model_validate(r) for r in rows],
    )


@router.get("/catalog/{codigo}", response_model=LegalObligationCatalogRead)
async def get_catalog_entry(
    codigo: str,
    db: AsyncSession = Depends(get_db),
) -> LegalObligationCatalogRead:
    """Lookup single entry by canonical codigo (e.g., RGPD-ART-32)."""
    row = await get_by_codigo(db, codigo)
    if not row:
        raise HTTPException(
            status_code=404,
            detail=f"Legal obligation '{codigo}' not found in catalog",
        )
    return LegalObligationCatalogRead.model_validate(row)
