"""API endpoints AdminSettings panel /admin/settings.

Todos requieren autenticación + scope admin (``role=owner``) via
``require_owner`` dependency (``backend/app/auth/dependencies.py``).
Cliente NO accede.

7 endpoints (plan v4.2 tarea 4.5 + 4.12):

- ``GET    /api/v1/admin/settings``                 → AdminSettingsResponse
- ``PATCH  /api/v1/admin/settings/branding``        → AdminSettingsResponse
- ``PATCH  /api/v1/admin/settings/notifications``   → AdminSettingsResponse
- ``PATCH  /api/v1/admin/settings/smtp``            → AdminSettingsResponse
- ``PATCH  /api/v1/admin/settings/general``         → AdminSettingsResponse
- ``PATCH  /api/v1/admin/settings/analytics_prefs`` → AdminSettingsResponse
- ``PATCH  /api/v1/admin/settings/fiscal``          → AdminSettingsResponse  (#44)
- ``GET    /api/v1/admin/settings/about``           → AdminSettingsAbout

Repetición de 5 PATCH endpoints es intencional: preserva OpenAPI
type-safe doc por endpoint con su Pydantic schema correcto. Una
abstracción path-param + dispatch dinámico rompería la documentación
generada automáticamente y oscurecería el contrato API.

Audit log integration (4.A.2.d): trigger Postgres
``tg_audit_admin_settings`` (migración 8e02b4ed6004) captura cada
INSERT/UPDATE/DELETE automáticamente. Servicio
``service.update_section`` ejecuta ``set_config('app.current_user',
user.email, true)`` antes del UPDATE → trigger persiste
``audit_log.usuario`` con email Marcos. Hash chain via
``tg_audit_log_hash_chain`` heredado.

Ver plan v4.2 sección FASE 4 + sub-bloques 4.A.2.c (endpoints) +
4.A.2.d (audit_log integration).
"""
from __future__ import annotations

import logging
import subprocess
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.admin_settings import service
from backend.app.admin_settings.email_config import get_smtp_config
from backend.app.config import get_settings
from backend.app.admin_settings.storage import (
    delete_logo_by_url,
    upload_logo,
)
from backend.app.core.email.sender import EmailSender
from backend.app.core.storage.minio_client import ensure_admin_assets_bucket
from backend.app.admin_settings.schemas import (
    AdminSettingsAbout,
    AdminSettingsResponse,
    AnalyticsPrefs,
    BrandingSettings,
    FiscalSettings,
    GeneralSettings,
    NotificationsSettings,
    SmtpSettings,
)
from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db
from backend.app.models.auth import User
from backend.app.models.core import Client


logger = logging.getLogger(__name__)


router = APIRouter(prefix="/admin/settings", tags=["admin-settings"])

OwnerUser = Annotated[User, Depends(require_owner)]


def _settings_or_404(exc: service.AdminSettingsNotFoundError) -> HTTPException:
    """Mapea AdminSettingsNotFoundError de service → HTTPException 404."""
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# ─────────────────────────────────────────────────────────────────
# GET / — full singleton read
# ─────────────────────────────────────────────────────────────────


@router.get(
    "",
    response_model=AdminSettingsResponse,
    summary="GET full admin settings (singleton)",
)
async def get_admin_settings(
    user: OwnerUser,
    db: AsyncSession = Depends(get_db),
) -> AdminSettingsResponse:
    try:
        settings = await service.get_settings(db)
    except service.AdminSettingsNotFoundError as exc:
        raise _settings_or_404(exc) from exc
    return AdminSettingsResponse.model_validate(settings)


# ─────────────────────────────────────────────────────────────────
# PATCH /<section> — update atómico por categoría
# ─────────────────────────────────────────────────────────────────


@router.patch(
    "/branding",
    response_model=AdminSettingsResponse,
    summary="PATCH branding section (logo, colors, footer)",
)
async def patch_branding(
    payload: BrandingSettings,
    user: OwnerUser,
    db: AsyncSession = Depends(get_db),
) -> AdminSettingsResponse:
    try:
        settings = await service.update_section(
            db=db, section="branding", payload=payload, user=user,
        )
    except service.AdminSettingsNotFoundError as exc:
        raise _settings_or_404(exc) from exc
    return AdminSettingsResponse.model_validate(settings)


