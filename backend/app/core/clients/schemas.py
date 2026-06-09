"""Core — Clients & Projects: Pydantic schemas."""
import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# === CLIENTS ===

class ClientCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=255)
    cif: str = Field(..., min_length=1, max_length=20)
    sector: str | None = None
    contacto_email: str | None = None
    contacto_telefono: str | None = None


class ClientOut(BaseModel):
    id: uuid.UUID
    nombre: str
    cif: str
    sector: str | None
    contacto_email: str | None
    contacto_telefono: str | None
    created_at: datetime
    # CRITICAL #1 · project_id resuelto (1 proyecto = 1 cliente). El selector
    # navega con ESTE id, no con client.id (que da 404 en /projects/{id}/header).
    project_id: uuid.UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class ClientUpdate(BaseModel):
    """PATCH /clients/{id}: todos los campos opcionales (partial update).

    Sub-fase 5.A FASE 5 — Marcos edita datos cliente desde panel
    /admin/clients/{id} Tab Datos. ``cif`` no se permite cambiar
    (unique constraint + identidad fiscal).
    """

    model_config = ConfigDict(extra="forbid")

    nombre: str | None = Field(default=None, min_length=1, max_length=255)
    sector: str | None = Field(default=None, max_length=100)
    provincia: str | None = Field(default=None, max_length=100)
    numero_empleados: int | None = Field(default=None, ge=0)
    contacto_email: str | None = Field(default=None, max_length=255)
    contacto_telefono: str | None = Field(default=None, max_length=50)
    lead_source: str | None = Field(default=None, max_length=100)


class ClientDetail(BaseModel):
    """GET /clients/{id}: detalle completo + métricas agregadas.

    Sub-fase 5.A FASE 5 — backing del panel /admin/clients/{id}.
    Extiende ``ClientOut`` con ``deleted_at`` (suspend state),
    contadores derivados (projects/users) y ``last_activity_at``
    (max timestamp entre projects/contracts/invoices del cliente).
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str
    cif: str
    sector: str | None
    provincia: str | None
    numero_empleados: int | None
    contacto_email: str | None
    contacto_telefono: str | None
    lead_source: str | None
    logo_path: str | None
    created_at: datetime
    updated_at: datetime | None
    deleted_at: datetime | None

    projects_count: int = Field(default=0, ge=0)
    users_count: int = Field(default=0, ge=0)
    last_activity_at: datetime | None = None


# === AUDIT LOG (lectura) ===

class AuditLogEntry(BaseModel):
    """Entry serializado de ``audit_log`` (read-only, inmutable BD).

    GET /clients/{id}/audit retorna lista filtrada por client_id +
    sus projects asociados. Hash chain (``hash_prev``/``hash_current``)
    se expone para que UI muestre badge integridad.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tabla: str
    registro_id: uuid.UUID
    accion: str
    usuario: str | None
    timestamp: datetime
    payload_old: dict[str, Any] | None
    payload_new: dict[str, Any] | None
    hash_prev: str | None
    hash_current: str | None


class AuditLogPage(BaseModel):
    """Paginación audit log para Tab Audit Log frontend."""

    items: list[AuditLogEntry]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    size: int = Field(ge=1, le=100)


# === FACTURAS AGREGADAS POR CLIENTE (M15 cross-project) ===

class ClientInvoiceAggregated(BaseModel):
    """Invoice resumida para Tab Facturas en /admin/clients/{id}.

    Sub-fase 5.A FASE 5 — endpoint agregado evita N+1 que tendría
    el frontend si tuviese que listar projects + iterar invoices
    por cada uno (decisión audit pre-FASE 5 H4).
    """

    model_config = ConfigDict(from_attributes=True)

    invoice_id: uuid.UUID = Field(alias="id")
    project_id: uuid.UUID | None
    project_name: str | None
    numero_correlativo: str | None
    tipo: str | None
    total: float | None
    estado_pago: str | None
    fecha_emision: date | None
    fecha_vencimiento: date | None


# === PROJECTS ===

class ProjectCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=255)
    categoria_objetivo: str | None = None
    fase: str | None = None


class ProjectOut(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    nombre: str
    fase: str | None
    categoria_objetivo: str | None
    estado: str | None
    # Sub-atom 1.E.2.bis Phase A · lifecycle visible para selector landing
    # + archive (DELETE) response coherente sin breaking change otros callers.
    lifecycle_state: str | None = None
    deleted_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
