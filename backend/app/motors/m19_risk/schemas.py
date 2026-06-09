"""Motor 19 — Project Risk Management — Pydantic schemas.

Patron consistente con M12 y M3. Usa ConfigDict(from_attributes=True)
para auto-mapping desde modelos SQLAlchemy.
"""
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# === ProjectRisk CRUD ===

class ProjectRiskCreate(BaseModel):
    """Create a new project risk manually (not from catalog)."""
    risk_code: str = Field(..., max_length=20)
    titulo: str = Field(..., max_length=255)
    descripcion: str | None = None
    categoria: str | None = None
    probabilidad: float | None = Field(None, ge=0.0, le=1.0)
    impacto_dias: int | None = Field(None, ge=0)
    impacto_euros: float | None = Field(None, ge=0)
    owner: str | None = Field(None, max_length=255)
    trigger_condicion: str | None = None
    mitigation_plan: dict[str, Any] | None = None
    contingency_plan: dict[str, Any] | None = None


class ProjectRiskUpdate(BaseModel):
    """Partial update of a project risk. All fields optional."""
    titulo: str | None = Field(None, max_length=255)
    descripcion: str | None = None
    categoria: str | None = None
    probabilidad: float | None = Field(None, ge=0.0, le=1.0)
    impacto_dias: int | None = Field(None, ge=0)
    impacto_euros: float | None = Field(None, ge=0)
    owner: str | None = Field(None, max_length=255)
    trigger_condicion: str | None = None
    mitigation_plan: dict[str, Any] | None = None
    contingency_plan: dict[str, Any] | None = None


class ProjectRiskOut(BaseModel):
    """Full project risk response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    risk_code: str
    titulo: str
    descripcion: str | None
    categoria: str | None
    probabilidad: float | None
    impacto_dias: int | None
    impacto_euros: float | None
    owner: str | None
    trigger_condicion: str | None
    status: str | None
    mitigation_plan: dict[str, Any] | None
    contingency_plan: dict[str, Any] | None
    materialization_evidence: dict[str, Any] | None = None
    closure_evidence: dict[str, Any] | None = None
    materializado_at: datetime | None
    cerrado_at: datetime | None
    created_at: datetime
    updated_at: datetime | None


# === Lifecycle transitions ===

class MonitorRiskRequest(BaseModel):
    """Transition identificado -> monitorizado."""
    notas: str | None = None


class MaterializeRiskRequest(BaseModel):
    """Transition monitorizado -> materializado (trigger activated)."""
    trigger_evidence: str = Field(..., min_length=1)
    materialized_by: str | None = Field(None, max_length=255)
    ejecutar_contingencia: bool = Field(True)


class CloseRiskRequest(BaseModel):
    """Transition to cerrado."""
    resolution_notes: str = Field(..., min_length=1)
    closed_by: str | None = Field(None, max_length=255)


# === Catalog operations ===

class InstantiateCatalogRequest(BaseModel):
    """Instantiate the 30 base risks from catalog for a project."""
    force: bool = Field(False, description="Re-instantiate even if already loaded")
    only_categorias: list[str] | None = Field(None)


class InstantiateCatalogResponse(BaseModel):
    """Response of catalog instantiation."""
    project_id: UUID
    risks_created: int
    risks_skipped: int
    catalog_version: str
    categorias_loaded: list[str]


# === Dashboard ===

class RiskDashboardItem(BaseModel):
    """One risk in the dashboard with semaphore."""
    id: UUID
    risk_code: str
    titulo: str
    categoria: str | None
    status: str | None
    probabilidad: float | None
    impacto_dias: int | None
    score: float
    semaforo: str  # verde | amarillo | rojo
    owner: str | None
    materializado_at: datetime | None = None


class RiskDashboardResponse(BaseModel):
    """Dashboard overview for Marcos weekly review."""
    project_id: UUID
    total_risks: int
    by_status: dict[str, int]
    by_categoria: dict[str, int]
    by_semaforo: dict[str, int]
    top_critical: list[RiskDashboardItem]
    recently_materialized: list[RiskDashboardItem]
    generated_at: datetime


# === Filters ===

class RiskListFilters(BaseModel):
    """Query filters for listing risks."""
    status: str | None = None
    categoria: str | None = None
    owner: str | None = None
    semaforo: str | None = None
