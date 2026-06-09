"""Pydantic schemas de la API Motor 16."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field, model_validator

from .enums import Role, Sector, SessionState
from .types import Question


class CreateSessionBody(BaseModel):
    sector: Sector
    role: Role
    interlocutor_email: EmailStr
    interlocutor_name: Optional[str] = Field(None, max_length=200)
    ttl_hours: int = Field(168, ge=1, le=720)
    language: str = Field("es", pattern=r'^(es|en)$')
    metadata_extra: Optional[dict] = None


class CreateSessionResponse(BaseModel):
    session_id: uuid.UUID
    template_id: str
    template_nombre: str
    tiempo_estimado_minutos: int
    total_questions: int
    # Post-MB-4.bis3 (ADR-020 v3): magic_link_id/url None · cliente accede
    # /client-portal/onboarding directly. Campos preservados para compat
    # API admin pero siempre None.
    magic_link_id: uuid.UUID | None = None
    magic_link_url: str | None = None
    otp: str | None = None
    expires_at: datetime
    state: SessionState
    portal_url: str | None = "/client-portal/onboarding"


class CreatePreclienteSessionBody(BaseModel):
    """Batch B · trigger admin del diagnóstico previo.

    #7.3: acepta ``lead_id`` → crea/reusa el PROYECTO LIGERO del lead (cierra la
    costura antes fuera de alcance). ``project_id`` sigue admitido (proyecto ya
    existente). Al menos uno de los dos es obligatorio. sector/role se fijan a
    PRECLIENTE/SPONSOR en el endpoint."""
    lead_id: Optional[uuid.UUID] = None
    project_id: Optional[uuid.UUID] = None
    interlocutor_email: EmailStr
    interlocutor_name: Optional[str] = Field(None, max_length=200)
    ttl_hours: int = Field(336, ge=1, le=720)  # 14 días por defecto (cat F M12)
    language: str = Field("es", pattern=r'^(es|en)$')

    @model_validator(mode="after")
    def _require_lead_or_project(self) -> "CreatePreclienteSessionBody":
        if self.lead_id is None and self.project_id is None:
            raise ValueError("Se requiere lead_id o project_id")
        return self


class PreclienteEmailTemplate(BaseModel):
    subject: str
    html: str
    text: str


class CreatePreclienteSessionResponse(BaseModel):
    session_id: uuid.UUID
    magic_link_id: uuid.UUID | None
    magic_link_url: str | None
    expires_at: datetime
    state: SessionState
    # Plantilla branded lista para que Marcos la envíe A MANO (NO auto-send).
    email: PreclienteEmailTemplate


class SessionSummary(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    template_id: str | None
    sector: str | None
    role: str | None
    interlocutor_email: str | None
    interlocutor_name: str | None
    state: str | None
    total_questions: int
    answered_questions: int
    progress_percentage: float
    created_at: datetime
    sent_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    expires_at: datetime | None


class SessionDetail(SessionSummary):
    magic_link_id: uuid.UUID | None
    language: str | None
    metadata_extra: dict | None


class TemplateSummary(BaseModel):
    id: str
    version: str
    sector: Sector
    role: Role
    nombre: str
    descripcion: str
    tiempo_estimado_minutos: int
    language: str
    total_questions: int


class CatalogResponse(BaseModel):
    total: int
    templates: list[TemplateSummary]
    available_sectors: list[Sector]


class MarkSessionSentResponse(BaseModel):
    session_id: uuid.UUID
    state: SessionState
    sent_at: datetime


class CancelSessionBody(BaseModel):
    reason: str | None = Field(None, max_length=500)


class CancelSessionResponse(BaseModel):
    session_id: uuid.UUID
    state: SessionState
    magic_link_revoked: bool


# ==== CLIENT-SIDE (M16-B) ====

class ConsumeBody(BaseModel):
    token: str = Field(..., min_length=10)
    otp: str | None = Field(None, max_length=6)


class ConsumeResponse(BaseModel):
    session_id: uuid.UUID
    session_secret: str
    template_id: str
    template_nombre: str
    tiempo_estimado_minutos: int
    total_questions: int
    answered_questions: int
    progress_percentage: float
    sections: list[str]
    state: SessionState


class SubmitAnswerBody(BaseModel):
    question_id: str = Field(..., min_length=3, max_length=80)
    answer_value: Any


class SubmitAnswerResponse(BaseModel):
    question_id: str
    saved: bool
    progress_percentage: float
    state: SessionState


class NextQuestionResponse(BaseModel):
    done: bool
    question: Question | None = None
    progress_percentage: float
    current_section: str | None = None
    remaining_required: int


class FinalSubmitBody(BaseModel):
    allow_partial: bool = False


class FinalSubmitResponse(BaseModel):
    session_id: uuid.UUID
    state: SessionState
    completed_at: datetime | None
    missing_required: list[str]


class ClientProgressResponse(BaseModel):
    session_id: uuid.UUID
    state: str
    total_questions: int
    answered_questions: int
    progress_percentage: float
    sections_completed: list[str]
    sections_partial: list[str]
