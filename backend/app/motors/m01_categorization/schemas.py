"""Motor 1 — Categorization Engine: Pydantic schemas."""
import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# === ENUMS as Literal types ===

ImpactLevelType = Literal["BAJO", "MEDIO", "ALTO"]
CategoryType = Literal["BASICA", "MEDIA", "ALTA"]


# === SYSTEM ===

class SystemCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=255)
    descripcion: str | None = None
    frontera: str | None = None


class SystemOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    nombre: str
    descripcion: str | None
    frontera: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# === INFORMATION TYPES ===

class InformationTypeIn(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=255)
    valoracion_d: ImpactLevelType = "BAJO"
    valoracion_i: ImpactLevelType = "BAJO"
    valoracion_c: ImpactLevelType = "BAJO"
    valoracion_a: ImpactLevelType = "BAJO"
    valoracion_t: ImpactLevelType = "BAJO"
    justificacion: str | None = None


class InformationTypeOut(BaseModel):
    id: uuid.UUID
    nombre: str
    valoracion_d: str | None
    valoracion_i: str | None
    valoracion_c: str | None
    valoracion_a: str | None
    valoracion_t: str | None
    justificacion: str | None

    model_config = ConfigDict(from_attributes=True)


class InformationTypeBatchRequest(BaseModel):
    items: list[InformationTypeIn] = Field(..., min_length=1)


# === SERVICES ===

class ServiceIn(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=255)
    valoracion_d: ImpactLevelType = "BAJO"
    valoracion_i: ImpactLevelType = "BAJO"
    valoracion_c: ImpactLevelType = "BAJO"
    valoracion_a: ImpactLevelType = "BAJO"
    valoracion_t: ImpactLevelType = "BAJO"
    justificacion: str | None = None


class ServiceOut(BaseModel):
    id: uuid.UUID
    nombre: str
    valoracion_d: str | None
    valoracion_i: str | None
    valoracion_c: str | None
    valoracion_a: str | None
    valoracion_t: str | None
    justificacion: str | None

    model_config = ConfigDict(from_attributes=True)


class ServiceBatchRequest(BaseModel):
    items: list[ServiceIn] = Field(..., min_length=1)


# === CATEGORIZATION ===

class CategorizeRequest(BaseModel):
    aprobado_por: str | None = None


class CategorizationOut(BaseModel):
    id: uuid.UUID
    system_id: uuid.UUID
    categoria_resultante: CategoryType
    determining_dimension: str | None = None
    justification: str | None = None
    fecha_acta: date | None
    aprobado_por: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# === HISTORY ===

class CategorizationHistoryItem(BaseModel):
    id: uuid.UUID
    version: int | None
    categoria_resultante: CategoryType
    fecha_acta: date | None
    aprobado_por: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CategorizationVersionDetail(BaseModel):
    id: uuid.UUID
    system_id: uuid.UUID
    version: int | None
    categoria_resultante: CategoryType
    fecha_acta: date | None
    aprobado_por: str | None
    input_snapshot: dict | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# === ACTA E-012 ===

class ActaE012Out(BaseModel):
    markdown_content: str
    metadata: dict


# === DIMENSION SUMMARY ===

class DimensionSummaryOut(BaseModel):
    max_d: ImpactLevelType
    max_i: ImpactLevelType
    max_c: ImpactLevelType
    max_a: ImpactLevelType
    max_t: ImpactLevelType
    projected_category: CategoryType
    info_types_count: int
    services_count: int


# === SIGNATURE RE-INTEGRATION M1+M12 (M12-G1) ===

class RequestSignatureBody(BaseModel):
    recipient_email: EmailStr
    recipient_name: str | None = Field(None, max_length=120)
    recipient_role: str = Field("Responsable de la Información", max_length=120)


class RequestSignatureResponse(BaseModel):
    link_id: uuid.UUID
    magic_link_url: str
    otp: str
    expires_at: datetime
    recipient_email: str
    previous_link_revoked: bool
    acta_snapshot_hash: str


class SignatureStatusResponse(BaseModel):
    system_id: uuid.UUID
    has_signature_request: bool
    link_id: uuid.UUID | None = None
    state: str | None = None
    issued_at: datetime | None = None
    expires_at: datetime | None = None
    consumed_at: datetime | None = None
    recipient_email: str | None = None


# === INHERITED AAPP FLOOR (#5 · Sub-bloque E) ===

class InheritedFloorBody(BaseModel):
    """Suelo de categoría heredado de la AAPP contratante. None = sin herencia."""

    categoria_heredada_aapp: CategoryType | None = None


class InheritedFloorOut(BaseModel):
    project_id: uuid.UUID
    categoria_heredada_aapp: CategoryType | None = None
    categoria_objetivo: str | None = None
    # Variante 2 · el suelo elevó el target categoria_objetivo (solo sube).
    categoria_objetivo_elevated: bool = False
    # #5 cabo · nivel detectado del proyecto (N1/N2/N2.5/N3 · floor_elevation_service)
    # y artefactos regenerados en N2 (propuesta/plan/gap). N2.5/N3 NO llegan aquí:
    # bloquean con 409 (contrato en vuelo / firmado · la incoherencia es imposible).
    level: str | None = None
    regenerated: list[str] = Field(default_factory=list)
