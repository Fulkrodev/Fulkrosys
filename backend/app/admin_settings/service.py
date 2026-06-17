"""Service layer AdminSettings panel /admin/settings.

Helpers expuestos:

- ``get_settings(db)``: query singleton row.
- ``update_section(db, section, payload, user_id)``: UPDATE atómico
  por categoría con merge ``exclude_unset``.
- ``ensure_seeded(db)``: idempotente, defensive layer.

Decisiones arquitectónicas:

- PATCH atómico por categoría (no endpoint "PATCH all"). Cada
  endpoint toca solo una columna JSONB, audit_log entry granular.
- Pydantic schemas validan en endpoint (FastAPI auto). Service
  recibe instance ya validada; verificación ``isinstance`` redundante
  como defensa-en-profundidad.
- ``exclude_unset=True`` permite parciales DENTRO de una categoría
  (ej: PATCH branding con solo ``primary_color`` preserva
  ``logo_url`` previo).
- Service raises ``AdminSettingsNotFoundError`` (custom domain
  exception). Endpoint layer mapea a HTTPException 404. Coherente
  con pattern ``AuthError`` de m21_portal_cliente.
- ``ensure_seeded`` NO sustituye la migración Alembic 506c7a897689.
  Es defensive layer extra (BD pre-migrate, race condition raro).

NOTE 4.A.2.d: integración audit_log hash-chained pendiente.
``update_section`` ya recibe ``user_id`` en signature; persistencia
del entry concreto se añade en sub-bloque 4.A.2.d.

Ver plan v4.2 sección FASE 4 + sub-bloque 4.A.2.b.
"""
from __future__ import annotations

import logging
from typing import Literal, Type

from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from backend.app.admin_settings.schemas import (
    AnalyticsPrefs,
    BrandingSettings,
    FiscalSettings,
    GeneralSettings,
    NotificationsSettings,
    SmtpSettings,
)
from backend.app.models.admin import ADMIN_SETTINGS_ID, AdminSettings
from backend.app.models.auth import User


SectionName = Literal[
    "branding",
    "notifications",
    "smtp",
    "general",
    "analytics_prefs",
    "fiscal",
]


SECTION_SCHEMAS: dict[SectionName, Type[BaseModel]] = {
    "branding": BrandingSettings,
    "notifications": NotificationsSettings,
    "smtp": SmtpSettings,
    "general": GeneralSettings,
    "analytics_prefs": AnalyticsPrefs,
    "fiscal": FiscalSettings,
}


class AdminSettingsNotFoundError(Exception):
    """Singleton row missing — seed default no aplicado.

    Endpoint layer mapea a HTTPException 404. Caso esperado solo
    si la migración Alembic 506c7a897689 no se aplicó (BD nueva
    sin upgrade head, o race condition extraordinaria).
    """


async def get_settings(db: AsyncSession) -> AdminSettings:
    """Query singleton row admin_settings.

    Raises:
        AdminSettingsNotFoundError: si singleton id no existe.
    """
    result = await db.execute(
        select(AdminSettings).where(AdminSettings.id == ADMIN_SETTINGS_ID)
    )
    settings = result.scalar_one_or_none()
    if settings is None:
        raise AdminSettingsNotFoundError(
            "AdminSettings singleton row missing. Verificar migración "
            "Alembic 506c7a897689 (alembic upgrade head)."
        )
    return settings


async def ensure_seeded(db: AsyncSession) -> AdminSettings:
    """Idempotente: garantiza singleton row exists.

    Defensive layer: si seed default falló o BD se creó sin aplicar
    la migración data-aware, esto crea la fila. NO sustituye la
    migración 506c7a897689 — es backup de último recurso.

    Returns:
        AdminSettings (creada o existente).
    """
    try:
        return await get_settings(db)
    except AdminSettingsNotFoundError:
        settings = AdminSettings(id=ADMIN_SETTINGS_ID)
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
        return settings


async def update_section(
    db: AsyncSession,
    section: SectionName,
    payload: BaseModel,
    user: User,
) -> AdminSettings:
    """Update atómico de una categoría JSONB con merge parcial.

    audit_log entry generado automáticamente por trigger
    ``tg_audit_admin_settings`` (sub-bloque 4.A.2.d). Antes del
    UPDATE ejecutamos ``set_config('app.current_user', user.email, true)``
    para que el trigger ``fn_audit_track`` capture el usuario que
    hace el cambio. Hash chain via trigger separado
    ``tg_audit_log_hash_chain`` (heredado, inmutabilidad enforced).

    El uso de ``set_config()`` (función) en lugar de ``SET LOCAL``
    es intencional: asyncpg no soporta bind parameters con SET LOCAL
    pero sí con set_config. Pattern documentado en
    ``backend/app/database.py::set_tenant_context``.

    Args:
        db: AsyncSession activa.
        section: una de SECTION_SCHEMAS keys.
        payload: Pydantic schema instance ya validada por endpoint.
        user: User autenticado que ejecuta el cambio. ``user.email``
              persistido en ``audit_log.usuario`` via trigger.

    Returns:
        AdminSettings tras UPDATE (refresh aplicado).

    Raises:
        AdminSettingsNotFoundError: singleton missing.
        ValueError: payload schema mismatch con section (defensa
                    redundante, FastAPI ya valida en endpoint).
    """
    expected_schema = SECTION_SCHEMAS[section]
    if not isinstance(payload, expected_schema):
        raise ValueError(
            f"Payload {type(payload).__name__} no coincide con schema "
            f"esperado {expected_schema.__name__} para section "
            f"'{section}'."
        )

    settings = await get_settings(db)

    # exclude_unset=True permite PATCH parcial dentro de categoría:
    # un cliente que solo manda primary_color preserva logo_url
    # previo en BD. Sin exclude_unset, los defaults del schema
    # sobrescribirían fields no enviados.
    new_data = payload.model_dump(exclude_unset=True)

    # Merge con valor actual (preserva fields no enviados)
    current = getattr(settings, section) or {}
    merged = {**current, **new_data}

    # S24 (campaña auditoría): el password SMTP NO se almacena en claro. Se cifra
    # con Fernet (clave derivada de app_secret_key · reuse token_encryption) y se
    # marca con prefijo enc:v1: para que el lector (email_config) sepa descifrarlo.
    # Sólo se (re)cifra si llega un password nuevo en plano (no re-cifrar lo ya cifrado).
    if section == "smtp" and merged.get("password"):
        pwd = str(merged["password"])
        if not pwd.startswith("enc:v1:"):
            try:
                from backend.app.motors.m16_onboarding.token_encryption import (
                    encrypt_str,
                )
                merged["password"] = "enc:v1:" + encrypt_str(pwd)
            except Exception:  # noqa: BLE001
                # Sin app_secret_key utilizable no se persiste el secreto en claro.
                logger.warning("SMTP password no cifrable · se descarta del guardado")
                merged.pop("password", None)

    # set_config(..., true) → scope local-to-transaction. El trigger
    # tg_audit_admin_settings (fn_audit_track) lee este setting al
    # disparar AFTER UPDATE y lo persiste como audit_log.usuario.
    # UPDATE + audit_log entry en MISMA transaction = atomicidad ENS.
    await db.execute(
        text("SELECT set_config('app.current_user', :usr, true)"),
        {"usr": user.email},
    )

    setattr(settings, section, merged)

    await db.commit()
    await db.refresh(settings)

    return settings
