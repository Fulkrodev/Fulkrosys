"""M21 Portal Cliente — auth service (login, JWT, audit).

Reutiliza los helpers de backend/app/auth/crypto.py (hash_password,
verify_password, issue_token, decode_token, Ed25519 JWT).
"""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt as pyjwt
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.crypto import (
    decode_token, generate_csrf_token, hash_password, issue_token,
    verify_password,
)
from backend.app.models.client_portal import (
    ClientSession, ClientUser, ClientUserAudit,
)

from .scopes import PORTAL_SCOPE


SESSION_TTL = timedelta(hours=12)
# Acceso de soporte trazado: sesión de impersonation READ-ONLY corta (decisión
# Marcos · caduca sola · menos ventana abierta).
SUPPORT_SESSION_TTL = timedelta(minutes=45)
LOCKOUT_THRESHOLD = 5
LOCKOUT_MINUTES = 30


class MfaRequiredError(Exception):
    """Password OK but user has MFA enabled and no mfa_code provided.

    CLUSTER 6 Phase 6A · 2-step login: endpoint catches y devuelve HTTP 401
    con ``requires_mfa: True`` permitiendo UI prompt TOTP step 2.
    """


class AuthError(Exception):
    """Errores de autenticacion (login, scopes)."""


def _generate_temp_password() -> str:
    """Password temporal seguro para primer acceso (12 chars)."""
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789"
    return "".join(secrets.choice(chars) for _ in range(12))


async def _log_audit(
    db: AsyncSession,
    user: ClientUser | None,
    action: str,
    metadata: dict | None = None,
    ip: str | None = None,
    client_id: uuid.UUID | None = None,
) -> None:
    entry = ClientUserAudit(
        client_user_id=user.id if user else None,
        client_id=(client_id or (user.client_id if user else None)),
        action=action,
        metadata_jsonb=metadata or {},
        ip_address=ip,
        created_at=datetime.now(timezone.utc),
    )
    db.add(entry)
    await db.flush()


async def _resolve_active_project_id(
    db: AsyncSession, client_id: uuid.UUID,
) -> uuid.UUID | None:
    """Resuelve el project_id activo del client (latest non-deleted) ·
    None si client no tiene proyectos · usado MB-14.2 hash chain
    integration (DEC-MB14-1 ADR-038)."""
    result = await db.execute(
        text(
            "SELECT id FROM projects WHERE client_id = :cid "
            "AND deleted_at IS NULL "
            "ORDER BY created_at DESC LIMIT 1"
        ),
        {"cid": str(client_id)},
    )
    return result.scalar_one_or_none()


async def _log_audit_chain(
    db: AsyncSession,
    user: ClientUser,
    action_type: str,
    action_data: dict | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
    session_id: str | None = None,
) -> None:
    """Log hash-chain audit entry (ADR-038 MB-14.2) si project resolvable.

    Backward compat: si project no resolvable · skip silent (event sigue
    persistido en _log_audit standard · sin hash chain).
    """
    project_id = await _resolve_active_project_id(db, user.client_id)
    if not project_id:
        return

    from backend.app.motors.m21_portal_cliente.audit_log_service import (
        AuditLogService,
    )

    service = AuditLogService(db)
    try:
        await service.log_action(
            project_id=project_id,
            client_user_id=user.id,
            action_type=action_type,
            action_data=action_data or {},
            ip_address=ip,
            user_agent=user_agent,
            session_id=session_id,
            client_id=user.client_id,
        )
    except Exception:
        # Hash chain write failure NO debe abortar login/logout flow.
        pass


# ════════════════════════════════════════════════════════════════════
# User lifecycle (Marcos desde cockpit)
# ════════════════════════════════════════════════════════════════════

