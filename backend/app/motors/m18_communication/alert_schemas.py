"""Schemas Pydantic alertas proactivas (MB-13.4 · ADR-035)."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AlertResponse(BaseModel):
    """Alerta serializada para UI."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    severity: str = Field(..., description="info | warning | critical")
    category: str
    title: str
    description: str | None = None
    action_url: str | None = None
    triggered_by: str | None = None
    triggered_at: datetime
    acknowledged_at: datetime | None = None
    metadata_jsonb: dict | None = None
