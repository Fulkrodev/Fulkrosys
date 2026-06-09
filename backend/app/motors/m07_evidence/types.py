"""Pydantic models for evidence type catalog validation."""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class EvidenceTypeTemplate(BaseModel):
    """Schema for a single evidence type in the catalog."""

    id: str = Field(..., min_length=4, max_length=80, pattern=r"^EVT-")
    nombre: str = Field(..., min_length=1, max_length=120)
    descripcion: str = Field(..., min_length=1)
    categoria: str = Field(..., min_length=1, max_length=50)
    mime_types_permitidos: list[str] = Field(..., min_length=1)
    extensiones_permitidas: list[str] = Field(..., min_length=1)
    tamano_max_mb: int = Field(..., gt=0, le=500)
    caducidad_dias: int | None = Field(default=None)
    medidas_asociadas: list[str] = Field(default_factory=list)
    obligatorio: bool = Field(default=False)

    @field_validator("mime_types_permitidos", mode="before")
    @classmethod
    def validate_mime_types(cls, v: list[str]) -> list[str]:
        for mime in v:
            if "/" not in mime:
                raise ValueError(f"Invalid MIME type: {mime}")
        return v

    @field_validator("extensiones_permitidas", mode="before")
    @classmethod
    def validate_extensions(cls, v: list[str]) -> list[str]:
        for ext in v:
            if not ext.startswith("."):
                raise ValueError(f"Extension must start with dot: {ext}")
        return v

    @field_validator("caducidad_dias", mode="before")
    @classmethod
    def validate_caducidad(cls, v: int | None) -> int | None:
        if v is not None and (v < 1 or v > 3650):
            raise ValueError(f"caducidad_dias must be 1-3650 or null, got {v}")
        return v


class EvidenceTypesCatalog(BaseModel):
    """Schema for the full evidence types catalog JSON."""

    version: str = Field(..., min_length=1)
    description: str = Field(default="")
    types: list[EvidenceTypeTemplate] = Field(..., min_length=1)

    @field_validator("types", mode="after")
    @classmethod
    def validate_unique_ids(cls, v: list[EvidenceTypeTemplate]) -> list[EvidenceTypeTemplate]:
        ids = [t.id for t in v]
        if len(ids) != len(set(ids)):
            dupes = [x for x in ids if ids.count(x) > 1]
            raise ValueError(f"Duplicate evidence type IDs: {set(dupes)}")
        return v
