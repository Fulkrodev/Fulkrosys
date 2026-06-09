"""Motor 5 -- Obligations Library -- Pydantic types.

Defines the validation schemas for obligation templates loaded from
the JSON library. Each template describes a reusable obligation that
gets instantiated per-project.
"""
from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator, model_validator

# ── Valid domain constants ──────────────────────────────────────────

CATEGORIES_VALID = frozenset({
    "organizativo",
    "operacional",
    "medidas_proteccion",
})

EXECUTION_MODES_VALID = frozenset({
    "consultor_genera",
    "cliente_aporta_evidencia",
    "mixto",
    "automatizado",
})

ENTREGABLE_TIPOS_VALID = frozenset({
    "documento",
    "configuracion",
    "evidencia",
    "informe",
    "procedimiento",
    "registro",
    "politica",
    "plan",
    "acta",
    "captura",
})

MAGIC_LINK_TEMPLATES_VALID = frozenset({
    "upload_evidence",
    "fill_form",
    "review_and_sign",
    "download_report",
    "confirm_action",
    None,
})

# Template ID pattern: OBL-{measure_code}-{NNN}
_TEMPLATE_ID_RE = re.compile(r"^OBL-[\w.]+-\d{3}$")

# Measure code pattern: familia.subfamilia.N or familia.N
_MEASURE_CODE_RE = re.compile(r"^[a-z]+(\.[a-z]+)*\.\d+$")


class ObligationTemplate(BaseModel):
    """Single obligation template from the JSON library."""

    id: str = Field(
        ...,
        min_length=8,
        max_length=80,
        description="Template ID in format OBL-{measure_code}-{NNN}",
    )
    measure_code: str = Field(
        ...,
        min_length=3,
        max_length=40,
        description="ENS measure code, e.g. org.1, op.acc.6",
    )
    titulo: str = Field(
        ...,
        min_length=5,
        max_length=200,
        description="Short human-readable title",
    )
    descripcion: str = Field(
        ...,
        min_length=10,
        description="Detailed description of the obligation",
    )
    categoria: str = Field(
        ...,
        description="Category: organizativo | operacional | medidas_proteccion",
    )
    modo_ejecucion: str = Field(
        ...,
        description="Execution mode",
    )
    entregable_tipo: str = Field(
        ...,
        description="Expected deliverable type",
    )
    entregable_esperado: str = Field(
        ...,
        min_length=5,
        description="Human description of expected deliverable",
    )
    esfuerzo_horas: float = Field(
        ...,
        gt=0,
        le=500,
        description="Estimated effort in hours",
    )
    responsable: str = Field(
        ...,
        min_length=2,
        description="Default responsible role",
    )
    magic_link_template: str | None = Field(
        default=None,
        description="Magic link template name if applicable",
    )
    dependencias_template_ids: list[str] = Field(
        default_factory=list,
        description="List of prerequisite template IDs",
    )
    criterios_aceptacion: list[str] = Field(
        ...,
        min_length=1,
        description="Acceptance criteria list (at least one)",
    )
    fuente_normativa: list[str] = Field(
        ...,
        min_length=1,
        description="Normative sources (at least one)",
    )
    version: str = Field(
        default="1.0",
        description="Template version",
    )

    @field_validator("id")
    @classmethod
    def validate_template_id(cls, v: str) -> str:
        if not _TEMPLATE_ID_RE.match(v):
            raise ValueError(
                f"Template ID '{v}' does not match pattern OBL-{{code}}-NNN"
            )
        return v

    @field_validator("measure_code")
    @classmethod
    def validate_measure_code(cls, v: str) -> str:
        if not _MEASURE_CODE_RE.match(v):
            raise ValueError(
                f"Measure code '{v}' does not match pattern familia.N or familia.sub.N"
            )
        return v

    @field_validator("categoria")
    @classmethod
    def validate_categoria(cls, v: str) -> str:
        if v not in CATEGORIES_VALID:
            raise ValueError(
                f"Invalid categoria '{v}'. Must be one of: {sorted(CATEGORIES_VALID)}"
            )
        return v

    @field_validator("modo_ejecucion")
    @classmethod
    def validate_modo_ejecucion(cls, v: str) -> str:
        if v not in EXECUTION_MODES_VALID:
            raise ValueError(
                f"Invalid modo_ejecucion '{v}'. Must be one of: {sorted(EXECUTION_MODES_VALID)}"
            )
        return v

    @field_validator("entregable_tipo")
    @classmethod
    def validate_entregable_tipo(cls, v: str) -> str:
        if v not in ENTREGABLE_TIPOS_VALID:
            raise ValueError(
                f"Invalid entregable_tipo '{v}'. Must be one of: {sorted(ENTREGABLE_TIPOS_VALID)}"
            )
        return v

    @field_validator("magic_link_template")
    @classmethod
    def validate_magic_link_template(cls, v: str | None) -> str | None:
        if v is not None and v not in MAGIC_LINK_TEMPLATES_VALID:
            raise ValueError(
                f"Invalid magic_link_template '{v}'. Must be one of: {sorted(x for x in MAGIC_LINK_TEMPLATES_VALID if x)}"
            )
        return v

    @model_validator(mode="after")
    def id_matches_measure_code(self) -> "ObligationTemplate":
        """Ensure the template ID contains the measure_code."""
        expected_prefix = f"OBL-{self.measure_code}-"
        if not self.id.startswith(expected_prefix):
            raise ValueError(
                f"Template ID '{self.id}' must start with '{expected_prefix}'"
            )
        return self


class ObligationsLibrary(BaseModel):
    """Wrapper model for the full obligations library JSON."""

    version: str = Field(..., description="Library version")
    templates: list[ObligationTemplate] = Field(
        ...,
        min_length=1,
        description="List of obligation templates",
    )