@router.post(
    "/branding/logo",
    response_model=AdminSettingsResponse,
    summary="Upload logo PNG/JPG (max 2MB) + actualiza branding.logo_url",
)
async def upload_branding_logo(
    user: OwnerUser,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> AdminSettingsResponse:
    """Upload logo brand + auto-update ``branding.logo_url``.

    - MIME types permitidos: ``image/png``, ``image/jpeg``. SVG
      explicitamente bloqueado por XSS attack vector.
    - Tamaño máximo: 2MB.
    - Bucket dedicado: ``fulkro-admin-assets`` (public read).
    - Path UUID-based para evitar cache stale post-update.
    - Cleanup automático del logo previo si existe (storage hygiene).
    - audit_log entry generado por trigger ``tg_audit_admin_settings``
      vía ``service.update_section`` (sub-bloque 4.A.2.d).
    """
    ensure_admin_assets_bucket()

    file_bytes = await file.read()
    content_type = file.content_type or "application/octet-stream"

    try:
        new_path, new_url = upload_logo(file_bytes, content_type)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    # Cleanup logo previo (best-effort, no rompe upload si falla)
    try:
        current = await service.get_settings(db)
        previous_url = (current.branding or {}).get("logo_url")
        if previous_url and previous_url != new_url:
            delete_logo_by_url(previous_url)
    except service.AdminSettingsNotFoundError:
        # Singleton missing — el update_section siguiente fallará 404
        pass
    except Exception as exc:  # noqa: BLE001
        logger.warning("Cleanup previous logo failed: %s", exc)

    # Update branding.logo_url vía service (audit_log automático)
    try:
        settings = await service.update_section(
            db=db,
            section="branding",
            payload=BrandingSettings(logo_url=new_url),
            user=user,
        )
    except service.AdminSettingsNotFoundError as exc:
        raise _settings_or_404(exc) from exc

    return AdminSettingsResponse.model_validate(settings)


@router.patch(
    "/notifications",
    response_model=AdminSettingsResponse,
    summary="PATCH notifications section (forward, magic link config)",
)
async def patch_notifications(
    payload: NotificationsSettings,
    user: OwnerUser,
    db: AsyncSession = Depends(get_db),
) -> AdminSettingsResponse:
    try:
        settings = await service.update_section(
            db=db, section="notifications", payload=payload, user=user,
        )
    except service.AdminSettingsNotFoundError as exc:
        raise _settings_or_404(exc) from exc
    return AdminSettingsResponse.model_validate(settings)


@router.patch(
    "/smtp",
    response_model=AdminSettingsResponse,
    summary="PATCH smtp section (override host/port/credentials)",
)
async def patch_smtp(
    payload: SmtpSettings,
    user: OwnerUser,
    db: AsyncSession = Depends(get_db),
) -> AdminSettingsResponse:
    try:
        settings = await service.update_section(
            db=db, section="smtp", payload=payload, user=user,
        )
    except service.AdminSettingsNotFoundError as exc:
        raise _settings_or_404(exc) from exc
    return AdminSettingsResponse.model_validate(settings)


# ─────────────────────────────────────────────────────────────────
# POST /smtp/test — envío test validando SMTP config (4.A.3.b)
# ─────────────────────────────────────────────────────────────────


class SmtpTestRequest(BaseModel):
    """Body /smtp/test (override one-shot opcional, no persiste).

    Plan v4.2 tarea 4.20 literal: solo host/port/user/password.
    from_email/from_name/use_tls SIEMPRE de Settings env (no UI).
    """

    model_config = ConfigDict(extra="forbid")

    use_admin_settings: bool = Field(default=True)
    override_host: str | None = Field(default=None, max_length=255)
    override_port: int | None = Field(default=None, ge=1, le=65535)
    override_username: str | None = Field(default=None, max_length=255)
    override_password: str | None = Field(default=None, max_length=500)


class SmtpTestResponse(BaseModel):
    ok: bool
    sent_to: str
    backend_used: str
    error: str | None = None


@router.post(
    "/smtp/test",
    response_model=SmtpTestResponse,
    summary="Envía email test a Marcos validando SMTP config",
)
async def smtp_test(
    request: SmtpTestRequest,
    user: OwnerUser,
    db: AsyncSession = Depends(get_db),
) -> SmtpTestResponse:
    """Envía email test al email admin configurado validando SMTP config.

    Modos:
    - ``use_admin_settings=True`` (default): usa AdminSettings.smtp
      custom + Settings env fallback.
    - ``use_admin_settings=False``: ignora AdminSettings.smtp, usa
      solo Settings env (test infra base).
    - ``override_*``: campos one-shot (no persisten), prioridad
      máxima sobre AdminSettings + env.

    Sólo ``host/port/username/password`` editables (plan v4.2 tarea
    4.20 literal). ``from_email/from_name/use_tls`` siempre de
    Settings env (no UI-facing).
    """
    destination = get_settings().marcos_admin_email

    override_dict: dict | None = None
    if (request.override_host or request.override_port
            or request.override_username or request.override_password):
        override_dict = {
            "host": request.override_host,
            "port": request.override_port,
            "username": request.override_username,
            "password": request.override_password,
        }

    if request.use_admin_settings or override_dict:
        smtp_config = await get_smtp_config(db, override=override_dict)
    else:
        # Settings env directo (bypass AdminSettings) — sub-caso poco
        # frecuente. Llamamos get_smtp_config con override que no es
        # None pero vacío de todas keys que filtran AdminSettings:
        # más simple = construir SmtpConfig manualmente desde Settings
        # via parse_smtp_from + fields. Hacemos esto via flag local.
        from backend.app.admin_settings.email_config import (
            SmtpConfig,
            parse_smtp_from,
        )

        s = get_settings()
        from_name, from_email = parse_smtp_from(s.smtp_from)
        smtp_config = SmtpConfig(
            host=s.smtp_host or "",
            port=s.smtp_port or 587,
            username=s.smtp_user or None,
            password=s.smtp_password.get_secret_value() or None,
            from_email=from_email,
            from_name=from_name,
            use_tls=s.smtp_use_tls,
        )

    if not smtp_config.host:
        return SmtpTestResponse(
            ok=False,
            sent_to=destination,
            backend_used="smtp",
            error=(
                "SMTP host no configurado (ni AdminSettings.smtp ni "
                "Settings env)"
            ),
        )

    sender = EmailSender(backend="smtp", smtp_config=smtp_config)

    try:
        result = await sender.send(
            db=db,
            to=destination,
            subject="FULKRO · SMTP test envío",
            html_body=(
                "<h2>Test SMTP FULKRO</h2>"
                "<p>Configuración SMTP validada correctamente.</p>"
                "<ul>"
                f"<li>Host: {smtp_config.host}</li>"
                f"<li>Port: {smtp_config.port}</li>"
                f"<li>From: {smtp_config.from_email}</li>"
                f"<li>TLS: {smtp_config.use_tls}</li>"
                "</ul>"
                f"<p><small>Sent: {datetime.now(timezone.utc).isoformat()}"
                "</small></p>"
            ),
            text_body=(
                f"FULKRO SMTP test envío. Host: {smtp_config.host}:"
                f"{smtp_config.port}"
            ),
            template_used="smtp_test",
        )

        await db.commit()

        return SmtpTestResponse(
            ok=result.ok,
            sent_to=destination,
            backend_used=result.backend_used,
            error=result.error,
        )
    except Exception as exc:  # noqa: BLE001
        return SmtpTestResponse(
            ok=False,
            sent_to=destination,
            backend_used="smtp",
            error=f"SMTP error: {exc}",
        )


@router.patch(
    "/general",
    response_model=AdminSettingsResponse,
    summary="PATCH general section (timezone, locale, date format)",
)
async def patch_general(
    payload: GeneralSettings,
    user: OwnerUser,
    db: AsyncSession = Depends(get_db),
) -> AdminSettingsResponse:
    try:
        settings = await service.update_section(
            db=db, section="general", payload=payload, user=user,
        )
    except service.AdminSettingsNotFoundError as exc:
        raise _settings_or_404(exc) from exc
    return AdminSettingsResponse.model_validate(settings)


@router.patch(
    "/analytics_prefs",
    response_model=AdminSettingsResponse,
    summary="PATCH analytics preferences",
)
async def patch_analytics_prefs(
    payload: AnalyticsPrefs,
    user: OwnerUser,
    db: AsyncSession = Depends(get_db),
) -> AdminSettingsResponse:
    try:
        settings = await service.update_section(
            db=db, section="analytics_prefs", payload=payload, user=user,
        )
    except service.AdminSettingsNotFoundError as exc:
        raise _settings_or_404(exc) from exc
    return AdminSettingsResponse.model_validate(settings)


@router.patch(
    "/fiscal",
    response_model=AdminSettingsResponse,
    summary="PATCH fiscal section (NIF, nombre fiscal, domicilio, IVA/IRPF, banco)",
)
async def patch_fiscal(
    payload: FiscalSettings,
    user: OwnerUser,
    db: AsyncSession = Depends(get_db),
) -> AdminSettingsResponse:
    """Actualiza la identidad fiscal del emisor (punto #44).

    FUENTE ÚNICA consumida por QR Verifactu, PDF de factura,
    contratos/DPA, RoPA y Facturae seller (vía
    ``core.fiscal_identity.get_fiscal_identity``). audit_log generado
    automáticamente por el trigger ``tg_audit_admin_settings``
    (``service.update_section`` setea ``app.current_user``).
    """
    try:
        settings = await service.update_section(
            db=db, section="fiscal", payload=payload, user=user,
        )
    except service.AdminSettingsNotFoundError as exc:
        raise _settings_or_404(exc) from exc
    return AdminSettingsResponse.model_validate(settings)


# ─────────────────────────────────────────────────────────────────
# GET /about — read-only stats system
# ─────────────────────────────────────────────────────────────────

# Constraints declarados (audit-first 4.A.2.c):
#
# Plan v4.2 tarea 4.12 + sección 4.2.3 asume infraestructura que
# NO existe en repo actual:
# - Tabla `rag_chunks` (corpus stats query): NO existe en BD —
#   el motor RAG/corpus aún no ha materializado la tabla.
# - `settings.APP_VERSION`: no definido en `app.config.Settings`.
# - `get_git_commit()` helper: no existe en codebase.
# - `calc_uptime()` helper: no existe.
#
# Decisión audit-first: implementar `/about` con MVP que cumple
# el schema `AdminSettingsAbout` usando stubs documentados donde
# la infra falta. Mejorable cuando rag_chunks/version/uptime
# infra exista (FASE 9 frontend v0.2 / FASE 11 corpus o sub-bloque
# dedicado). Schema respetado, contrato API estable.
# App start time tracked in-process · uptime relativo al primer import
# del módulo (suficiente granularidad para `/admin/settings/about`).
_APP_START_AT: datetime = datetime.now(timezone.utc)


def _uptime_days() -> int:
    """Días enteros desde el arranque del proceso."""
    delta = datetime.now(timezone.utc) - _APP_START_AT
    return delta.days


def _git_commit_hash() -> str:
    """Devuelve commit hash actual via subprocess git. Si falla, 'unknown'."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=2, check=True,
        )
        return result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return "unknown"


@router.get(
    "/about",
    response_model=AdminSettingsAbout,
    summary="GET read-only stats (version, corpus, suite, uptime)",
)
async def get_about(
    user: OwnerUser,
    db: AsyncSession = Depends(get_db),
) -> AdminSettingsAbout:
    """Stats sistema. Stubs donde infra plan v4.2 no existe aún."""
    # Active clients (clients table existe, query funciona)
    clients_query = select(func.count()).select_from(Client).where(
        Client.deleted_at.is_(None),
    )
    active_clients_count = await db.scalar(clients_query) or 0

    # Corpus stats REALES (FIX P4-2b · 2026-06-09): el motor corpus ya
    # materializó knowledge_documents + knowledge_chunks. Antes eran stubs a 0
    # (la tabla rag_chunks legacy no existía · se consolidó en knowledge_*).
    # Best-effort: si la query falla en algún entorno sin corpus seedeado,
    # degrada a 0 sin romper el endpoint /about.
    corpus_sources_target = 92  # plan v4.2 sección 4.2.3 · objetivo nominal
    corpus_sources_count = 0
    corpus_chunks_total = 0
    corpus_last_updated = None
    try:
        from backend.app.models.knowledge import (
            KnowledgeChunk,
            KnowledgeDocument,
        )

        corpus_sources_count = await db.scalar(
            select(func.count())
            .select_from(KnowledgeDocument)
            .where(KnowledgeDocument.deleted_at.is_(None)),
        ) or 0
        corpus_chunks_total = await db.scalar(
            select(func.count()).select_from(KnowledgeChunk),
        ) or 0
        corpus_last_updated = await db.scalar(
            select(func.max(KnowledgeDocument.created_at)),
        )
    except Exception:  # pragma: no cover · defensivo entorno sin corpus
        logger.exception("get_about corpus stats query failed · degradando a 0")

    # Suite passing: refleja realidad acotada actual (4.A.2.c).
    # No hay infra para calcular dinámicamente; valor coherente con
    # backend/tests/auth + m21_portal_cliente acotada actual = 81.
    # Cuando suite full sea ejecutable confiable, sustituir por
    # query a algún tracking real.
    suite_passing_stub = 81
    test_loc_ratio_avg_stub = 0.0  # no infra para ratio dinámico

    return AdminSettingsAbout(
        version=get_settings().app_version,
        commit_hash=_git_commit_hash(),
        uptime_days=_uptime_days(),
        active_clients_count=active_clients_count,
        corpus_sources_count=corpus_sources_count,
        corpus_sources_target=corpus_sources_target,
        corpus_chunks_total=corpus_chunks_total,
        corpus_last_updated=corpus_last_updated,
        corpus_completion_pct=round(
            min(100.0, (corpus_sources_count / corpus_sources_target) * 100), 1,
        ) if corpus_sources_target else 0.0,
        suite_passing=suite_passing_stub,
        test_loc_ratio_avg=test_loc_ratio_avg_stub,
    )


# ── FIX P4-1 · Pricing editable (fuente única) ──────────────────────────────

class PricingConfigUpdate(BaseModel):
    BASICA: float | None = None
    MEDIA: float | None = None
    ALTA: float | None = None


@router.get("/pricing")
async def get_pricing_settings(
    user: OwnerUser,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Precios base ENS editables (BASICA/MEDIA/ALTA · FIX P4-1)."""
    from backend.app.core.pricing.repository import get_pricing_config
    return await get_pricing_config(db)


@router.put("/pricing")
async def update_pricing_settings(
    payload: PricingConfigUpdate,
    user: OwnerUser,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Edita los precios base ENS · se reflejan en cotización/factura/propuesta.

    FIX P4-1 (Marcos editable). Persiste en pricing_config + refresca el override
    en memoria de este worker. Para propagar a todos los workers, reiniciar el
    backend (el valor queda persistido en BD de inmediato).
    """
    from backend.app.core.pricing.repository import (
        get_pricing_config,
        set_pricing_config,
    )
    prices = {
        k: v for k, v in {
            "BASICA": payload.BASICA,
            "MEDIA": payload.MEDIA,
            "ALTA": payload.ALTA,
        }.items() if v is not None
    }
    if not prices:
        raise HTTPException(status_code=400, detail="Sin precios para actualizar")
    await set_pricing_config(db, prices, updated_by=user.email)
    await db.commit()
    return await get_pricing_config(db)
