"""Tipos Pydantic del catalogo de plantillas onboarding."""
from __future__ import annotations

import re
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from .enums import QuestionType, Role, Sector

TEMPLATE_ID_RE = re.compile(r'^onb-[a-z_]+-[a-z_]+-v\d+$')
QUESTION_ID_RE = re.compile(r'^q-[a-z0-9_]+$')


class QuestionOption(BaseModel):
    value: str = Field(..., min_length=1, max_length=80)
    label: str = Field(..., min_length=1, max_length=200)


class BranchingCondition(BaseModel):
    """Condition for skip_if. If true, the question is skipped."""
    question_id: str
    operator: str = Field(..., pattern=r'^(equals|not_equals|in|contains)$')
    value: Any


class QuestionValidation(BaseModel):
    required: bool = False
    min_length: Optional[int] = Field(None, ge=0)
    max_length: Optional[int] = Field(None, le=10000)
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    regex: Optional[str] = None


class Question(BaseModel):
    id: str
    type: QuestionType
    section: str = Field(..., min_length=1, max_length=50)
    label: str = Field(..., min_length=5, max_length=500)
    tooltip: Optional[str] = Field(None, max_length=1000)
    example: Optional[str] = Field(None, max_length=500)
    options: Optional[list[QuestionOption]] = None
    validation: QuestionValidation = Field(default_factory=QuestionValidation)
    placeholder: Optional[str] = Field(None, max_length=200)
    skip_if: Optional[BranchingCondition] = None
    # Batch B diagnóstico previo: etiqueta INTERNA para Marcos (NUNCA se muestra
    # al lead · el frontend no la renderiza). Principio "el formulario CAPTURA,
    # Marcos CATEGORIZA": p.ej. la pregunta de datos personales lleva
    # "contexto_rgpd" para distinguir marco RGPD de dimensión ENS. Ninguna
    # pregunta revela al lead su categoría ENS.
    internal_tag: Optional[str] = Field(None, max_length=80)

    @field_validator('id')
    @classmethod
    def _validate_id(cls, v: str) -> str:
        if not QUESTION_ID_RE.match(v):
            raise ValueError(f'id de pregunta no cumple patron q-<snake_case>: {v}')
        return v

    @field_validator('options')
    @classmethod
    def _validate_options_for_select(cls, v, info):
        qtype = info.data.get('type')
        if qtype in (QuestionType.SINGLE_SELECT, QuestionType.MULTI_SELECT):
            if not v or len(v) < 2:
                raise ValueError(f'{qtype} requiere al menos 2 opciones')
        return v


class OnboardingTemplate(BaseModel):
    id: str
    version: str = Field(..., pattern=r'^\d+\.\d+$')
    sector: Sector
    role: Role
    nombre: str = Field(..., min_length=5, max_length=120)
    descripcion: str = Field(..., min_length=20, max_length=1000)
    tiempo_estimado_minutos: int = Field(..., ge=5, le=120)
    language: str = Field("es", pattern=r'^(es|en)$')
    questions: list[Question] = Field(..., min_length=3, max_length=80)

    @field_validator('id')
    @classmethod
    def _validate_id(cls, v: str) -> str:
        if not TEMPLATE_ID_RE.match(v):
            raise ValueError(f'id no cumple patron onb-<sector>-<role>-vN: {v}')
        return v

    @field_validator('questions')
    @classmethod
    def _validate_unique_question_ids(cls, v: list[Question]) -> list[Question]:
        ids = [q.id for q in v]
        if len(ids) != len(set(ids)):
            raise ValueError('question ids duplicados dentro de la plantilla')
        return v
