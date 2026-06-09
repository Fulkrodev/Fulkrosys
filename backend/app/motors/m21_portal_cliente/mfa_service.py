"""CLUSTER 6 Phase 6A · MFA TOTP cliente service.

Reuse admin ``backend/app/auth/totp_svc`` canonical helpers (generate_secret,
verify_code, provisioning_uri) · DRY OPS-026 sostained.

Filosofía cliente-mínimo: cliente opt-in voluntary · NO forced. ``initiate``
genera secret + otpauth_uri (UI frontend renders QR via SVG inline · NO
extra deps). ``confirm`` verifica primer código + genera 10 backup codes
single-use. ``verify_login`` accepts TOTP o backup code (consume) en login
post-password. ``disable`` requiere current TOTP + audit log.

audit_log emit canonical events Sub-atom 5.A 3-way OR pattern:
- mfa.initiated   · cliente startea enrollment
- mfa.confirmed   · cliente verifica + backup codes generadas
- mfa.verified    · login successful via TOTP
- mfa.failed      · TOTP code wrong (también backup wrong)
- mfa.backup_code_used · cliente usó backup code en login
- mfa.disabled    · cliente desactiva MFA (require TOTP confirm)
"""
from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth import totp_svc
from backend.app.models.client_portal import (
    ClientUser,
    ClientUserBackupCode,
    ClientUserTotpSecret,
)

BACKUP_CODES_COUNT = 10
BACKUP_CODE_LENGTH = 10  # 10 hex chars · displayable groups of 5

# 2026-06-09 · MFA por CÓDIGO AL EMAIL (sustituye TOTP para el cliente).
EMAIL_CODE_DIGITS = 6
EMAIL_CODE_TTL_MINUTES = 10
EMAIL_CODE_MAX_ATTEMPTS = 5


class MfaError(Exception):
    """MFA-related error · login/setup/disable issues."""


@dataclass
class InitiateResult:
    secret: str
    otpauth_uri: str


@dataclass
class ConfirmResult:
    backup_codes: list[str]