async def create_user(
    db: AsyncSession,
    client_id: uuid.UUID,
    email: str,
    full_name: str,
    *,
    dni: str | None = None,
) -> tuple[ClientUser, str]:
    """Crea usuario portal cliente con password temporal · siempre RW unico (ADR-013 v3).

    Devuelve (user, temp_password). Constraint v3: maximo 1 usuario activo
    por client_id. Validacion en service-layer + UNIQUE BD (commit 3).
    """
    email_norm = email.strip().lower()

    # Duplicado?
    r = await db.execute(
        select(ClientUser).where(
            ClientUser.client_id == client_id,
            ClientUser.email == email_norm,
            ClientUser.deleted_at.is_(None),
        )
    )
    existing = r.scalar_one_or_none()
    if existing is not None:
        raise AuthError(
            f"Ya existe usuario con email {email_norm} para este cliente"
        )

    temp_password = _generate_temp_password()
    user = ClientUser(
        client_id=client_id,
        email=email_norm,
        password_hash=hash_password(temp_password),
        full_name=full_name,
        dni=dni,
        must_change_password=True,
        created_by_marcos=True,
    )
    db.add(user)
    await db.flush()
    await _log_audit(
        db, user, "user_created",
        metadata={"created_by": "marcos", "scope": PORTAL_SCOPE},
        client_id=client_id,
    )
    return user, temp_password


async def list_users_by_client(
    db: AsyncSession, client_id: uuid.UUID,
) -> list[ClientUser]:
    r = await db.execute(
        select(ClientUser).where(
            ClientUser.client_id == client_id,
            ClientUser.deleted_at.is_(None),
        ).order_by(ClientUser.email)
    )
    return list(r.scalars().all())


async def deactivate_user(
    db: AsyncSession, user_id: uuid.UUID,
) -> ClientUser:
    user = await db.get(ClientUser, user_id)
    if user is None:
        raise AuthError("Usuario no encontrado")
    user.deactivated_at = datetime.now(timezone.utc)
    # Revoca todas las sesiones activas
    sessions = (await db.execute(
        select(ClientSession).where(
            ClientSession.client_user_id == user_id,
            ClientSession.revoked_at.is_(None),
        )
    )).scalars().all()
    now = datetime.now(timezone.utc)
    for s in sessions:
        s.revoked_at = now
    await _log_audit(db, user, "user_deactivated")
    return user


async def reset_password_by_marcos(
    db: AsyncSession, user_id: uuid.UUID,
) -> str:
    """Marcos fuerza reset: genera nueva temp password + must_change_password."""
    user = await db.get(ClientUser, user_id)
    if user is None:
        raise AuthError("Usuario no encontrado")
    temp = _generate_temp_password()
    user.password_hash = hash_password(temp)
    user.must_change_password = True
    user.failed_attempts = 0
    user.locked_until = None
    await _log_audit(
        db, user, "password_reset_by_marcos",
    )
    return temp


async def update_user(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    email: str | None = None,
    full_name: str | None = None,
) -> ClientUser:
    """Marcos edita email/full_name de un ClientUser (cockpit · require_owner).

    Pre-check de UNIQUE(client_id, email) → AuthError controlado (NO IntegrityError
    /500). Emails se almacenan normalizados (strip().lower() · igual que
    create_user/login). Cambiar el email NO invalida sesiones activas (atadas al
    user_id, no al email · default Marcos · no fuerza re-login).
    """
    user = await db.get(ClientUser, user_id)
    if user is None or user.deactivated_at is not None:
        raise AuthError("Usuario no encontrado")
    changed: list[str] = []
    if email is not None:
        email_norm = email.strip().lower()
        if email_norm != user.email:
            dup = (await db.execute(
                select(ClientUser.id).where(
                    ClientUser.client_id == user.client_id,
                    ClientUser.email == email_norm,
                    ClientUser.id != user_id,
                ).limit(1)
            )).first()
            if dup is not None:
                raise AuthError(
                    "Ya existe un usuario con ese email en este cliente."
                )
            user.email = email_norm
            changed.append("email")
    if full_name is not None:
        user.full_name = full_name.strip() or None
        changed.append("full_name")
    await _log_audit(
        db, user, "user_updated_by_marcos", metadata={"fields": changed},
    )
    await db.flush()
    return user


# ════════════════════════════════════════════════════════════════════
# Login / logout
# ════════════════════════════════════════════════════════════════════

