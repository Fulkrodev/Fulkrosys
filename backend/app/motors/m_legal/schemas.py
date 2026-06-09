"""Pydantic schemas · legal_obligations_catalog read-only API.

Sub-atom 1.C.0.C.expand v3.9.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class LegalObligationCatalogRead(BaseModel):
    """Response schema · single legal obligation entry."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    codigo: str
    regulacion: str = Field(description="RGPD | LOPDGDD | NIS2 | DORA | AI_Act")
    articulo: Optional[str] = None
    titulo: str
    obligacion: str
    sector_aplica: Optional[list[str]] = None
    ens_categoria_aplica: Optional[list[str]] = None
    evidencia_requerida: Optional[str] = None
    vinculo_medida_ens: Optional[list[str]] = None
    fuente_url: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class LegalObligationCatalogList(BaseModel):
    """Response schema · list of legal obligations + total."""

    total: int = Field(description="Total entries matching filter")
    items: list[LegalObligationCatalogRead]
