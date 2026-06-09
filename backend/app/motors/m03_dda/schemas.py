"""Motor 3 — DdA Engine Schemas Pydantic."""
from datetime import datetime, date
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from backend.app.motors.m03_dda.enums import (
    EstadoImplementacion,
    CategoriaSistema,
)


class DdaCreateRequest(BaseModel):
    """Crear nueva DdA para un proyecto."""
    project_id: UUID
    system_category: CategoriaSistema
    responsable: str | None = None


class DdaEntryUpdateRequest(BaseModel):
    """Actualizar el estado de una entry de DdA."""
    estado_implementacion: EstadoImplementacion | None = None
    justificacion_no_aplica: str | None = None
    refuerzos_aplicados: list[str] | None = None
    responsable: str | None = None
    observaciones: str | None = None


class DdaEntryOut(BaseModel):
    """Una entry de DdA (una medida del Anexo II para un proyecto)."""
    id: UUID
    project_id: UUID
    measure_codigo: str
    measure_nombre: str
    measure_marco: str
    measure_familia: str | None
    aplicabilidad: str
    estado_implementacion: str
    justificacion_no_aplica: str | None
    refuerzos_aplicados: list[str] | None
    magerit_safeguards: list[str]
    responsable: str | None
    observaciones: str | None
    version: int | None
    aprobado_por: str | None
    fecha_aprobacion: date | None


class DdaCompletionStats(BaseModel):
    """Stats de completitud para dashboard."""
    project_id: UUID
    total_medidas: int
    total_aplicables: int
    no_aplica: int
    implantadas: int
    parcial: int
    no_implantadas: int
    no_valoradas: int
    completion_pct: float


class DdaGenerateResult(BaseModel):
    """Resultado de generar una DdA."""
    project_id: UUID
    system_category: CategoriaSistema
    total_entries: int
    aplicables: int
    no_aplica: int


class DdaFreezeResult(BaseModel):
    """Resultado de congelar una DdA."""
    project_id: UUID
    aprobado_por: str
    fecha_aprobacion: str
    frozen_entries: int


# === SIGNATURE RE-INTEGRATION M3+M12 (M3-G2) ===

class RequestE040SignatureBody(BaseModel):
    recipient_email: EmailStr
    recipient_name: str | None = Field(None, max_length=120)
    recipient_role: str = Field("Responsable de Seguridad", max_length=120)


class RequestE040SignatureResponse(BaseModel):
    link_id: UUID
    magic_link_url: str
    otp: str
    expires_at: datetime
    recipient_email: str
    previous_link_revoked: bool
    dda_snapshot_hash: str
    frozen_at: str
    total_entries: int


class E040SignatureStatusResponse(BaseModel):
    project_id: UUID
    has_signature_request: bool
    is_frozen: bool
    total_entries: int
    link_id: UUID | None = None
    state: str | None = None
    issued_at: datetime | None = None
    expires_at: datetime | None = None
    consumed_at: datetime | None = None
    recipient_email: str | None = None