async def login(
    db: AsyncSession,
    email: str,
    password: str,
    *,
    ip: str | None = None,
    user_agent: str | None = None,
    mfa_code: str | None = None,
) -> tuple[ClientUser, str, str, datetime]:
    """Login: valida password + opcional TOTP MFA cliente.

    Devuelve (user, session_jwt, csrf_token, expires_at).

    CLUSTER 6 Phase 6A · cliente puede opt-in MFA voluntary. Si
    ``user.mfa_enabled = True`` y ``mfa_code is None`` → raise
    ``MfaRequiredError`` (endpoint devuelve 401 + ``requires_mfa: True``
    permitiendo UI step 2). Si ``mfa_code`` provided → verifica via
    ``mfa_service.verify_login_code`` (acepta TOTP 6 dígitos o backup
    code single-use).

    Backward compat: cliente sin MFA (``mfa_enabled=False``) sigue flujo
    SAN-E.MB-1.1 ADR-046 original · solo password.

    El csrf_token se embebe como claim ``csrf`` del JWT y también se
    devuelve para que el endpoint lo setee en la cookie ``fulkro_csrf``
    (pattern triple binding, ver ADR-019: header == cookie == JWT
    claim, replicando admin dependencies.py:53-65).
    """
    email_norm = email.strip().lower()
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    r = await db.execute(
        select(ClientUser).where(
            ClientUser.email == email_norm,
            ClientUser.deleted_at.is_(None),
        )
    )
    user = r.scalar_one_or_none()

    if user is None:
        # No exponer "email no existe"; log audit generico
        await _log_audit(
            db, None, "login_failure",
            metadata={"reason": "unknown_email", "email": email_norm},
            ip=ip,
        )
        raise AuthError("Credenciales invalidas")

    if user.deactivated_at is not None:
        await _log_audit(db, user, "login_failure",
                          metadata={"reason": "deactivated"}, ip=ip)
        raise AuthError("Usuario desactivado")

    now = datetime.now(timezone.utc)
    if user.locked_until and user.locked_until > now:
        await _log_audit(db, user, "login_failure",
                          metadata={"reason": "locked",
                                    "locked_until": user.locked_until.isoformat()},
                          ip=ip)
        raise AuthError(
            f"Cuenta bloqueada hasta {user.locked_until.isoformat()}"
        )

    if not verify_password(password, user.password_hash):
        user.failed_attempts = (user.failed_attempts or 0) + 1
        if user.failed_attempts >= LOCKOUT_THRESHOLD:
            user.locked_until = now + timedelta(minutes=LOCKOUT_MINUTES)
            await _log_audit(db, user, "account_locked",
                              metadata={"failed_attempts": user.failed_attempts},
                              ip=ip)
        else:
            await _log_audit(db, user, "login_failure",
                              metadata={"reason": "bad_password",
                                        "failed_attempts": user.failed_attempts},
                              ip=ip)
        await db.flush()
        raise AuthError("Credenciales invalidas")

    # CLUSTER 6 Phase 6A · MFA gate post-password verify.
    # Si user opt-in MFA y NO viene código → señalizamos UI step 2.
    # Si código provided → verificamos antes de seguir adelante.
    if user.mfa_enabled:
        from backend.app.motors.m21_portal_cliente import mfa_service

        if mfa_code is None:
            # 2026-06-09 · método por defecto = código al email. En el step 1
            # (sin código) se lo ENVIAMOS para que lo teclee en el step 2.
            if (user.mfa_method or "email") == "email":
                await mfa_service.issue_email_code(db, user)
            await _log_audit(
                db, user, "login_mfa_required", ip=ip,
            )
            _mfa_err = MfaRequiredError("Verificación 2 pasos requerida")
            _mfa_err.method = user.mfa_method or "email"  # frontend copy hint
            raise _mfa_err
        ok = await mfa_service.verify_login_code(db, user, mfa_code)
        if not ok:
            user.failed_attempts = (user.failed_attempts or 0) + 1
            if user.failed_attempts >= LOCKOUT_THRESHOLD:
                user.locked_until = now + timedelta(minutes=LOCKOUT_MINUTES)
                await _log_audit(
                    db, user, "account_locked",
                    metadata={"failed_attempts": user.failed_attempts,
                              "reason": "mfa_failures"},
                    ip=ip,
                )
            else:
                await _log_audit(
                    db, user, "login_failure",
                    metadata={"reason": "bad_mfa_code",
                              "failed_attempts": user.failed_attempts},
                    ip=ip,
                )
            await db.flush()
            raise AuthError("Credenciales invalidas")

    # Success
    user.failed_attempts = 0
    user.locked_until = None
    user.last_login = now
    csrf_token = generate_csrf_token()
    # extra_claims["role"]: middleware Next.js dispatchea cliente vs admin.
    # ADR-013 v3 single-user-RW · siempre PORTAL_SCOPE ('rw') para portal
    # cliente. Frontend middleware reconoce 'rw' como cliente · 'owner' como
    # admin (ADR-018 cierra cliente portal flow simplificado · MB-3 cleanup).
    token, jti, expires_at = issue_token(
        user_id=f"client:{user.id}",
        typ="session",
        ttl=SESSION_TTL,
        csrf_token=csrf_token,
        extra_claims={"role": PORTAL_SCOPE},
    )
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    session = ClientSession(
        client_user_id=user.id,
        jwt_jti=jti,
        jwt_token_hash=token_hash,
        ip_address=ip,
        user_agent=user_agent,
        expires_at=expires_at,
        last_activity=now,
    )
    db.add(session)
    await _log_audit(db, user, "login_success", ip=ip)
    await _log_audit_chain(
        db, user, "LOGIN",
        action_data={
            "method": "password",
        },
        ip=ip,
        user_agent=user_agent,
        session_id=token[:64],
    )
    await db.flush()
    return user, token, csrf_token, expires_at


