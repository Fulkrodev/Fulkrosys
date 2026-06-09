"""Motor 30 — Client Contacts: Pydantic schemas in/out.

7 schemas plan v4.2 FASE 5.5.2.3:
  1. ``ClientContactCreate``
  2. ``ClientContactUpdate`` (PATCH semantics, todos opcionales)
  3. ``ClientContactOut`` (detail + list — incluye agregados timeline)
  4. ``ClientContactListItem`` (light variant para listado, sin notas)
  5. ``ClientContactInteractionOut``
  6. ``TimelineEntryOut`` (interaction + entity hint)
  7. ``CopilotContextEntry`` (formatted para A14 system prompt enrichment)
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl

# Categorías de rol soportadas. Bloque 1: 14 categorías plan v4.2 (CRM-friendly).
# Bloque 2: 5 roles canónicos ENS (CCN-STIC 801) añadidos en SAN-C.MB-9.5.
# La columna BD ``role_category VARCHAR(50)`` acepta cualquier string · este
# Literal es el contrato Pydantic vigente. Backwards-compatible: contactos
# pre-existentes con categorías Bloque 1 siguen válidos.
RoleCategory = Literal[
    # Bloque 1 · CRM categorías (plan v4.2)
    "sponsor",
    "rseg",
    "ciso",
    "cto",
    "cio",
    "dpo",
    "legal",
    "compras",
    "rrhh",
    "operaciones",
    "tecnico",
    "auditor_interno",
    "consultor_externo",
    "usuario_final",
    "otros",
    # Bloque 2 · Roles ENS canónicos (CCN-STIC 801) · SAN-C.MB-9.5
    "responsable_informacion",   # RI
    "responsable_servicio",      # RS
    "responsable_seguridad",     # RSEG (alias formal de "rseg")
    "responsable_sistema",       # RSIS
    "punto_contacto_ccn",        # POC ante CCN-CERT
    "miembro_comite_seguridad",  # Comité de Seguridad
]

PreferredCommunication = Literal[
    "email",
    "phone",
    "whatsapp",
    "linkedin_dm",
    "portal_inbox",
]

InteractionType = Literal[
    "meeting",
    "message",
    "magic_link",
    "contract_signature",
    "email",
    "other",
]


class ClientContactCreate(BaseModel):
    """Body POST /clients/{client_id}/contacts."""

    full_name: str = Field(..., min_length=1, max_length=255)
    preferred_name: str | None = Field(None, max_length=100)
    email: EmailStr
    phone: str | None = Field(None, max_length=50)
    linkedin_url: HttpUrl | None = None

    role_title: str = Field(..., min_length=1, max_length=150)
    role_category: RoleCategory

    is_primary: bool = False
    is_signatory: bool = False
    has_portal_access: bool = False

    # SAN-E v3.MB-5.0.bis · ENS_REQUIRED stakeholders
    role_ens_required: str | None = Field(None, max_length=30)
    contact_role_notes: str | None = None

    notes_marcos: str | None = None
    preferred_communication: PreferredCommunication | None = None
    timezone: str = Field("Europe/Madrid", max_length=50)


class ClientContactUpdate(BaseModel):
    """Body PATCH /clients/{client_id}/contacts/{contact_id}."""

    full_name: str | None = Field(None, min_length=1, max_length=255)
    preferred_name: str | None = Field(None, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=50)
    linkedin_url: HttpUrl | None = None

    role_title: str | None = Field(None, min_length=1, max_length=150)
    role_category: RoleCategory | None = None

    is_primary: bool | None = None
    is_signatory: bool | None = None
    has_portal_access: bool | None = None

    # SAN-E v3.MB-5.0.bis · ENS_REQUIRED stakeholders (PATCH semantics)
    role_ens_required: str | None = Field(None, max_length=30)
    contact_role_notes: str | None = None

    notes_marcos: str | None = None
    preferred_communication: PreferredCommunication | None = None
    timezone: str | None = Field(None, max_length=50)


class ClientContactOut(BaseModel):
    """GET /clients/{client_id}/contacts/{contact_id} (detalle)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID

    full_name: str
    preferred_name: str | None = None
    email: str
    phone: str | None = None
    linkedin_url: str | None = None

    role_title: str
    role_category: str

    is_primary: bool
    is_signatory: bool
    has_portal_access: bool
    client_user_id: uuid.UUID | None = None

    # SAN-E v3.MB-5.0.bis · ENS_REQUIRED stakeholders
    role_ens_required: str | None = None
    contact_role_notes: str | None = None

    notes_marcos: str | None = None
    preferred_communication: str | None = None
    timezone: str

    is_active: bool
    inactive_reason: str | None = None
    inactive_since: datetime | None = None

    created_at: datetime
    updated_at: datetime | None = None

    last_interaction_at: datetime | None = None
    last_interaction_type: str | None = None
    interactions_count: int = 0


class ClientContactListItem(BaseModel):
    """Variante listado: omite notes_marcos por privacidad + payload size."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    preferred_name: str | None = None
    email: str
    phone: str | None = None
    role_title: str
    role_category: str
    is_primary: bool
    is_signatory: bool
    has_portal_access: bool
    is_active: bool
    last_interaction_at: datetime | None = None
    last_interaction_type: str | None = None


class ClientContactInteractionOut(BaseModel):
    """Entrada interacción cruda (motor 30 timeline raw)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    contact_id: uuid.UUID
    interaction_type: str
    source_motor: str | None = None
    source_id: uuid.UUID | None = None
    summary: str | None = None
    details: dict[str, Any] | None = None
    created_at: datetime


class TimelineEntryOut(BaseModel):
    """GET /timeline — interaction + hint entidad origen.

    Distinto de ``ClientContactInteractionOut`` por incluir info
    derivada para UI (ej. cuándo el motor origen marca el evento).
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    interaction_type: str
    source_motor: str | None = None
    source_id: uuid.UUID | None = None
    summary: str | None = None
    details: dict[str, Any] | None = None
    occurred_at: datetime
    # alias de created_at para semántica timeline


class CopilotContextEntry(BaseModel):
    """Una línea formateada para system prompt A14.

    Devuelta por ``ClientContactService.get_for_copilot_context``.
    """

    full_name: str
    role_title: str
    role_category: str
    is_primary: bool
    is_signatory: bool
    notes_excerpt: str | None = None
    formatted_line: str
    # Línea pre-renderizada lista para inyectar en prompt.
