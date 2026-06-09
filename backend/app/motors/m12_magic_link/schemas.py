"""Motor 12 — Magic Link Schemas Pydantic."""
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from backend.app.motors.m12_magic_link.purposes import MagicLinkPurpose


class MagicLinkGenerateRequest(BaseModel):
    """Request para generar un magic link (endpoint protegido)."""

    project_id: UUID
    purpose: MagicLinkPurpose
    recipient_email: EmailStr
    scope: dict[str, Any] | None = Field(
        default=None,
        description="Datos especificos del link: document_id, acta_id, etc.",
    )
    allowed_countries: list[str] | None = Field(
        default=None,
        description="Lista ISO paises permitidos. None = sin restriccion.",
    )
    sent_to_contact_id: UUID | None = Field(
        default=None,
        description=(
            "FK opcional client_contacts.id (M30). Si presente, al consumir "
            "el link se loggea interaction_type='magic_link' en timeline "
            "del contacto."
        ),
    )
    # FASE 4.5 sub-bloque A · ADR-011 email customization (migration f658961972a2)
    cc_emails: list[EmailStr] | None = Field(
        default=None,
        description="Carbon copy emails adicionales. Aplicado por EmailSender.",
    )
    custom_subject: str | None = Field(
        default=None,
        max_length=255,
        description="Override del subject default per purpose.",
    )
    custom_body_intro: str | None = Field(
        default=None,
        description="Texto custom Marcos antes del cuerpo template (prepend, no replace).",
    )
    ttl_hours: int | None = Field(
        default=None,
        gt=0,
        description="Override TTL del PurposeConfig default.",
    )
    max_uses: int | None = Field(
        default=None,
        gt=0,
        description="Override max_uses del PurposeConfig default.",
    )


class MagicLinkGenerateResponse(BaseModel):
    """Response tras generar un magic link."""

    magic_link_id: UUID
    token: str = Field(description="JWT firmado Ed25519. SOLO mostrar al creador una vez.")
    otp: str | None = Field(
        default=None,
        description="OTP de 6 digitos si el purpose lo requiere. "
                    "Se envia al destinatario por canal separado.",
    )
    url: str = Field(description="URL completa con el token embebido.")
    expires_at: datetime
    purpose: MagicLinkPurpose
    action_label: str


class MagicLinkGenerateAndSendResponse(BaseModel):
    """#11 · respuesta de generar + ENVIAR el magic link por email (botón manual).

    El token plano sólo existe en el momento de generar (en BD vive hasheado), por
    eso el envío del email ocurre AQUÍ, no como reenvío posterior por id. El envío
    lo dispara Marcos manualmente (botón) · NO es automático."""

    magic_link_id: UUID
    url: str
    expires_at: datetime
    purpose: MagicLinkPurpose
    action_label: str
    otp: str | None = Field(
        default=None,
        description=(
            "OTP de 6 dígitos si el purpose lo requiere. NO se incrusta en el "
            "email del enlace (anularía el 2º factor) · transmitir por canal "
            "separado (SMS/teléfono)."
        ),
    )
    email_sent: bool
    email_backend: str
    email_message_id: str | None = None
    email_error: str | None = None
    recipient_email: str


class MagicLinkConsumeRequest(BaseModel):
    """Request para consumir un magic link (endpoint publico)."""

    token: str = Field(description="JWT del magic link.")
    otp: str | None = Field(
        default=None,
        description="OTP si el purpose lo exige.",
    )
    client_ip: str | None = None
    user_agent: str | None = None


class MagicLinkConsumeResponse(BaseModel):
    """Response tras consumir exitosamente un magic link."""

    magic_link_id: UUID
    purpose: MagicLinkPurpose
    project_id: UUID
    scope: dict[str, Any] | None
    action_label: str
    remaining_uses: int


class MagicLinkRevokeRequest(BaseModel):
    """Request para revocar un magic link activo."""

    magic_link_id: UUID
    reason: str | None = None


# ────────────────────────────────────────────────────────────────────
# FASE 4.5 sub-bloque B · list (admin) + by-token public status
# ────────────────────────────────────────────────────────────────────


class MagicLinkListItem(BaseModel):
    """Subset seguro para list admin (no expone token_hash ni otp_hash)."""

    id: UUID
    project_id: UUID
    tipo_operacion: MagicLinkPurpose
    recipient_email: str | None = None
    cc_emails: list[str] | None = None
    custom_subject: str | None = None
    expira_at: datetime
    max_usos: int | None = None
    usos: int
    revocado: bool
    revoked_at: datetime | None = None
    sent_to_contact_id: UUID | None = None
    created_at: datetime


class MagicLinkPublicStatus(BaseModel):
    """Subset PÚBLICO devuelto en GET /by-token/{token} (sin auth).

    Reglas de privacidad (estricto · ADR-011 · sub-bloque B.1):
    - Solo info necesaria para que la UI sign-flow renderice el contexto.
    - NO expone: id (UUID interno), project_id, token_hash, otp_hash,
      recipient_email completo, cc_emails, custom_subject (interno email),
      custom_body_intro (interno email), sent_to_contact_id, allowed_countries.
    - recipient_email_hint enmascara el email destinatario para que el
      cliente confirme que abrió el link correcto sin filtrar el email
      completo a un atacante con el token.
    """

    tipo_operacion: MagicLinkPurpose
    scope: dict[str, Any] | None = None
    expira_at: datetime
    max_usos: int | None = None
    usos: int
    revocado: bool
    recipient_email_hint: str | None = Field(
        default=None,
        description=(
            "Mascara del email destinatario: 3 primeros chars + *** + dominio "
            "(ej: 'jor***@dataforma.es'). NULL si recipient_email no fijado."
        ),
    )
