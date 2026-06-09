"""Motor 4 -- Gap Analysis Engine -- Pydantic schemas.

Pattern consistent with M19 and M3. Uses ConfigDict(from_attributes=True).
"""
from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# === Gap Finding CRUD ===

class GapFindingOut(BaseModel):
    """Full gap finding response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    fuente: str | None
    severidad: str | None
    medida_afectada: str | None
    descripcion: str | None
    evidencia_relacionada: str | None
    estado: str | None
    asignado_a: str | None
    fecha_objetivo: date | None
    metadata_jsonb: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime | None


class GapFindingUpdate(BaseModel):
    """Partial update of a gap finding."""
    severidad: str | None = None
    estado: str | None = None
    asignado_a: str | None = Field(None, max_length=255)
    fecha_objetivo: date | None = None
    descripcion: str | None = None


# === Lifecycle transitions ===

class CloseGapRequest(BaseModel):
    """Close a gap finding."""
    resolution_notes: str = Field(..., min_length=1)
    closed_by: str | None = Field(None, max_length=255)


# === Analysis ===

class AnalyzeProjectRequest(BaseModel):
    """Request to run gap analysis on a project."""
    force: bool = Field(False, description="Re-analyze even if already analyzed")
    categoria_objetivo: str | None = Field(
        None,
        description="Override system category (BASICA/MEDIA/ALTA). Auto-detected if omitted.",
    )


class AnalyzeProjectResponse(BaseModel):
    """Response from gap analysis execution."""
    project_id: UUID
    categoria_usada: str
    dda_entries_evaluated: int
    gaps_created: int
    gaps_by_severidad: dict[str, int]
    quick_wins_count: int
    critical_nuclear_gaps: list[str]
    catalog_version: str
    generated_at: datetime


# === Dashboard ===

class GapDashboardItem(BaseModel):
    """One gap in the dashboard."""
    id: UUID
    medida_afectada: str | None
    severidad: str | None
    severidad_numeric: int = 0
    estado: str | None
    esfuerzo_horas: int | None = None
    quick_win: bool = False
    nuclear: bool = False
    familia: str | None = None
    semaforo: str = "verde"


class GapDashboardResponse(BaseModel):
    """Dashboard overview for gap analysis."""
    project_id: UUID
    total_gaps: int
    by_severidad: dict[str, int]
    by_familia: dict[str, int]
    by_estado: dict[str, int]
    by_semaforo: dict[str, int]
    top_10_critical: list[GapDashboardItem]
    quick_wins: list[GapDashboardItem]
    nuclear_gaps: list[GapDashboardItem]
    generated_at: datetime


# === Filters ===

class GapListFilters(BaseModel):
    """Query filters for listing gaps."""
    severidad: str | None = None
    estado: str | None = None
    familia: str | None = None
    only_quick_wins: bool = False
    only_nuclear: bool = False