async def mint_support_session(
    db: AsyncSession,
    client_user: ClientUser,
    admin_user_id: uuid.UUID,
    *,
    ip: str | None = None,
    user_agent: str | None = None,
) -> tuple[str, str, datetime]:
    """Acuña una sesión de soporte READ-ONLY (admin → portal cliente) SIN password.

    Espeja el minteo de ``login`` pero: (1) TTL corto (SUPPORT_SESSION_TTL · 45min),
    (2) claim ``support=true`` en el JWT → lo lee ``authenticate_request`` (chokepoint
    app-level) para rechazar TODO método mutating (read-only transversal), (3)
    ClientSession con ``is_support_access=True`` + ``support_admin_user_id`` (rastro
    + revoke + atribución). NO valida password (autoridad del admin · require_owner
    en el endpoint que la invoca). La prueba legal inmutable va en audit_log.

    Devuelve (session_jwt, csrf_token, expires_at).
    """
    now = datetime.now(timezone.utc)
    csrf_token = generate_csrf_token()
    token, jti, expires_at = issue_token(
        user_id=f"client:{client_user.id}",
        typ="session",
        ttl=SUPPORT_SESSION_TTL,
        csrf_token=csrf_token,
        extra_claims={"role": PORTAL_SCOPE, "support": True},
    )
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    session = ClientSession(
        client_user_id=client_user.id,
        jwt_jti=jti,
        jwt_token_hash=token_hash,
        ip_address=ip,
        user_agent=user_agent,
        expires_at=expires_at,
        last_activity=now,
        is_support_access=True,
        support_admin_user_id=admin_user_id,
    )
    db.add(session)
    await db.flush()
    return token, csrf_token, expires_at


async def logout(
    db: AsyncSession, jwt_jti: str, *, ip: str | None = None,
) -> bool:
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    r = await db.execute(
        select(ClientSession).where(
            ClientSession.jwt_jti == jwt_jti,
            ClientSession.deleted_at.is_(None),
        )
    )
    session = r.scalar_one_or_none()
    if session is None:
        return False
    session.revoked_at = datetime.now(timezone.utc)
    user = await db.get(ClientUser, session.client_user_id)
    await _log_audit(db, user, "session_revoked",
                      metadata={"jti": jwt_jti}, ip=ip)
    if user:
        await _log_audit_chain(
            db, user, "LOGOUT",
            action_data={"jti": jwt_jti}, ip=ip,
        )
    # Acceso de soporte: si la sesión revocada era de soporte, emite el bookend
    # support.access.ended en audit_log (R6 · Sub-atom 5.A) · prueba legal de
    # cuándo terminó el acceso del admin. "reusa el logout" (decisión Marcos).
    if session.is_support_access:
        import json as _json
        admin_email = (await db.execute(
            text("SELECT email FROM auth_users WHERE id = :aid"),
            {"aid": str(session.support_admin_user_id)},
        )).scalar() if session.support_admin_user_id else None
        await db.execute(text(
            "INSERT INTO audit_log (id, tabla, registro_id, accion, usuario, "
            "project_id, client_id, payload_new, timestamp) "
            "VALUES (gen_random_uuid(), 'client_sessions', :cid, "
            "'support.access.ended', :usr, NULL, :cid, :payload, now())"
        ), {
            "cid": str(user.client_id) if user else None,
            "usr": (admin_email or "admin")[:255],
            "payload": _json.dumps({
                "admin_user_id": (
                    str(session.support_admin_user_id)
                    if session.support_admin_user_id else None
                ),
                "client_user_id": str(session.client_user_id),
                "jti": jwt_jti,
                "reason": "logout",
            }),
        })
    await db.flush()
    return True


