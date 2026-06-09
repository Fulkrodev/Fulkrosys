"""Schemas Pydantic para AdminSettings panel /admin/settings.

Validación shape JSONB ANTES de persistir. ENS-correctness:

- ``extra="forbid"`` en cada categoría: rechaza payloads con campos
  no esperados (defensa contra typos del frontend o intentos de
  poison data desde panel admin).
- Type-safe boundaries: tipos explícitos, sin defaults silenciosos
  para campos críticos.
- Pattern validation donde aplica (hex color, locale ISO, IANA
  timezone via str + service-layer check).

Distinción con `app.config.Settings`:

- `Settings`: env-based, immutable runtime, defaults conservadores
- `AdminSettings` (este módulo): BD-based, mutable runtime, override
  panel admin con audit trail (audit_log)

PATCH atómico por categoría (no endpoint "PATCH all"):

- PATCH /api/v1/admin/settings/branding       → BrandingSettings
- PATCH /api/v1/admin/settings/notifications  → NotificationsSettings
- PATCH /api/v1/admin/settings/smtp           → SmtpSettings
- PATCH /api/v1/admin/settings/general        → GeneralSettings
- PATCH /api/v1/admin/settings/analytics      → AnalyticsPrefs

Cada PATCH usa la category schema directamente. `exclude_unset=True`
en service layer permite parciales (update solo campos enviados).

Ver plan v4.2 sección FASE 4 + sub-bloque 4.A.2.a + ADR pendiente
si decisiones nuevas surgen.
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ─────────────────────────────────────────────────────────────────
# Categoría: branding (logos, colores corporativos, footer text)
# ─────────────────────────────────────────────────────────────────


class BrandingSettings(BaseModel):
    """Identidad visual: logo, colores, footer text."""

    model_config = ConfigDict(extra="forbid")

    logo_url: Optional[str] = Field(default=None, max_length=500)
    primary_color: Optional[str] = Field(
        default=None,
        pattern=r"^#[0-9A-Fa-f]{6}$",
        description="Color hex format #RRGGBB",
    )
    secondary_color: Optional[str] = Field(
        default=None,
        pattern=r"^#[0-9A-Fa-f]{6}$",
        description="Color hex format #RRGGBB",
    )
    footer_text: Optional[str] = Field(default=None, max_length=500)


# ─────────────────────────────────────────────────────────────────
# Categoría: notifications (email forward + magic link config v4)
# Plan v4.2 sección 4.2.2 (código literal preservado)
# ─────────────────────────────────────────────────────────────────


class MagicLinkPurposeOverride(BaseModel):
    """Override por purpose en magic_link_per_purpose_overrides dict."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    default_recipient_email: Optional[EmailStr] = None
    cc_emails: List[EmailStr] = Field(default_factory=list)
    template_id: Optional[str] = None


class NotificationsSettings(BaseModel):
    """Email forward + magic link sender config + digest preferences."""

    model_config = ConfigDict(extra="forbid")

    client_messages_forward_enabled: bool = True
    client_messages_forward_to: Optional[EmailStr] = None
    smtp_custom: Optional[Dict] = None
    digest_enabled: bool = True
    digest_time_local: str = Field(
        default="08:00",
        pattern=r"^([01]\d|2[0-3]):[0-5]\d$",
        description="Hora local HH:MM 24h format",
    )
    magic_link_default_sender: Optional[EmailStr] = None
    magic_link_per_purpose_overrides: Dict[str, MagicLinkPurposeOverride] = Field(
        default_factory=dict,
    )
    # #26 · número WhatsApp de Marcos editable desde el panel (antes solo env →
    # no se podía cambiar el destino de notificaciones inbound sin reiniciar).
    # Si vacío, el dispatcher cae al valor de entorno.
    marcos_whatsapp_number: Optional[str] = Field(
        default=None,
        description=(
            "Número WhatsApp de Marcos en E.164 (ej. +34637165328) · destino de "
            "notificaciones inbound. Vacío = usa el valor de entorno."
        ),
        pattern=r"^\+?[1-9]\d{6,14}$",
    )


# ─────────────────────────────────────────────────────────────────
# Categoría: smtp (override env-based defaults Settings)
# ─────────────────────────────────────────────────────────────────


class SmtpSettings(BaseModel):
    """SMTP override custom. Settings env-based son fallback."""

    model_config = ConfigDict(extra="forbid")

    host: Optional[str] = Field(default=None, max_length=255)
    port: Optional[int] = Field(default=None, ge=1, le=65535)
    username: Optional[str] = Field(default=None, max_length=255)
    password: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Password en plano (BD-encrypted en sub-bloque posterior si se requiere)",
    )


# ─────────────────────────────────────────────────────────────────
# Categoría: general (timezone, locale, formato fecha)
# ─────────────────────────────────────────────────────────────────


