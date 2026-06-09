"""AdminSettings — configuración mutable runtime panel /admin/settings.

Distinción crítica con `app.config.Settings`:

- `Settings` (`config.py`): env-based, immutable runtime, carga desde
  `.env` + variables de entorno. Contiene database_url, anthropic_api_key,
  smtp_host (defaults), etc.
- `AdminSettings` (este model, BD-based): mutable runtime via PATCH
  endpoints en `/api/v1/admin/settings/*`. Trazabilidad ENS via
  `audit_log` integration (cada PATCH genera entry hash-chained).

Tabla singleton:

- 1 sola fila con `id = ADMIN_SETTINGS_ID` (UUID fija constante).
- `CheckConstraint` BD-level enforce singleton — INSERT con otro UUID
  fallaría a nivel de constraint.
- Seed default insertado en migración Alembic (server_defaults populan
  todas las JSONB con `'{}'::jsonb`).
- Nunca DELETE — solo UPDATE via service layer.

Decisión arquitectónica audit-first (sub-bloque 4.A.1):

Plan v4.2 sugería literal `id Integer = 1`. Audit pre-implementación
reveló que `audit_log.registro_id` es UUID NOT NULL (cross-motor
contract existente desde S1-S2). Si AdminSettings tuviera Integer pk,
la integración con audit_log de tarea 4.14 requeriría refactor del
audit_log model afectando todos los motors que ya lo usan. UUID fija
constante preserva la semántica singleton del plan + cumple el contrato
existente sin scope creep.

Categorías JSONB:
- `branding`: logo, colors override, footer text
- `notifications`: email forward, magic link config v4
  (`magic_link_default_sender`, `magic_link_per_purpose_overrides`)
- `smtp`: override del SMTP env-based de Settings (host/port/user/password)
- `general`: timezone, idioma, formato fecha
- `analytics_prefs`: `show_corpus_metric` bool, etc.

Validación de shape de cada JSONB se hace en service layer vía Pydantic
schemas (sub-bloque 4.A.2). El BD acepta cualquier dict; el contrato lo
imponen los endpoints PATCH.

Defensa doble defaults:
- Python-side `default=dict`: ORM-level — `AdminSettings()` sin args produce dicts vacíos.
- BD-side `server_default=text("'{}'::jsonb")`: SQL-level — INSERT directo
  via `op.execute()` también queda válido sin tocar JSONB columns.

Ver plan v4.2 sección FASE 4 + sub-bloque 4.A.1.
"""
from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import text

from backend.app.models.base import Base, TimestampMixin


ADMIN_SETTINGS_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
"""UUID singleton constante para `AdminSettings`.

Service layer query: ``select(AdminSettings).where(AdminSettings.id == ADMIN_SETTINGS_ID)``.
"""


class AdminSettings(Base, TimestampMixin):
    """Configuración runtime singleton mutable via panel /admin/settings."""

    __tablename__ = "admin_settings"
    __table_args__ = (
        CheckConstraint(
            f"id = '{ADMIN_SETTINGS_ID}'::uuid",
            name="admin_settings_singleton",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
    )

    branding: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    notifications: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    smtp: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    general: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    analytics_prefs: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    # Punto #44 (OLA 0) · identidad fiscal del emisor/consultor como
    # FUENTE ÚNICA: nif, nombre_fiscal, nombre_comercial, tipo_persona
    # (F autónomo / J sociedad), domicilio fiscal estructurado, iva/irpf,
    # datos bancarios. Editable vía /admin/settings/fiscal + auditado por
    # el trigger tg_audit_admin_settings (a nivel tabla, dispara también
    # en esta columna). Consumido vía core.fiscal_identity.get_fiscal_identity.
    fiscal: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
