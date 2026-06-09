"""M30 · Pydantic schemas Department (sub-atom 1.C.F.2).

Request + response models + suggestions per category ENS (B/M/A).
Suggestions definidas en service-layer · estos schemas solo describen
el contrato API.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DepartmentBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None


class DepartmentRead(DepartmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class DepartmentSuggestion(BaseModel):
    """Sugerencia per category ENS · usada por SuggestionsBanner UX."""

    code: str
    name: str
    description: str


class DepartmentSuggestionsResponse(BaseModel):
    project_id: uuid.UUID
    project_category: str | None
    suggestions: list[DepartmentSuggestion]
    existing_count: int


class DepartmentBulkCreateBody(BaseModel):
    """Body para bulk-accept suggestions desde admin UI."""

    items: list[DepartmentCreate]


# Sub-atom 1.C.F.3.2 · assign/bulk/list/report shapes
class ContactAssignBody(BaseModel):
    """Body PATCH assign single contact · ``None`` = des-asignar."""

    department_id: uuid.UUID | None = None


class ContactsBulkAssignBody(BaseModel):
    """Body POST bulk-assign · todos los contacts al mismo department."""

    contact_ids: list[uuid.UUID] = Field(..., min_length=1)


class ContactSummaryForDepartment(BaseModel):
    """Vista reducida de empleado para listado per área."""

    id: uuid.UUID
    full_name: str
    email: str
    role_title: str
    role_category: str
    has_portal_access: bool
    department_id: uuid.UUID | None


class DepartmentReportBucket(BaseModel):
    """Bucket per department en report_per_area."""

    department_id: str
    code: str
    name: str
    total_contacts: int
    by_role_category: dict[str, int]


class DepartmentReportUnassigned(BaseModel):
    """Bucket empleados sin asignar."""

    total_contacts: int
    by_role_category: dict[str, int]


class DepartmentReportResponse(BaseModel):
    """Counts empleados per area + breakdown role_category."""

    project_id: str
    departments: list[DepartmentReportBucket]
    unassigned: DepartmentReportUnassigned
    total_employees: int
