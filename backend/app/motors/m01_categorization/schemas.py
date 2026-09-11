"""Motor 1 — Categorization Engine: Pydantic schemas."""
import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# === ENUMS as Literal types ===

ImpactLevelType = Literal["BAJO", "MEDIO", "ALTO"]
# O1.1 · el resumen de dimensiones SI puede devolver NO_AFECTADA y una categoria
# nula: un sistema sin ninguna dimension afectada no se proyecta a BASICA
# (Anexo I punto 3). El tipo de ENTRADA de una valoracion sigue siendo
# BAJO/MEDIO/ALTO -- valorar una dimension es adscribirla --; lo que se relaja es
# el tipo de SALIDA del resumen, que tiene que poder decir "sin adscribir".
ImpactLevelOrUnaffectedType = Literal["NO_AFECTADA", "BAJO", "MEDIO", "ALTO"]
CategoryType = Literal["BASICA", "MEDIA", "ALTA"]
# R05 (E-155 · CCN-STIC 803): servicio finalista (presta el fin del sistema) vs
# instrumental (soporta a otros). Sede física vs región cloud (ubicación real).
ServiceTipoType = Literal["finalista", "instrumental"]
SiteTipoType = Literal["sede_fisica", "region_cloud"]


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
    # R05 · finalista | instrumental (alcance E-155 · CCN-STIC 803)
    tipo: ServiceTipoType | None = None


class ServiceOut(BaseModel):
    id: uuid.UUID
    nombre: str
    valoracion_d: str | None
    valoracion_i: str | None
    valoracion_c: str | None
    valoracion_a: str | None
    valoracion_t: str | None
    justificacion: str | None
    tipo: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ServiceBatchRequest(BaseModel):
    items: list[ServiceIn] = Field(..., min_length=1)


class ServiceTipoUpdate(BaseModel):
    """R05 · edición puntual del tipo de un servicio (editor de alcance)."""
    tipo: ServiceTipoType | None = None


# === SCOPE E-155 · SEDES (system_sites) + EXCLUSIONES (scope_exclusions) ===

class SiteIn(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=255)
    tipo: SiteTipoType | None = None
    direccion: str | None = None
    pais: str | None = Field(None, max_length=100)
    descripcion: str | None = None


class SiteOut(BaseModel):
    id: uuid.UUID
    nombre: str
    tipo: str | None
    direccion: str | None
    pais: str | None
    descripcion: str | None

    model_config = ConfigDict(from_attributes=True)


class SiteBatchRequest(BaseModel):
    items: list[SiteIn] = Field(default_factory=list)


class ExclusionIn(BaseModel):
    elemento: str = Field(..., min_length=1, max_length=255)
    justificacion: str | None = None


class ExclusionOut(BaseModel):
    id: uuid.UUID
    elemento: str
    justificacion: str | None

    model_config = ConfigDict(from_attributes=True)


class ExclusionBatchRequest(BaseModel):
    items: list[ExclusionIn] = Field(default_factory=list)


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
    # Regla 2 · si la categorizacion se calculo con la regla del maximo anterior
    # -- la que adscribia a BAJO las dimensiones NO afectadas, contra el Anexo I
    # punto 3 -- la marca viaja con ella. Sin esto, la marca estaria en la base
    # y no obligaria a nada: nadie la veria.
    requiere_recategorizacion: bool = False
    motivo_recategorizacion: str | None = None

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
    max_d: ImpactLevelOrUnaffectedType
    max_i: ImpactLevelOrUnaffectedType
    max_c: ImpactLevelOrUnaffectedType
    max_a: ImpactLevelOrUnaffectedType
    max_t: ImpactLevelOrUnaffectedType
    # None cuando no hay NINGUNA dimension afectada: no hay nada que proyectar.
    projected_category: CategoryType | None
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