def _hash_backup_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _generate_backup_codes() -> list[str]:
    """Generate ``BACKUP_CODES_COUNT`` cryptographically-random hex codes."""
    return [
        secrets.token_hex(BACKUP_CODE_LENGTH // 2)
        for _ in range(BACKUP_CODES_COUNT)
    ]


async def _resolve_active_project_id(
    db: AsyncSession, client_id: uuid.UUID,
) -> uuid.UUID | None:
    """Resolve latest non-deleted project_id for client (audit_log 3-way OR)."""
    result = await db.execute(
        text(
            "SELECT id FROM projects WHERE client_id = :cid "
            "AND deleted_at IS NULL "
            "ORDER BY created_at DESC LIMIT 1"
        ),
        {"cid": str(client_id)},
    )
    return result.scalar_one_or_none()


async def _emit_audit(
    db: AsyncSession,
    user: ClientUser,
    action_type: str,
    action_data: dict | None = None,
) -> None:
    """Sub-atom 5.A audit_log 3-way OR emit · best-effort try/except.

    Pattern aligned con ChatService._emit_chat_audit_log + Phase 5 cumulative
    cluster propagation 5/5. Hash chain via AuditLogService cuando project
    resolvable · skip silent si client sin proyectos (cliente nuevo registry).
    """
    project_id = await _resolve_active_project_id(db, user.client_id)
    if project_id is None:
        return
    try:
        from backend.app.motors.m21_portal_cliente.audit_log_service import (
            AuditLogService,
        )
        service = AuditLogService(db)
        await service.log_action(
            project_id=project_id,
            client_user_id=user.id,
            action_type=action_type,
            action_data=action_data or {},
            client_id=user.client_id,
        )
    except Exception:
        # audit_log write failure NO bloquea MFA flow (graceful degradation)
        pass


async def get_totp_record(
    db: AsyncSession, client_user_id: uuid.UUID,
) -> ClientUserTotpSecret | None:
    result = await db.execute(
        select(ClientUserTotpSecret).where(
            ClientUserTotpSecret.client_user_id == client_user_id,
            ClientUserTotpSecret.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def initiate(
    db: AsyncSession, user: ClientUser,
) -> InitiateResult:
    """Start MFA enrollment · genera secret + otpauth_uri (NOT verified yet).

    Idempotent: si record existe NOT verified → re-genera secret (cliente
    re-empezó scanning QR). Si verified=True → MfaError (debe disable primero).
    """
    existing = await get_totp_record(db, user.id)
    if existing and existing.verified:
        raise MfaError("MFA ya activado · desactiva primero para re-enrollar")

    secret = totp_svc.generate_secret()
    if existing:
        existing.secret = secret
        existing.verified = False
        existing.confirmed_at = None
        existing.last_used_at = None
    else:
        rec = ClientUserTotpSecret(
            client_user_id=user.id,
            secret=secret,
            verified=False,
        )
        db.add(rec)

    await db.flush()
    await _emit_audit(db, user, "mfa.initiated")

    return InitiateResult(
        secret=secret,
        otpauth_uri=totp_svc.provisioning_uri(secret, user.email),
    )


async def confirm(
    db: AsyncSession, user: ClientUser, code: str,
) -> ConfirmResult:
    """Verifica primer TOTP code + activa MFA + genera backup codes.

    Backup codes DISPLAYED ONCE response · cliente debe anotarlas.
    Idempotent backup-codes: si confirm called twice · second call regenera
    backup codes (old codes marked deleted via DELETE WHERE unused).
    """
    rec = await get_totp_record(db, user.id)
    if rec is None:
        raise MfaError("Inicia enrollment primero")

    if not totp_svc.verify_code(rec.secret, code):
        await _emit_audit(db, user, "mfa.failed", {"reason": "confirm_bad_code"})
        raise MfaError("Código TOTP inválido")

    now = datetime.now(timezone.utc)
    rec.verified = True
    rec.confirmed_at = now
    rec.last_used_at = now
    user.mfa_enabled = True
    user.mfa_method = "totp"  # enrolling TOTP fija el método (login lo respeta)

    # Wipe any prior unused backup codes (re-confirm regenera fresh batch)
    await db.execute(
        text(
            "DELETE FROM client_user_backup_codes "
            "WHERE client_user_id = :uid AND used_at IS NULL"
        ),
        {"uid": str(user.id)},
    )

    backup_codes = _generate_backup_codes()
    for code_plain in backup_codes:
        db.add(ClientUserBackupCode(
            client_user_id=user.id,
            code_hash=_hash_backup_code(code_plain),
        ))
    await db.flush()
    await _emit_audit(db, user, "mfa.confirmed", {"backup_codes_count": len(backup_codes)})

    return ConfirmResult(backup_codes=backup_codes)


async def verify_login_code(
    db: AsyncSession, user: ClientUser, code: str,
) -> bool:
    """Verifica el segundo factor en login según ``user.mfa_method``.

    - ``email`` (default · nuevo): código de 6 dígitos enviado al email.
    - ``totp`` (legacy · compat): TOTP de app autenticadora o backup code.

    On success emit audit ``mfa.verified`` (o ``mfa.backup_code_used``).
    On failure emit ``mfa.failed``.
    """
    # 2026-06-09 · método por defecto = código al email (sustituye TOTP).
    if (user.mfa_method or "email") == "email":
        return await verify_email_code(db, user, code)

    # --- legacy TOTP / backup code path (method='totp') ---
    rec = await get_totp_record(db, user.id)
    if rec is None or not rec.verified:
        await _emit_audit(db, user, "mfa.failed", {"reason": "no_mfa_record"})
        return False

    code_clean = (code or "").strip().replace(" ", "")

    # TOTP path
    if code_clean.isdigit() and len(code_clean) == 6:
        if totp_svc.verify_code(rec.secret, code_clean):
            rec.last_used_at = datetime.now(timezone.utc)
            await db.flush()
            await _emit_audit(db, user, "mfa.verified")
            return True
        # else fall through to backup code attempt (defensive)

    # Backup code path
    code_hash = _hash_backup_code(code_clean.lower())
    result = await db.execute(
        select(ClientUserBackupCode).where(
            ClientUserBackupCode.client_user_id == user.id,
            ClientUserBackupCode.code_hash == code_hash,
            ClientUserBackupCode.used_at.is_(None),
        )
    )
    backup = result.scalar_one_or_none()
    if backup is None:
        await _emit_audit(db, user, "mfa.failed", {"reason": "code_invalid"})
        return False

    backup.used_at = datetime.now(timezone.utc)
    await db.flush()
    await _emit_audit(db, user, "mfa.backup_code_used")
    return True


# ════════════════════════════════════════════════════════════════════
# MFA por CÓDIGO AL EMAIL (2026-06-09 · sustituye TOTP para el cliente)
# ════════════════════════════════════════════════════════════════════


def _generate_email_code() -> str:
    """Código numérico de ``EMAIL_CODE_DIGITS`` dígitos (cero-padded)."""
    upper = 10 ** EMAIL_CODE_DIGITS
    return str(secrets.randbelow(upper)).zfill(EMAIL_CODE_DIGITS)


def _hash_email_code(code: str) -> str:
    return hashlib.sha256(code.strip().encode("utf-8")).hexdigest()


def _render_login_code_email(name: str, code: str) -> str:
    """Email R29 friendly con el código de verificación de login."""
    safe_name = (name or "").replace("<", "&lt;").replace(">", "&gt;")
    return f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 540px; margin: 0 auto; color: #1f2937;">
      <h2 style="color: #4f46e5;">Tu código de acceso</h2>
      <p>Hola {safe_name},</p>
      <p>Para entrar en tu portal, introduce este código de verificación:</p>
      <p style="font-size: 32px; font-weight: 700; letter-spacing: 6px; background: #f3f4f6; padding: 16px 24px; border-radius: 10px; text-align: center; color: #111827;">{code}</p>
      <p>Caduca en {EMAIL_CODE_TTL_MINUTES} minutos. Si no has intentado entrar,
      puedes ignorar este correo · tu cuenta sigue protegida.</p>
      <p style="color: #6b7280; font-size: 14px; margin-top: 32px;">FULKRO · sin prisa por tu parte.</p>
    </div>
    """.strip()


async def issue_email_code(db: AsyncSession, user: ClientUser) -> None:
    """Genera + envía por email un código de login de 6 dígitos.

    Guarda solo el hash (sha256) + caducidad en ``client_users``, resetea el
    contador de intentos y envía el email (best-effort · un fallo de envío NO
    rompe el flujo · el cliente puede pedir reenvío). Emit audit ``mfa.code_sent``.
    """
    code = _generate_email_code()
    now = datetime.now(timezone.utc)
    user.mfa_email_code_hash = _hash_email_code(code)
    user.mfa_email_code_expires_at = now + timedelta(minutes=EMAIL_CODE_TTL_MINUTES)
    user.mfa_email_code_attempts = 0
    user.mfa_email_code_sent_at = now
    await db.flush()
    await _emit_audit(db, user, "mfa.code_sent", {"channel": "email"})

    try:
        from backend.app.core.email.sender import get_email_sender

        sender = get_email_sender()
        await sender.send(
            db,
            to=user.email,
            subject="Tu código de acceso a FULKRO",
            html_body=_render_login_code_email(user.full_name or user.email, code),
            template_used="mfa_login_code",
            client_id=user.client_id,
        )
    except Exception:  # pragma: no cover · best-effort
        # El envío puede fallar (SMTP no configurado en local/dev). NO bloquea
        # la señalización requires_mfa · el cliente puede reenviar.
        pass


async def confirm_email_enrollment(
    db: AsyncSession, user: ClientUser, code: str,
) -> bool:
    """Activa MFA por email: verifica el código enviado en ``issue_email_code``
    y, si es correcto, deja ``mfa_enabled=True`` + ``mfa_method='email'``.

    Returns True si activado · False si el código es inválido/caducado.
    """
    ok = await verify_email_code(db, user, code)
    if not ok:
        return False
    user.mfa_enabled = True
    user.mfa_method = "email"
    await db.flush()
    await _emit_audit(db, user, "mfa.confirmed", {"channel": "email"})
    return True


async def verify_email_code(
    db: AsyncSession, user: ClientUser, code: str,
) -> bool:
    """Verifica el código de email · caducidad + intentos + match (consume).

    On success limpia el código y emit ``mfa.verified``. On failure incrementa
    intentos y emit ``mfa.failed``. Caducado o sin código → False.
    """
    now = datetime.now(timezone.utc)
    code_clean = (code or "").strip().replace(" ", "")

    if not user.mfa_email_code_hash or user.mfa_email_code_expires_at is None:
        await _emit_audit(db, user, "mfa.failed", {"reason": "no_email_code"})
        return False
    if user.mfa_email_code_expires_at < now:
        await _emit_audit(db, user, "mfa.failed", {"reason": "email_code_expired"})
        return False
    if (user.mfa_email_code_attempts or 0) >= EMAIL_CODE_MAX_ATTEMPTS:
        await _emit_audit(db, user, "mfa.failed", {"reason": "email_code_max_attempts"})
        return False

    if _hash_email_code(code_clean) != user.mfa_email_code_hash:
        user.mfa_email_code_attempts = (user.mfa_email_code_attempts or 0) + 1
        await db.flush()
        await _emit_audit(db, user, "mfa.failed", {"reason": "email_code_invalid"})
        return False

    # Éxito · consume el código (single-use).
    user.mfa_email_code_hash = None
    user.mfa_email_code_expires_at = None
    user.mfa_email_code_attempts = 0
    await db.flush()
    await _emit_audit(db, user, "mfa.verified", {"channel": "email"})
    return True


async def disable(
    db: AsyncSession, user: ClientUser, code: str,
) -> None:
    """Desactiva MFA · emit audit ``mfa.disabled``.

    - method='email': basta sesión autenticada (no se pide código · el cliente
      ya está dentro de Ajustes). Limpia el código pendiente.
    - method='totp' (legacy): requiere el TOTP actual + borra secret/backup codes.
    """
    if (user.mfa_method or "email") == "email":
        user.mfa_enabled = False
        user.mfa_email_code_hash = None
        user.mfa_email_code_expires_at = None
        user.mfa_email_code_attempts = 0
        await db.flush()
        await _emit_audit(db, user, "mfa.disabled", {"channel": "email"})
        return

    rec = await get_totp_record(db, user.id)
    if rec is None or not rec.verified:
        raise MfaError("MFA no está activo")

    if not totp_svc.verify_code(rec.secret, (code or "").strip()):
        await _emit_audit(db, user, "mfa.failed", {"reason": "disable_bad_code"})
        raise MfaError("Código TOTP inválido")

    rec.deleted_at = datetime.now(timezone.utc)
    user.mfa_enabled = False
    await db.execute(
        text(
            "DELETE FROM client_user_backup_codes "
            "WHERE client_user_id = :uid AND used_at IS NULL"
        ),
        {"uid": str(user.id)},
    )
    await db.flush()
    await _emit_audit(db, user, "mfa.disabled")


async def status(
    db: AsyncSession, user: ClientUser,
) -> dict:
    """Read MFA state cliente · settings page header info.

    2026-06-09 · expone ``method`` ('email'|'totp'). Para 'email', enrolled y
    verified == mfa_enabled (no hay secret · el email ya es conocido).
    """
    method = user.mfa_method or "email"
    if method == "email":
        return {
            "method": "email",
            "mfa_enabled": user.mfa_enabled,
            "enrolled": user.mfa_enabled,
            "verified": user.mfa_enabled,
            "email": user.email,
            "backup_codes_remaining": 0,
            "last_used_at": None,
        }

    rec = await get_totp_record(db, user.id)
    enrolled = rec is not None
    verified = rec is not None and rec.verified
    remaining_backup = 0
    if verified:
        result = await db.execute(
            text(
                "SELECT COUNT(*) FROM client_user_backup_codes "
                "WHERE client_user_id = :uid AND used_at IS NULL"
            ),
            {"uid": str(user.id)},
        )
        remaining_backup = result.scalar_one()
    return {
        "method": "totp",
        "mfa_enabled": user.mfa_enabled,
        "enrolled": enrolled,
        "verified": verified,
        "email": user.email,
        "backup_codes_remaining": int(remaining_backup),
        "last_used_at": rec.last_used_at.isoformat() if rec and rec.last_used_at else None,
    }