class GeneralSettings(BaseModel):
    """Configuración general: timezone, locale, formato fecha."""

    model_config = ConfigDict(extra="forbid")

    timezone: str = Field(
        default="Europe/Madrid",
        max_length=50,
        description="IANA timezone identifier (validación contra zoneinfo en service layer)",
    )
    locale: str = Field(
        default="es-ES",
        pattern=r"^[a-z]{2}-[A-Z]{2}$",
        description="Locale ISO format ll-CC",
    )
    date_format: str = Field(
        default="DD/MM/YYYY",
        max_length=20,
    )


# ─────────────────────────────────────────────────────────────────
# Categoría: analytics_prefs (privacidad analytics)
# ─────────────────────────────────────────────────────────────────


class AnalyticsPrefs(BaseModel):
    """Preferencias analytics. Solo campo show_corpus_metric en plan v4.2."""

    model_config = ConfigDict(extra="forbid")

    show_corpus_metric: bool = True


# ─────────────────────────────────────────────────────────────────
# Categoría: fiscal (identidad fiscal del emisor/consultor · punto #44)
# FUENTE ÚNICA: NIF, nombre fiscal/comercial, tipo persona F/J, domicilio
# fiscal estructurado, régimen IVA/IRPF, datos bancarios. Consumida por
# QR Verifactu, PDF factura, contratos/DPA, RoPA, Facturae seller vía
# core.fiscal_identity.get_fiscal_identity. Default régimen: autónomo
# persona física (tipo_persona='F', sujeto_irpf=True).
# ─────────────────────────────────────────────────────────────────


class FiscalSettings(BaseModel):
    """Identidad fiscal del emisor. Todos los campos opcionales (PATCH
    parcial), pero los consumidores exigen al menos ``nif`` +
    ``nombre_fiscal`` + domicilio para emitir factura/contrato válidos."""

    model_config = ConfigDict(extra="forbid")

    # Identidad
    nif: Optional[str] = Field(
        default=None, max_length=20,
        description="NIF/CIF del emisor. Autónomo persona física: NIF con letra (ej. 77171140E).",
    )
    nombre_fiscal: Optional[str] = Field(
        default=None, max_length=200,
        description="Nombre/razón fiscal canónica (persona física del autónomo o razón social SL).",
    )
    nombre_comercial: Optional[str] = Field(
        default=None, max_length=200,
        description="Nombre comercial/marca (ej. FULKRO). Si vacío se usa nombre_fiscal.",
    )
    tipo_persona: Literal["F", "J"] = Field(
        default="F",
        description="F=persona física (autónomo) · J=jurídica (sociedad). Determina PersonTypeCode Facturae.",
    )

    # Domicilio fiscal estructurado (Facturae exige vía + CP + municipio + provincia)
    domicilio_via: Optional[str] = Field(default=None, max_length=250)
    domicilio_cp: Optional[str] = Field(default=None, max_length=10)
    domicilio_municipio: Optional[str] = Field(default=None, max_length=120)
    domicilio_provincia: Optional[str] = Field(default=None, max_length=120)
    domicilio_pais: str = Field(default="España", max_length=80)

    # Régimen impositivo
    iva_pct: float = Field(default=21.0, ge=0, le=100, description="Tipo IVA general aplicable (%).")
    sujeto_irpf: bool = Field(
        default=True,
        description="Autónomo: facturas a empresa/AAPP con retención IRPF.",
    )
    irpf_pct: float = Field(
        default=15.0, ge=0, le=100,
        description="% retención IRPF. Nuevo autónomo puede aplicar 7% reducido (3 primeros años).",
    )

    # Datos bancarios (fuente única · fallback Settings.marcos_bank_* en transición)
    iban: Optional[str] = Field(default=None, max_length=34)
    bank_holder: Optional[str] = Field(default=None, max_length=200)
    bank_institution: Optional[str] = Field(default=None, max_length=120)
    bank_bic: Optional[str] = Field(default=None, max_length=11)


# ─────────────────────────────────────────────────────────────────
# About endpoint (read-only stats)
# Plan v4.2 sección 4.2.3 (código literal preservado)
# ─────────────────────────────────────────────────────────────────


class AdminSettingsAbout(BaseModel):
    """Stats read-only para tab About: versión + corpus + suite."""

    version: str
    commit_hash: str
    uptime_days: int
    active_clients_count: int
    corpus_sources_count: int
    corpus_sources_target: int
    corpus_chunks_total: int
    corpus_last_updated: Optional[datetime]
    corpus_completion_pct: float
    suite_passing: int
    test_loc_ratio_avg: float


# ─────────────────────────────────────────────────────────────────
# Response schema (full settings GET)
# ─────────────────────────────────────────────────────────────────


class AdminSettingsResponse(BaseModel):
    """Response completo GET /api/v1/admin/settings/."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    branding: BrandingSettings
    notifications: NotificationsSettings
    smtp: SmtpSettings
    general: GeneralSettings
    analytics_prefs: AnalyticsPrefs
    fiscal: FiscalSettings
    created_at: datetime
    updated_at: Optional[datetime]
