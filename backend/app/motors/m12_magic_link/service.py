"""Motor 12 — Magic Link Engine: Service layer.

Implements cryptographic magic link generation, consumption, and revocation
for FULKRO's client interaction system. Clients receive time-limited,
cryptographically signed URLs for specific operations (signing documents,
uploading evidence, authorizing pentests, etc.) without needing accounts.

Security model:
- JWT signed with Ed25519 (EdDSA) — spec v2.1 Motor 12
- Token NEVER stored in DB; only SHA-256 hash (token_hash column)
- OTP (6-digit TOTP) sent via separate channel when purpose requires it
- OTP hash stored, never plaintext
- Rate limiting: 3 OTP failures → link permanently invalidated
- Geo-restriction: allowed_countries JSONB (prepared, not enforced yet)
- Audit trail: every action logged to client_interactions (append-only)

References:
- Spec v2.1, Section 5.1 Motor 12 — Magic Link Engine
- 9 purpose types defined in purposes.py
"""
import hashlib
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt as pyjwt
import pyotp
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.operations import MagicLink, ClientInteraction
from backend.app.motors.m12_magic_link.purposes import (
    MagicLinkPurpose,
    get_config,
)
from backend.app.motors.m12_magic_link.schemas import (
    MagicLinkGenerateRequest,
    MagicLinkGenerateResponse,
    MagicLinkConsumeRequest,
    MagicLinkConsumeResponse,
)


# ================================================================
# CONSTANTS
# ================================================================

JWT_ALGORITHM = "EdDSA"
OTP_FAILURE_THRESHOLD = 3
OTP_DIGITS = 6
# §1.5: expiración propia del OTP, corta e independiente del TTL del link
# (que puede llegar a 120 días). Reduce la ventana de fuerza bruta del OTP.
OTP_TTL_MINUTES = 15


# ================================================================
# KEY MANAGEMENT
# ================================================================

def _load_signing_keys() -> tuple[bytes, bytes]:
    """Load Ed25519 key pair from env or generate ephemeral for development.

    Returns (private_key_pem, public_key_pem) as bytes.

    In production, FULKRO_ML_PRIVATE_KEY env var must contain the PEM-encoded
    Ed25519 private key. In development, generates an ephemeral pair with a
    WARNING log — tokens signed with ephemeral keys become invalid on restart.
    """
    env_key = os.environ.get("FULKRO_ML_PRIVATE_KEY")
    if env_key:  # pragma: no cover — production path, env var not set in tests
        private_pem = env_key.encode() if isinstance(env_key, str) else env_key
        private_key = serialization.load_pem_private_key(private_pem, password=None)
        public_pem = private_key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        logger.info("Magic Link: Ed25519 key loaded from FULKRO_ML_PRIVATE_KEY")
        return private_pem, public_pem

    from backend.app.core.signing_keys import is_production

    if is_production():
        raise RuntimeError(
            "FULKRO_ML_PRIVATE_KEY no definido en producción. Debe inyectarse la "
            "clave Ed25519 (PEM): sin ella los magic links se invalidarían en cada "
            "reinicio. NUNCA se autogenera en producción (fail-fast)."
        )

    # Development fallback: ephemeral key
    logger.warning(
        "Magic Link: FULKRO_ML_PRIVATE_KEY not set. Generating ephemeral Ed25519 key "
        "(dev/test only). Tokens will be invalid after restart."
    )
    private_key = Ed25519PrivateKey.generate()
    private_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_pem


# Module-level key pair (loaded once at import)
_PRIVATE_KEY_PEM, _PUBLIC_KEY_PEM = _load_signing_keys()


# ================================================================
# CRYPTO HELPERS
# ================================================================

def _generate_jwt(payload: dict) -> str:
    """Generate JWT signed with Ed25519 (EdDSA).

    payload must include: jti, sub, purpose, exp, iat.
    Returns the compact JWT string.
    """
    return pyjwt.encode(payload, _PRIVATE_KEY_PEM, algorithm=JWT_ALGORITHM)


def _verify_jwt(token: str) -> dict:
    """Verify JWT signature and decode payload.

    Raises pyjwt.InvalidTokenError (or subclass) if signature invalid,
    expired, or malformed.
    """
    return pyjwt.decode(token, _PUBLIC_KEY_PEM, algorithms=[JWT_ALGORITHM])


