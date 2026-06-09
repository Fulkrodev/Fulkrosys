"""CLUSTER 6 Phase 6A · MFA TOTP cliente API endpoints.

Routes mounted under ``/client-portal/settings/mfa/*`` · all require
``get_current_client_user`` (ADR-013 doble pool · cliente only).

Endpoints:
- GET    /status      · estado MFA cliente (enrolled · verified · backup count)
- POST   /initiate    · genera secret + otpauth_uri (UI renders QR SVG inline)
- POST   /confirm     · verifica primer TOTP + genera 10 backup codes (DISPLAYED ONCE)
- POST   /disable     · requiere current TOTP · borra MFA + backup codes
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.models.client_portal import ClientUser
from backend.app.motors.m21_portal_cliente import mfa_service
from backend.app.motors.m21_portal_cliente.api import get_current_client_user

logger = logging.getLogger(__name__)

mfa_router = APIRouter(
    prefix="/client-portal/settings/mfa",
    tags=["Portal Cliente MFA"],
)


class InitiateResponse(BaseModel):
    secret: str
    otpauth_uri: str


class ConfirmBody(BaseModel):
    code: str = Field(..., min_length=6, max_length=10)


class ConfirmResponse(BaseModel):
    backup_codes: list[str]


class DisableBody(BaseModel):
    # method='email' no requiere código (sesión autenticada basta) · method='totp'
    # legacy sí. Opcional para soportar ambos.
    code: str | None = Field(None, max_length=10)


class EmailConfirmBody(BaseModel):
    code: str = Field(..., min_length=4, max_length=8)


class StatusResponse(BaseModel):
    method: str = "email"
    mfa_enabled: bool
    enrolled: bool
    verified: bool
    email: str | None = None
    backup_codes_remaining: int
    last_used_at: str | None


@mfa_router.get("/status", response_model=StatusResponse)
async def get_mfa_status(
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> StatusResponse:
    s = await mfa_service.status(db, user)
    return StatusResponse(**s)


@mfa_router.post("/initiate", response_model=InitiateResponse)
async def initiate_mfa(
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> InitiateResponse:
    try:
        result = await mfa_service.initiate(db, user)
        await db.commit()
    except mfa_service.MfaError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc),
        )
    return InitiateResponse(
        secret=result.secret, otpauth_uri=result.otpauth_uri,
    )


@mfa_router.post("/confirm", response_model=ConfirmResponse)
async def confirm_mfa(
    body: ConfirmBody,
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> ConfirmResponse:
    try:
        result = await mfa_service.confirm(db, user, body.code)
        await db.commit()
    except mfa_service.MfaError as exc:
        await db.commit()  # persist audit emit even on failure
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc),
        )

    # Best-effort email reminder · cliente debería anotar codes
    try:
        from backend.app.core.email.sender import get_email_sender
        sender = get_email_sender()
        html = _render_mfa_enrolled_email(user.full_name or user.email)
        await sender.send(
            db,
            to=user.email,
            subject="Verificación en 2 pasos activada",
            html_body=html,
            template_used="mfa_enrolled",
            client_id=user.client_id,
        )
        await db.commit()
    except Exception:
        logger.warning("MFA enrollment email failed · ignored")

    return ConfirmResponse(backup_codes=result.backup_codes)


# ── MFA por CÓDIGO AL EMAIL (2026-06-09 · sustituye TOTP para el cliente) ──

@mfa_router.post("/email/start", status_code=status.HTTP_204_NO_CONTENT)
async def email_start(
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Envía un código al email del cliente para ACTIVAR la verificación en 2
    pasos (enrollment paso 1). El cliente lo confirma en ``/email/confirm``."""
    await mfa_service.issue_email_code(db, user)
    await db.commit()


@mfa_router.post("/email/confirm", response_model=StatusResponse)
async def email_confirm(
    body: EmailConfirmBody,
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> StatusResponse:
    """Confirma el código recibido por email y activa MFA (method='email')."""
    ok = await mfa_service.confirm_email_enrollment(db, user, body.code)
    await db.commit()
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código inválido o caducado · pide uno nuevo",
        )
    return StatusResponse(**(await mfa_service.status(db, user)))


@mfa_router.post("/disable", status_code=status.HTTP_204_NO_CONTENT)
async def disable_mfa(
    body: DisableBody,
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    try:
        await mfa_service.disable(db, user, body.code or "")
        await db.commit()
    except mfa_service.MfaError as exc:
        await db.commit()  # persist audit emit even on failure
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc),
        )


def _render_mfa_enrolled_email(name: str) -> str:
    """R29 friendly email confirmation post-MFA enrollment.

    NO admin lingo · NO presión · congrats tone · acción clara.
    """
    safe_name = name.replace("<", "&lt;").replace(">", "&gt;")
    return f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 540px; margin: 0 auto; color: #1f2937;">
      <h2 style="color: #15803d;">Verificación en 2 pasos activada ✓</h2>
      <p>Hola {safe_name},</p>
      <p>Has activado la verificación en 2 pasos en tu cuenta. A partir de
      ahora · cuando entres al portal te pediremos un código de tu app
      autenticadora.</p>
      <h3 style="margin-top: 24px;">Códigos de respaldo</h3>
      <p>Apunta los 10 códigos que te mostramos en pantalla. Cada uno sirve
      una sola vez · te permitirán entrar si pierdes el teléfono.</p>
      <p style="background: #f3f4f6; padding: 12px; border-radius: 8px;">
        <strong>Consejo</strong> · guárdalos en tu gestor de contraseñas o
        imprime una copia. Sin prisa por tu parte.
      </p>
      <p>Si no has sido tú · responde a este correo y lo arreglamos.</p>
      <p style="color: #6b7280; font-size: 14px; margin-top: 32px;">FULKRO ENS</p>
    </div>
    """.strip()
