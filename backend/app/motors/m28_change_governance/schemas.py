"""Motor 28 — Pydantic schemas."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ChangeIntake(BaseModel):
    description: str = Field(..., min_length=10, max_length=2000)
    requested_by: str = Field(..., min_length=2, max_length=120)
    proposed_date: str | None = None


class ChangeAssessRequest(BaseModel):
    answers: dict[str, bool]


class ChangeAssessmentOut(BaseModel):
    change_id: uuid.UUID
    project_id: uuid.UUID
    description: str
    materiality_level: Literal["MINOR", "RELEVANT", "MATERIAL"]
    materiality_score: int
    impact_vector: dict[str, bool]
    required_documents: list[str]
    required_workflows: list[str]
    required_signoffs: list[str]
    customer_actions: list[str]
    deadline_policy: str
    assessed_at: datetime


class RecategorizationCreate(BaseModel):
    change_id: uuid.UUID
    new_category: Literal["BASICA", "MEDIA", "ALTA"]
    rationale: str = Field(..., min_length=10, max_length=2000)


class ExtraordinaryAuditCreate(BaseModel):
    change_id: uuid.UUID
    rationale: str = Field(..., min_length=10, max_length=2000)
    target_date: str | None = None


class TopologyReviewRequest(BaseModel):
    sector: str
    employees: int = Field(..., ge=1)
    has_internal_it: bool
    has_internal_ciso: bool
    multi_site: bool
    category: Literal["BASICA", "MEDIA", "ALTA"]


class TopologyOut(BaseModel):
    project_id: uuid.UUID
    recommended_pattern: str
    pattern_detail: dict[str, Any]
    requires_memo: bool


class ImpactDetailOut(BaseModel):
    change_id: uuid.UUID
    impact_vector: dict[str, bool]
    materiality_level: str
    materiality_score: int
