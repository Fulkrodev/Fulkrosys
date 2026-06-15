"""Auth API — login (password+MFA), WebAuthn, TOTP, sessions.

Six public flows per FULKRO spec:
- POST /auth/login
- POST /auth/webauthn/verify
- POST /auth/totp/verify
- POST /auth/logout
- GET  /auth/me
- POST /auth/webauthn/register[/begin|/complete]

Plus helpers:
- POST /auth/totp/setup, /auth/totp/confirm — onboard the TOTP fallback.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import jwt as pyjwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth import crypto, rate_limit, service, totp_svc, webauthn_svc
from backend.app.auth.dependencies import (
    CSRF_COOKIE,
    SESSION_COOKIE,
    CurrentUser,
)
from backend.app.auth.schemas import (
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    MeResponse,
    TOTPVerifyRequest,
    WebAuthnRegisterBeginRequest,
    WebAuthnRegisterBeginResponse,
    WebAuthnRegisterCompleteRequest,
    WebAuthnVerifyRequest,
)
from backend.app.config import get_settings
from backend.app.database import get_db


router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])
_settings = get_settings()


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────

def _ip(request: Request) -> str | None:
    if request.client is None:
        return None
    return request.client.host


def _ua(request: Request) -> str | None:
    return request.headers.get("user-agent")


def _set_auth_cookies(
    response: Response,
    *,
    session_token: str,
    csrf_token: str,
    expires_at: datetime,
) -> None:
    max_age = int((expires_at - datetime.now(timezone.utc)).total_seconds())
    if max_age < 0:
        max_age = 0
    # ``secure`` requires HTTPS. Relaxed in dev/test so the cookies can travel
    # over ``http://localhost`` during development and ``http://test`` in tests.
    secure_cookies = _settings.is_production
    response.set_cookie(
        key=SESSION_COOKIE,
        value=session_token,
        max_age=max_age,
        httponly=True,
        secure=secure_cookies,
        samesite="strict",
        path="/",
    )
    response.set_cookie(
        key=CSRF_COOKIE,
        value=csrf_token,
        max_age=max_age,
        httponly=False,
        secure=secure_cookies,
        samesite="strict",
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    for key in (SESSION_COOKIE, CSRF_COOKIE):
        response.delete_cookie(key=key, path="/", samesite="strict")


async def _decode_ticket(token: str, expected_typ: str) -> dict:
    try:
        payload = crypto.decode_token(token)
    except pyjwt.InvalidTokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid ticket") from exc
    if payload.get("typ") != expected_typ:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "wrong ticket type")
    return payload


# ──────────────────────────────────────────────────────────────────────
# POST /auth/login — password step
# ──────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)
) -> LoginResponse:
    ip = _ip(request)
    ua = _ua(request)

    if await rate_limit.ip_is_rate_limited(db, ip_address=ip):
        await rate_limit.record_attempt(
            db, email=body.email, ip_address=ip, user_agent=ua,
            success=False, reason="rate_limited",
        )
        await db.commit()  # persist rate-limit attempt before raising
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "too many attempts; try again later",
        )

    user = await service.get_user_by_email(db, body.email)

    if user is None:
        await rate_limit.record_attempt(
            db, email=body.email, ip_address=ip, user_agent=ua,
            success=False, reason="unknown_email",
        )
        await db.commit()  # persist unknown-email attempt before raising
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials")

    if not user.is_active:
        await rate_limit.record_attempt(
            db, email=body.email, ip_address=ip, user_agent=ua,
            success=False, reason="inactive",
        )
        await db.commit()  # persist inactive attempt before raising
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "account inactive")

    if service.user_is_locked(user):
        await rate_limit.record_attempt(
            db, email=body.email, ip_address=ip, user_agent=ua,
            success=False, reason="user_locked",
        )
        await db.commit()  # persist locked attempt before raising
        raise HTTPException(status.HTTP_423_LOCKED, "account temporarily locked")

    if not crypto.verify_password(body.password, user.password_hash):
        await service.register_failed_attempt(db, user)
        await rate_limit.record_attempt(
            db, email=body.email, ip_address=ip, user_agent=ua,
            success=False, reason="bad_password",
        )
        await db.commit()  # persist failed attempt + lockout counter before raising
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials")

    user.failed_login_attempts = 0
    await db.flush()

    await rate_limit.record_attempt(
        db, email=body.email, ip_address=ip, user_agent=ua,
        success=True, reason="password_ok",
    )

    creds = await service.get_webauthn_credentials(db, user.id)
    totp = await service.get_totp_secret(db, user.id)
    totp_available = totp is not None and totp.verified
    webauthn_available = len(creds) > 0

    webauthn_options: dict | None = None
    webauthn_state: dict | None = None
    if webauthn_available:
        webauthn_options, webauthn_state = webauthn_svc.begin_authentication(
            service.stored_credentials(creds)
        )

    ticket = _bind_ticket_state(str(user.id), webauthn_state, "mfa_ticket")

    await db.commit()  # persist failed_login_attempts reset + password_ok attempt
    return LoginResponse(
        mfa_ticket=ticket,
        webauthn=webauthn_options,
        totp_available=totp_available,
        webauthn_available=webauthn_available,
    )


def _bind_ticket_state(user_id: str, state: dict | None, typ: str) -> str:
    """Issue a JWT ticket whose ``state`` claim holds the WebAuthn state."""
    from backend.app.auth.crypto import (
        JWT_ALGORITHM,
        MFA_TICKET_TTL,
        REGISTRATION_TICKET_TTL,
        _PRIVATE_PEM,
    )

    ttl = {
        "mfa_ticket": MFA_TICKET_TTL,
        "registration_ticket": REGISTRATION_TICKET_TTL,
    }[typ]
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "jti": uuid.uuid4().hex,
        "typ": typ,
        "iat": int(now.timestamp()),
        "exp": int((now + ttl).timestamp()),
    }
    if state:
        payload["state"] = state
    return pyjwt.encode(payload, _PRIVATE_PEM, algorithm=JWT_ALGORITHM)


# ──────────────────────────────────────────────────────────────────────
# POST /auth/webauthn/verify — complete MFA with Yubikey/passkey
# ──────────────────────────────────────────────────────────────────────

@router.post("/webauthn/verify")
async def webauthn_verify(
    body: WebAuthnVerifyRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    payload = await _decode_ticket(body.mfa_ticket, "mfa_ticket")
    user_id = uuid.UUID(payload["sub"])
    state = payload.get("state")
    if not state:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "ticket has no webauthn state")

    user = await service.get_user(db, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "user not found")

    creds = await service.get_webauthn_credentials(db, user.id)
    if not creds:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "no webauthn credentials")

    try:
        credential = webauthn_svc.complete_authentication(
            state=state,
            existing=service.stored_credentials(creds),
            credential_id=webauthn_svc.b64url_decode(body.credential_id),
            client_data_json=webauthn_svc.b64url_decode(body.client_data_json),
            authenticator_data=webauthn_svc.b64url_decode(body.authenticator_data),
            signature=webauthn_svc.b64url_decode(body.signature),
        )
    except Exception as exc:  # fido2 raises various low-level errors
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "webauthn verification failed") from exc

    # Refresh sign count in DB
    stored = next(c for c in creds if c.credential_id == credential.credential_id)
    await service.bump_sign_count(db, stored, sign_count=credential.sign_count)
    await service.register_successful_login(db, user)

    token, csrf, expires_at, _ = await service.create_session(
        db, user=user, ip_address=_ip(request), user_agent=_ua(request)
    )
    _set_auth_cookies(response, session_token=token, csrf_token=csrf, expires_at=expires_at)
    await rate_limit.record_attempt(
        db, email=user.email, ip_address=_ip(request), user_agent=_ua(request),
        success=True, reason="webauthn_ok",
    )
    await db.commit()  # persist sign-count, successful login, session, attempt
    return {"csrf_token": csrf, "expires_at": expires_at.isoformat()}


# ──────────────────────────────────────────────────────────────────────
# POST /auth/totp/verify — fallback MFA
# ──────────────────────────────────────────────────────────────────────

@router.post("/totp/verify")
async def totp_verify(
    body: TOTPVerifyRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    payload = await _decode_ticket(body.mfa_ticket, "mfa_ticket")
    user_id = uuid.UUID(payload["sub"])

    user = await service.get_user(db, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "user not found")

    # §1.8 audit-2026-06-15 · el paso TOTP carecía de rate-limit IP y de lockout de
    # cuenta (sólo registraba el intento) → con un mfa_ticket válido (5 min) se podían
    # adivinar códigos sin tope por cuenta. Mismo control que /login.
    if await rate_limit.ip_is_rate_limited(db, ip_address=_ip(request)):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS, "too many attempts; try again later",
        )
    if service.user_is_locked(user):
        raise HTTPException(status.HTTP_423_LOCKED, "account temporarily locked")

    totp = await service.get_totp_secret(db, user.id)
    if totp is None or not totp.verified:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "totp not enrolled")

    if not totp_svc.verify_code(totp.secret, body.code):
        await service.register_failed_attempt(db, user)  # §1.8 · lockout por cuenta
        await rate_limit.record_attempt(
            db, email=user.email, ip_address=_ip(request), user_agent=_ua(request),
            success=False, reason="bad_totp",
        )
        await db.commit()  # persist bad-totp attempt + lockout counter before raising
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid code")

    await service.register_successful_login(db, user)
    token, csrf, expires_at, _ = await service.create_session(
        db, user=user, ip_address=_ip(request), user_agent=_ua(request)
    )
    _set_auth_cookies(response, session_token=token, csrf_token=csrf, expires_at=expires_at)
    await rate_limit.record_attempt(
        db, email=user.email, ip_address=_ip(request), user_agent=_ua(request),
        success=True, reason="totp_ok",
    )
    await db.commit()  # persist successful login, session, attempt
    return {"csrf_token": csrf, "expires_at": expires_at.isoformat()}


# ──────────────────────────────────────────────────────────────────────
# POST /auth/logout
# ──────────────────────────────────────────────────────────────────────

@router.post("/logout", response_model=LogoutResponse)
async def logout(
    request: Request,
    response: Response,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> LogoutResponse:
    payload = request.state.auth_payload
    jti = payload.get("jti")
    revoked = await service.revoke_session(db, jti) if jti else False
    _clear_auth_cookies(response)
    await db.commit()  # persist session revocation
    return LogoutResponse(revoked=revoked)


# ──────────────────────────────────────────────────────────────────────
# GET /auth/me
# ──────────────────────────────────────────────────────────────────────

@router.get("/me", response_model=MeResponse)
async def me(user: CurrentUser, db: AsyncSession = Depends(get_db)) -> MeResponse:
    creds = await service.get_webauthn_credentials(db, user.id)
    totp = await service.get_totp_secret(db, user.id)
    return MeResponse(
        id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        must_change_password=user.must_change_password,
        webauthn_credentials=len(creds),
        totp_enabled=bool(totp and totp.verified),
        role=user.role,
        is_owner=user.role == "owner",
    )


# ──────────────────────────────────────────────────────────────────────
# POST /auth/webauthn/register/{begin,complete}
# ──────────────────────────────────────────────────────────────────────

@router.post("/webauthn/register/begin", response_model=WebAuthnRegisterBeginResponse)
async def webauthn_register_begin(
    body: WebAuthnRegisterBeginRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> WebAuthnRegisterBeginResponse:
    creds = await service.get_webauthn_credentials(db, user.id)
    options, state = webauthn_svc.begin_registration(
        user_id=user.id.bytes,
        user_name=user.email,
        display_name=user.display_name or user.email,
        existing=service.stored_credentials(creds),
    )
    ticket = _bind_ticket_state(str(user.id), state, "registration_ticket")
    return WebAuthnRegisterBeginResponse(registration_ticket=ticket, options=options)


@router.post("/webauthn/register/complete")
async def webauthn_register_complete(
    body: WebAuthnRegisterCompleteRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    payload = await _decode_ticket(body.registration_ticket, "registration_ticket")
    if payload.get("sub") != str(user.id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "ticket subject mismatch")
    state = payload.get("state")
    if not state:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "ticket has no state")

    try:
        credential_data = webauthn_svc.complete_registration(
            state=state,
            client_data_json=webauthn_svc.b64url_decode(body.client_data_json),
            attestation_object=webauthn_svc.b64url_decode(body.attestation_object),
        )
    except Exception as exc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "webauthn registration failed"
        ) from exc

    cred = await service.upsert_webauthn_credential(
        db,
        user_id=user.id,
        credential_id=bytes(credential_data.credential_id),
        public_key=bytes(credential_data.public_key),
        device_name=body.device_name,
    )
    await db.commit()  # persist new webauthn credential
    return {
        "id": str(cred.id),
        "credential_id": webauthn_svc.b64url_encode(cred.credential_id),
        "device_name": cred.device_name,
    }


# ──────────────────────────────────────────────────────────────────────
# POST /auth/totp/setup, /auth/totp/confirm (helpers)
# ──────────────────────────────────────────────────────────────────────

class _TOTPSetupResponse(BaseModel):
    secret: str
    provisioning_uri: str


class _TOTPConfirmRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6)


@router.post("/totp/setup", response_model=_TOTPSetupResponse)
async def totp_setup(
    user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> _TOTPSetupResponse:
    existing = await service.get_totp_secret(db, user.id)
    if existing and existing.verified:
        raise HTTPException(status.HTTP_409_CONFLICT, "totp already enrolled")

    secret = totp_svc.generate_secret()
    if existing:
        existing.secret = secret
        existing.verified = False
    else:
        from backend.app.models.auth import TOTPSecret

        db.add(TOTPSecret(user_id=user.id, secret=secret, verified=False))
    await db.flush()
    await db.commit()  # persist TOTPSecret (new or updated)
    return _TOTPSetupResponse(
        secret=secret,
        provisioning_uri=totp_svc.provisioning_uri(secret, user.email),
    )


@router.post("/totp/confirm")
async def totp_confirm(
    body: _TOTPConfirmRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    totp = await service.get_totp_secret(db, user.id)
    if totp is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "no pending totp setup")
    if not totp_svc.verify_code(totp.secret, body.code):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid code")
    totp.verified = True
    await db.flush()
    await db.commit()  # persist verified=True flag
    return {"totp_enabled": True}


# ════════════════════════════════════════════════════════════════════
# SAN-B.MB-7.4 · Public key Ed25519 + verify-signature
# Endpoints sin auth · WHITELIST_EXACT (ADR-030 criterio 4 · catálogo
# público read-only para auditor externo verificar firmas FULKRO).
# ════════════════════════════════════════════════════════════════════

class _PublicKeyResponse(BaseModel):
    algorithm: str = "ed25519"
    format: str = "PEM"
    public_key: str = Field(..., description="Ed25519 public key PEM-encoded")
    key_id: str = Field(..., description="Stable identifier de la key actual")


class _VerifySignatureRequest(BaseModel):
    payload_b64: str = Field(..., description="Base64-encoded original payload bytes")
    signature_b64: str = Field(..., description="Base64-encoded signature (Ed25519)")


class _VerifySignatureResponse(BaseModel):
    valid: bool


@router.get("/public-key", response_model=_PublicKeyResponse)
async def get_public_key():
    """Devuelve clave pública Ed25519 FULKRO en formato PEM.

    Sin auth · permite auditor externo verificar firmas (artefactos M07
    evidence · M25 archive ZIP · backups M26) sin acceso al sistema.

    key_id es hash SHA256 truncado de la public_pem · estable mientras
    misma key activa · cambia al rotar (futuro KMS rotation).

    SAN-B.MB-7.4 · cierre TODO-AUTH-KEY-ENDPOINT-001 (backend).
    """
    import hashlib

    public_pem_str = crypto._PUBLIC_PEM.decode("utf-8")
    key_id = hashlib.sha256(crypto._PUBLIC_PEM).hexdigest()[:16]
    return _PublicKeyResponse(
        algorithm="ed25519",
        format="PEM",
        public_key=public_pem_str,
        key_id=key_id,
    )


@router.post("/verify-signature", response_model=_VerifySignatureResponse)
async def verify_signature(body: _VerifySignatureRequest):
    """Verifica payload+signature contra clave pública FULKRO.

    Útil para auditor externo automatizar verificación dossier sin
    instalar dependencias cripto (FULKRO actúa como oracle).

    Inputs base64-encoded para tolerar binary payloads via JSON.
    Returns {"valid": true|false}. Si signature/payload malformados
    base64, returns {"valid": false} (no crash).

    SAN-B.MB-7.4 · cierre TODO-AUTH-KEY-ENDPOINT-001 (backend).
    """
    import base64

    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import serialization

    try:
        payload = base64.b64decode(body.payload_b64, validate=True)
        signature = base64.b64decode(body.signature_b64, validate=True)
    except (ValueError, base64.binascii.Error):
        return _VerifySignatureResponse(valid=False)

    public_key = serialization.load_pem_public_key(crypto._PUBLIC_PEM)
    try:
        public_key.verify(signature, payload)
        return _VerifySignatureResponse(valid=True)
    except InvalidSignature:
        # Sólo una firma inválida devuelve valid=False. Cualquier otro error
        # (clave corrupta, payload mal codificado) DEBE propagarse para no
        # enmascarar bugs como "firma inválida".
        return _VerifySignatureResponse(valid=False)
