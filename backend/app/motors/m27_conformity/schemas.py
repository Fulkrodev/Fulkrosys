"""Motor 27 — Pydantic schemas."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from backend.app.motors.m27_conformity.route_machine import RouteState, RouteType
from backend.app.motors.m27_conformity.submission_machine import SubmissionState


# ── Conformity Route ───────────────────────────────────────────────────────

class RouteLockRequest(BaseModel):
    route_type: RouteType
    category: Literal["BASICA", "MEDIA", "ALTA"]
    overlay_code: str | None = Field(default=None, max_length=64)
    rationale: str = Field(..., min_length=10, max_length=2000)


class ConformityRouteOut(BaseModel):
    project_id: uuid.UUID
    route_type: RouteType
    state: RouteState
    category: str
    overlay_code: str | None
    locked_at: datetime | None
    next_review_due: date | None


class ConformityStatus(BaseModel):
    project_id: uuid.UUID
    route: ConformityRouteOut | None
    submissions_count: int
    pending_submissions: int
    renewal_state: str | None
    next_renewal_due: date | None
    invariants_ok: bool
    invariant_violations: list[str] = Field(default_factory=list)


# ── Basic Declaration (E-041 a E-044) ──────────────────────────────────────

class DeclarationGenerateRequest(BaseModel):
    requested_by: str = Field(..., min_length=2, max_length=120)
    notes: str | None = Field(default=None, max_length=2000)


class DeclarationOut(BaseModel):
    project_id: uuid.UUID
    declaration_id: uuid.UUID
    documents: list[str]   # codigos E-041..E-044
    generated_at: datetime
    state: Literal["draft", "ready_for_signature", "signed"]


# ── Submission ─────────────────────────────────────────────────────────────

class SubmissionCreate(BaseModel):
    target: Literal["AUDITOR", "REGISTRO", "AAPP", "PILAR", "LUCIA", "INES"]
    payload_template: str = Field(..., min_length=2, max_length=64)
    justification: str | None = Field(default=None, max_length=2000)


class SubmissionOut(BaseModel):
    submission_id: uuid.UUID
    project_id: uuid.UUID
    target: str
    state: SubmissionState
    payload_present: bool
    proof_present: bool
    created_at: datetime
    submitted_at: datetime | None
    completed_at: datetime | None


class SubmissionProofUpload(BaseModel):
    proof_type: Literal["pdf", "zip", "screenshot", "registry_id"]
    proof_reference: str = Field(..., min_length=1, max_length=500)
    completed: bool = False


# ── Renewal Clock ──────────────────────────────────────────────────────────

class RenewalCampaignOut(BaseModel):
    project_id: uuid.UUID
    state: Literal[
        "T-180", "T-120", "T-90", "T-60", "T-30",
        "DUE", "IN_PROGRESS", "COMPLETED", "LAPSED",
    ]
    target_renewal_date: date
    days_remaining: int
    actions_required: list[str]


# ── External Tool Export ───────────────────────────────────────────────────

class ExternalExportCreate(BaseModel):
    tool: Literal["PILAR", "LUCIA", "INES", "Registro"]
    params: dict[str, Any] = Field(default_factory=dict)


class ExternalExportOut(BaseModel):
    export_id: uuid.UUID
    tool: str
    artifact_path: str
    artifact_hash: str
    checklist: list[str]
    created_at: datetime
    proof_uploaded: bool = False


# ── PCE Overlay ────────────────────────────────────────────────────────────

class PceOverlayOut(BaseModel):
    project_id: uuid.UUID
    overlay_code: str | None
    overlay_name: str | None
    extra_controls: list[str] = Field(default_factory=list)
    detection_confidence: float = 0.0
    rationale: str | None = None