def _hash_token(token: str) -> str:
    """SHA-256 hex digest of the full JWT string.

    Used for DB storage — we NEVER store the token plaintext.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _mask_email(email: str | None) -> str | None:
    """Enmascara un email para exposición pública: 'jor***@dominio.es'.

    Usado en MagicLinkPublicStatus.recipient_email_hint (ADR-011 B.1).
    Permite al cliente confirmar que abrió el link correcto sin filtrar
    el email completo a un atacante con el token.
    """
    if not email or "@" not in email:
        return None
    local, _, domain = email.partition("@")
    if len(local) <= 3:
        prefix = local
    else:
        prefix = local[:3]
    return f"{prefix}***@{domain}"


def _hash_otp(otp: str) -> str:
    """SHA-256 hex digest of OTP plaintext.

    We NEVER store the OTP plaintext in DB.
    """
    return hashlib.sha256(otp.encode("utf-8")).hexdigest()


def _generate_otp() -> tuple[str, str]:
    """Generate a 6-digit TOTP and its hash.

    Returns (otp_plaintext, otp_hash).
    The plaintext is shown to the creator once (to send via separate channel).
    The hash is stored in DB for verification.
    """
    # Use pyotp with a random secret to generate a one-time code
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret, digits=OTP_DIGITS)
    otp_plaintext = totp.now()
    otp_hash = _hash_otp(otp_plaintext)
    return otp_plaintext, otp_hash


# ================================================================
# AUDIT HELPER
# ================================================================

async def _log_interaction(
    db: AsyncSession,
    magic_link_id,
    accion: str,
    ip: str | None = None,
    user_agent: str | None = None,
    payload: dict | None = None,
):
    """Append-only audit entry in client_interactions."""
    interaction = ClientInteraction(
        magic_link_id=magic_link_id,
        accion=accion,
        ip=ip,
        user_agent=user_agent,
        timestamp=datetime.now(timezone.utc),
        payload=payload,
    )
    db.add(interaction)
    await db.flush()


# ================================================================
# SERVICE CLASS
# ================================================================

class MagicLinkService:
    """Core service for magic link lifecycle: generate, consume, revoke."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_magic_link(
        self,
        request: MagicLinkGenerateRequest,
        base_url: str,
    ) -> MagicLinkGenerateResponse:
        """Generate a new magic link for a specific purpose.

        1. Validate purpose policy (ADR-042) · soft-warn deprecated purposes
        2. Get config (TTL, max_uses, requires_otp)
        3. Generate JWT with payload {jti, sub, purpose, scope, exp, iat}
        4. Generate OTP if requires_otp=True
        5. Insert row in magic_links with token_hash (never plaintext)
        6. Build URL: {base_url}/ml/consume?token={token}
        7. Log 'generated' event in client_interactions
        8. Return response with token plaintext ONCE (never shown again)
        """
        # ADR-042 · MagicLinkPolicyEnforcer validation gate (SAN-D MB-19.9).
        # Soft-deprecation: NO bloquea generación · sólo log warning para
        # purposes ONBOARDING_INICIAL/APORTE_EVIDENCIA (compat backward sites
        # legacy m05/m16). Hard-deprecation diferida MB-20+ (DEC-MB19B-HARD).
        from backend.app.motors.m12_magic_link.policy_enforcer import (
            MagicLinkPolicyEnforcer,
        )
        enforcer = MagicLinkPolicyEnforcer()
        is_ok, policy_status, policy_reason = enforcer.validate_purpose(
            request.purpose,
        )
        if not is_ok:
            # Solo "unknown" purpose llega aquí · no debería ocurrir post
            # Pydantic enum validation pero safety net contra purpose
            # nuevo en enum sin categorización ADR-042.
            raise ValueError(
                f"MagicLinkPolicyEnforcer rechazó purpose: {policy_reason}"
            )
        # policy_status ∈ {"ok", "deprecated_soft"} · ambos permiten
        # generación · soft solo loggea (ya hecho en enforcer).

        config = get_config(request.purpose)

        now = datetime.now(timezone.utc)
        # FASE 4.5 sub-bloque B.1: ttl_hours / max_uses overrides
        # respect del request, fallback al PurposeConfig default.
        ttl_hours = request.ttl_hours if request.ttl_hours else config["ttl_hours"]
        max_uses = request.max_uses if request.max_uses else config["max_uses"]
        expires_at = now + timedelta(hours=ttl_hours)
        jti = str(uuid4())

        # JWT payload
        jwt_payload = {
            "jti": jti,
            "sub": str(request.project_id),
            "purpose": request.purpose.value,
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
        }
        if request.scope:
            jwt_payload["scope"] = request.scope

        token = _generate_jwt(jwt_payload)
        token_hash = _hash_token(token)

        # OTP (con expiración propia corta · §1.5 · indep del TTL del link)
        otp_plaintext = None
        otp_hash = None
        otp_expires_at = None
        if config["requires_otp"]:
            otp_plaintext, otp_hash = _generate_otp()
            otp_expires_at = now + timedelta(minutes=OTP_TTL_MINUTES)

        # Geo restriction
        allowed_countries = None
        if request.allowed_countries and config["requires_geo"]:
            allowed_countries = request.allowed_countries

        # FASE 4.5 sub-bloque B.1: email customization (cols migration f658961972a2)
        cc_emails = (
            [str(e) for e in request.cc_emails] if request.cc_emails else None
        )

        # Persist to DB
        link = MagicLink(
            project_id=request.project_id,
            tipo_operacion=request.purpose.value,
            scope=request.scope,
            token_hash=token_hash,
            otp_hash=otp_hash,
            otp_expires_at=otp_expires_at,
            expira_at=expires_at,
            max_usos=max_uses,
            usos=0,
            revocado=False,
            recipient_email=str(request.recipient_email),
            allowed_countries=allowed_countries,
            sent_to_contact_id=request.sent_to_contact_id,
            cc_emails=cc_emails,
            custom_subject=request.custom_subject,
            custom_body_intro=request.custom_body_intro,
        )
        self.db.add(link)
        await self.db.flush()

        # Audit
        await _log_interaction(
            self.db,
            magic_link_id=link.id,
            accion="generated",
            payload={
                "purpose": request.purpose.value,
                "recipient": str(request.recipient_email),
                "ttl_hours": config["ttl_hours"],
            },
        )

        url = f"{base_url}/ml/consume?token={token}"

        return MagicLinkGenerateResponse(
            magic_link_id=link.id,
            token=token,
            otp=otp_plaintext,
            url=url,
            expires_at=expires_at,
            purpose=request.purpose,
            action_label=config["action_label"],
        )

    async def consume_magic_link(
        self,
        request: MagicLinkConsumeRequest,
    ) -> MagicLinkConsumeResponse:
        """Consume a magic link — the critical security path.

        Verification order (fail-fast):
        1. Verify JWT signature (EdDSA) + not expired (exp claim)
        2. Hash token, find in DB by token_hash
        3. Link exists (not soft-deleted)
        4. Not revoked (revocado=False AND revoked_at IS NULL)
        5. Not expired (expira_at > now — belt-and-suspenders with JWT exp)
        6. Uses remaining (usos < max_usos)
        7. OTP valid if required (SHA-256 compare)
        8. OTP failures < threshold (3 = permanent block)
        9. Geo check (skipped until geo lib is installed)

        On OTP failure: increment otp_failures, return generic 403.
        On success: increment usos, log to client_interactions, return scope.
        """
        # Step 1: Verify JWT
        try:
            jwt_payload = _verify_jwt(request.token)
        except pyjwt.InvalidTokenError as e:
            raise MagicLinkNotFoundError("Token invalido o expirado") from e

        # Step 2: Find in DB by token_hash
        token_hash = _hash_token(request.token)
        result = await self.db.execute(
            select(MagicLink).where(
                MagicLink.token_hash == token_hash,
                MagicLink.deleted_at.is_(None),
            )
        )
        link = result.scalars().first()
        if not link:
            raise MagicLinkNotFoundError("Token no encontrado")

        # Step 3+4: Not revoked
        if link.revocado or link.revoked_at is not None:
            raise MagicLinkRevokedError("El enlace ha sido revocado")

        # Step 5: Not expired (belt-and-suspenders)
        now = datetime.now(timezone.utc)
        if link.expira_at.tzinfo is None:  # pragma: no cover — asyncpg always returns tz-aware
            expira_utc = link.expira_at.replace(tzinfo=timezone.utc)
        else:
            expira_utc = link.expira_at
        if now > expira_utc:
            raise MagicLinkExpiredError("El enlace ha expirado")

        # Step 6: Uses remaining
        max_usos = link.max_usos or 1
        if link.usos >= max_usos:
            raise MagicLinkExhaustedError("El enlace ha agotado sus usos")

        # Step 7+8: OTP verification
        if link.otp_hash:
            if link.otp_failures >= OTP_FAILURE_THRESHOLD:
                raise MagicLinkOTPBlockedError(
                    "El enlace ha sido bloqueado por demasiados intentos fallidos"
                )
            # §1.5: expiración propia del OTP (corta · indep del TTL del link).
            if link.otp_expires_at is not None:
                otp_exp = link.otp_expires_at
                if otp_exp.tzinfo is None:
                    otp_exp = otp_exp.replace(tzinfo=timezone.utc)
                if now > otp_exp:
                    raise MagicLinkExpiredError("El código OTP ha expirado")
            if not request.otp:
                raise MagicLinkOTPRequired("Se requiere codigo OTP para este enlace")

            provided_hash = _hash_otp(request.otp)
            if provided_hash != link.otp_hash:
                link.otp_failures += 1
                await self.db.flush()
                await _log_interaction(
                    self.db,
                    magic_link_id=link.id,
                    accion="otp_failed",
                    ip=request.client_ip,
                    user_agent=request.user_agent,
                    payload={"attempt": link.otp_failures},
                )
                raise MagicLinkInvalidOTPError("Codigo incorrecto")

        # Step 9: Geo check (skipped until geo lib is installed)
        # if link.allowed_countries:
        #     country = _geolocate_ip(request.client_ip)
        #     if country not in link.allowed_countries:
        #         raise MagicLinkError("Acceso no permitido desde su ubicacion")

        # SUCCESS: increment uses and log
        link.usos += 1
        await self.db.flush()

        config = get_config(MagicLinkPurpose(link.tipo_operacion))

        await _log_interaction(
            self.db,
            magic_link_id=link.id,
            accion="consumed",
            ip=request.client_ip,
            user_agent=request.user_agent,
            payload={
                "use_number": link.usos,
                "remaining": max_usos - link.usos,
            },
        )

        # M30 integration: si magic link tiene sent_to_contact_id, registrar
        # interaction en timeline del contacto. Patrón coherente con A18
        # (meeting), M14 (signature). Silent fail si contacto no existe
        # (consistente con M18).
        if link.sent_to_contact_id is not None:
            from backend.app.motors.m30_client_contacts.service import (
                ClientContactService,
                ContactNotFoundError,
            )
            try:
                await ClientContactService(self.db).log_interaction(
                    contact_id=link.sent_to_contact_id,
                    interaction_type="magic_link",
                    source_motor="m12",
                    source_id=link.id,
                    summary=f"Magic link consumido: {link.tipo_operacion}",
                    details={
                        "purpose": link.tipo_operacion,
                        "use_number": link.usos,
                        "remaining": max_usos - link.usos,
                    },
                )
            except ContactNotFoundError:
                # contacto eliminado tras emisión link — no bloquea consume.
                pass

        return MagicLinkConsumeResponse(
            magic_link_id=link.id,
            purpose=MagicLinkPurpose(link.tipo_operacion),
            project_id=link.project_id,
            scope=link.scope,
            action_label=config["action_label"],
            remaining_uses=max_usos - link.usos,
        )

    async def revoke_magic_link(
        self,
        magic_link_id,
        reason: str | None = None,
    ) -> None:
        """Revoke a magic link. Sets revocado=True + revoked_at=now().

        Idempotent: revoking an already-revoked link is a no-op.
        """
        link = await self.db.get(MagicLink, magic_link_id)
        if not link or link.deleted_at is not None:
            raise MagicLinkNotFoundError("Magic link no encontrado")

        if link.revocado:
            return  # idempotent

        now = datetime.now(timezone.utc)
        link.revocado = True
        link.revoked_at = now
        await self.db.flush()

        await _log_interaction(
            self.db,
            magic_link_id=link.id,
            accion="revoked",
            payload={"reason": reason} if reason else None,
        )

    async def get_magic_link_status(self, magic_link_id) -> dict:
        """Get current status of a magic link (for admin dashboard)."""
        link = await self.db.get(MagicLink, magic_link_id)
        if not link or link.deleted_at is not None:
            raise MagicLinkNotFoundError("Magic link no encontrado")

        now = datetime.now(timezone.utc)
        expira_utc = link.expira_at
        if expira_utc.tzinfo is None:  # pragma: no cover — asyncpg always returns tz-aware
            expira_utc = expira_utc.replace(tzinfo=timezone.utc)

        max_usos = link.max_usos or 1
        is_expired = now > expira_utc
        is_revoked = link.revocado or link.revoked_at is not None
        is_exhausted = link.usos >= max_usos
        is_blocked = link.otp_failures >= OTP_FAILURE_THRESHOLD

        if is_revoked:
            status = "revoked"
        elif is_blocked:
            status = "blocked_otp"
        elif is_expired:
            status = "expired"
        elif is_exhausted:
            status = "exhausted"
        else:
            status = "active"

        return {
            "id": str(link.id),
            "purpose": link.tipo_operacion,
            "status": status,
            "uses": link.usos,
            "max_uses": max_usos,
            "expires_at": expira_utc.isoformat(),
            "created_at": link.created_at.isoformat(),
            "recipient_email": link.recipient_email,
            "otp_failures": link.otp_failures,
        }

    # ────────────────────────────────────────────────────────────
    # FASE 4.5 sub-bloque B · list + by-token public status
    # ────────────────────────────────────────────────────────────

    async def list_magic_links(
        self,
        project_id=None,
        purpose: str | None = None,
        active_only: bool = False,
        limit: int = 50,
    ) -> list[MagicLink]:
        """List magic links filtered (admin only).

        Caller debe haber establecido SET LOCAL ROLE fulkro_app_bypassrls o tenant context
        adecuado antes de invocar (RLS bypass en endpoint).
        """
        stmt = select(MagicLink).where(MagicLink.deleted_at.is_(None))
        if project_id is not None:
            stmt = stmt.where(MagicLink.project_id == project_id)
        if purpose is not None:
            stmt = stmt.where(MagicLink.tipo_operacion == purpose)
        if active_only:
            now = datetime.now(timezone.utc)
            stmt = stmt.where(
                MagicLink.revocado.is_(False),
                MagicLink.expira_at > now,
            )
        stmt = stmt.order_by(MagicLink.created_at.desc()).limit(limit)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_status_by_token(self, token: str) -> dict:
        """Resuelve token plaintext → contexto PÚBLICO del magic link.

        Endpoint público sin auth (sign-flow pre-consume). NO consume
        usos ni expone secretos. Usa el mismo hash de token que /consume
        para lookup.

        Devuelve subset estricto (privacidad ADR-011 sub-bloque B.1):
        - tipo_operacion, scope, expira_at, max_usos, usos, revocado
        - recipient_email_hint (3 chars + *** + dominio)

        NO devuelve: id interno, project_id, recipient_email completo,
        cc_emails, custom_subject/body_intro, allowed_countries.
        """
        token_hash = _hash_token(token)
        stmt = select(MagicLink).where(
            MagicLink.token_hash == token_hash,
            MagicLink.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        link = result.scalar_one_or_none()
        if link is None:
            raise MagicLinkNotFoundError("Magic link no encontrado")

        expira_utc = link.expira_at
        if expira_utc.tzinfo is None:  # pragma: no cover — asyncpg returns tz-aware
            expira_utc = expira_utc.replace(tzinfo=timezone.utc)

        return {
            "tipo_operacion": link.tipo_operacion,
            "scope": link.scope,
            "expira_at": expira_utc,
            "max_usos": link.max_usos,
            "usos": link.usos,
            "revocado": link.revocado,
            "recipient_email_hint": _mask_email(link.recipient_email),
        }


# ================================================================
# EXCEPTIONS
# ================================================================

class MagicLinkError(Exception):
    """Base exception for all magic link errors.

    Endpoints HTTP catchean esta excepcion generica y devuelven 403
    con mensaje uniforme al atacante (evita user enumeration). Los
    tests y el codigo interno pueden usar las subclases especificas
    para distinguir la causa exacta del fallo.
    """


class MagicLinkNotFoundError(MagicLinkError):
    """Token hash not found in magic_links table."""


class MagicLinkExpiredError(MagicLinkError):
    """Link has expired (expira_at < now())."""


class MagicLinkRevokedError(MagicLinkError):
    """Link was revoked (revocado=True or revoked_at IS NOT NULL)."""


class MagicLinkExhaustedError(MagicLinkError):
    """Link consumed beyond max_uses (usos >= max_usos)."""


class MagicLinkInvalidOTPError(MagicLinkError):
    """OTP provided does not match stored hash. Increments otp_failures."""


class MagicLinkOTPBlockedError(MagicLinkError):
    """OTP failure threshold reached (otp_failures >= OTP_FAILURE_THRESHOLD)."""


class MagicLinkOTPRequired(MagicLinkError):
    """OTP is required by the purpose but was not provided in the request."""