async def verify_session(
    db: AsyncSession, token: str,
) -> tuple[ClientUser, ClientSession]:
    """Verifica JWT + sesion activa. Raise AuthError si invalid."""
    try:
        payload = decode_token(token)
    except pyjwt.InvalidTokenError as exc:
        raise AuthError(f"Token invalido: {exc}")
    sub = payload.get("sub", "")
    if not sub.startswith("client:"):
        raise AuthError("Token no es de cliente")
    user_id = uuid.UUID(sub.removeprefix("client:"))
    jti = payload.get("jti")
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    r = await db.execute(
        select(ClientSession).where(
            ClientSession.jwt_jti == jti,
            ClientSession.client_user_id == user_id,
            ClientSession.revoked_at.is_(None),
            ClientSession.deleted_at.is_(None),
        )
    )
    session = r.scalar_one_or_none()
    if session is None:
        raise AuthError("Sesion no encontrada o revocada")
    if session.expires_at <= datetime.now(timezone.utc):
        raise AuthError("Sesion expirada")
    user = await db.get(ClientUser, user_id)
    if user is None or user.deactivated_at is not None:
        raise AuthError("Usuario desactivado")
    session.last_activity = datetime.now(timezone.utc)
    return user, session


# ════════════════════════════════════════════════════════════════════
# Password change
# ════════════════════════════════════════════════════════════════════

def validate_password_policy(pw: str) -> None:
    """Política de contraseña ClientUser (backend · autoridad · NO solo frontend).

    8-16 caracteres + al menos: una mayúscula, una minúscula, un número y un
    símbolo. Mensaje de error único y claro para el cliente. Aplica a las
    contraseñas que pone el USUARIO (la temporal server-generated se exime: el
    flujo must_change_password obliga a cambiarla por una que cumpla esto).
    """
    ok = (
        8 <= len(pw) <= 16
        and any(c.isupper() for c in pw)
        and any(c.islower() for c in pw)
        and any(c.isdigit() for c in pw)
        and any(not c.isalnum() for c in pw)
    )
    if not ok:
        raise AuthError(
            "La contraseña debe tener entre 8 y 16 caracteres e incluir "
            "mayúscula, minúscula, número y símbolo."
        )


async def change_password(
    db: AsyncSession,
    user_id: uuid.UUID,
    old_password: str,
    new_password: str,
    *,
    ip: str | None = None,
) -> ClientUser:
    user = await db.get(ClientUser, user_id)
    if user is None or user.deactivated_at is not None:
        raise AuthError("Usuario no encontrado")
    if not verify_password(old_password, user.password_hash):
        raise AuthError("Password actual incorrecta")
    validate_password_policy(new_password)
    user.password_hash = hash_password(new_password)
    user.password_changed_at = datetime.now(timezone.utc)
    user.must_change_password = False
    await _log_audit(db, user, "password_change", ip=ip)
    await db.flush()
    return user


__all__ = [
    "AuthError", "SESSION_TTL", "LOCKOUT_THRESHOLD", "LOCKOUT_MINUTES",
    "create_user", "list_users_by_client",
    "deactivate_user", "reset_password_by_marcos", "update_user",
    "login", "logout", "verify_session",
    "change_password", "validate_password_policy",
    "PORTAL_SCOPE",
]
