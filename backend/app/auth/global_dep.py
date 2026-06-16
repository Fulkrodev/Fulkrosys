"""Global dependency ``authenticate_request``.

Centraliza autenticación dispatcher dual + ``set_config`` audit user
+ CSRF para todos los endpoints excepto whitelist explícita.

Wired en ``main.py``:

    app = FastAPI(dependencies=[Depends(authenticate_request)])

Cobertura post-wiring (sub-fase 4.D Sesión 11):

- 22 endpoints existing con ``Depends`` auth chain (auth/* + admin_settings/*)
  ahora pasan también por global dep — defensa redundante OK.
- 262 endpoints motors mutating sin auth previa heredan auth + CSRF
  + set_config app.current_user automáticamente.

Whitelist 8 paths exact + 5 prefix (login, public portals, dev,
docs, magic_links public consume).

ADR-021 (motors auth strategy) + ADR-019 (CSRF triple binding) +
ADR-013 (separación 3 portales).

TODO-MOTORS-AUTH-LANDING-001 RESOLVE.
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

import jwt as pyjwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth import crypto
from backend.app.auth import service as auth_service_marcos
from backend.app.auth.csrf import SAFE_METHODS, SESSION_COOKIE, verify_csrf

# Acceso de soporte READ-ONLY · única ruta mutating permitida a una sesión de
# soporte (auto-logout para SALIR de soporte · ver guard en authenticate_request).
_SUPPORT_SELF_LOGOUT_PATH = "/api/v1/client-auth/logout"
from backend.app.database import get_db
from backend.app.models.auth import Session as MarcosSession
from backend.app.models.auth import User
from backend.app.models.client_portal import ClientUser
from backend.app.motors.m21_portal_cliente import auth_service as auth_service_cliente


# ────────────────────────────────────────────────────────────────────
# Whitelist paths — bypass auth check
# ────────────────────────────────────────────────────────────────────

# ADR-030: criterio inclusión + proceso amendment formalizado en
# docs/spec/DECISIONS.md. Cada entry tiene comentario justificación
# inline · cualquier nuevo endpoint requiere actualizar ADR-030.
WHITELIST_EXACT: frozenset[str] = frozenset({
    # ADR-030 · pre-auth · sin auth no se puede autenticar
    "/api/v1/auth/login",
    # ADR-030 · WebAuthn pre-cookie verify · cliente NO tiene session aún
    "/api/v1/auth/webauthn/verify",
    # ADR-030 · TOTP pre-cookie verify · cliente NO tiene session aún
    "/api/v1/auth/totp/verify",
    # ADR-030 · client portal pre-auth · login flow ClientUser
    "/api/v1/client-auth/login",
    # ADR-030 · healthcheck público estándar · monitoring/k8s probes
    "/api/v1/health",
    # H49 fix (TODO-RBAC sub-bloque RBAC.B): m12 magic-links/consume es POST
    # con token en body (no en URL path). El whitelist 4.D usaba prefix
    # ``/api/v1/magic-links/consume/`` con slash trailing → no matchea
    # ``POST /api/v1/magic-links/consume`` exact → endpoint público
    # bloqueado por global dep desde 4.D.
    "/api/v1/magic-links/consume",
    # H51 fix (TODO-RBAC sub-bloque RBAC.C): m16_onboarding /consume es
    # endpoint público token-based (magic link). Cliente recibe session_secret
    # tras consumir y lo usa después en /me/* via headers x-onboarding-* (NO
    # cookie). Bug pre-existente desde 4.D similar a H49.
    "/api/v1/onboarding/consume",
    # H54 fix (10.C audit cross-motor): m16 onboarding /lms/courses catalogo
    # publico de cursos LMS (sin respuestas). Docstring explicito. Bug
    # pre-existente desde 4.D.
    "/api/v1/onboarding/lms/courses",
    # H53 fix (10.C audit cross-motor): m07_evidence /public-key es endpoint
    # PUBLICO sin auth para verificacion firmas Ed25519 por clientes externos.
    # Refactor arquitectonico: endpoint movido a public_router.py sin
    # dependencies router-level + entrada whitelist global_dep.
    "/api/v1/evidence/public-key",
    # SAN-B.MB-7.4 (ADR-030 criterio 4): auth /public-key endpoint público
    # devuelve clave Ed25519 PEM para auditor externo verificar firmas FULKRO
    # sin acceso al sistema (artefactos M07/M25/M26/M14).
    "/api/v1/auth/public-key",
    # SAN-B.MB-7.4 (ADR-030 criterio 4): auth /verify-signature endpoint público
    # oracle verificación payload+signature contra clave FULKRO · alternativa
    # cliente sin libs cripto.
    "/api/v1/auth/verify-signature",
    # HIGH #7 · Trust Center público (m_compliance_monitor/public_api · prefix
    # /legal). La página anónima /trust consume el estado de compliance live;
    # devolvía 401. m_legal usa /legal-obligations (distinto), así que estos 2
    # exactos NO exponen nada admin.
    "/api/v1/legal/compliance/status",
    "/api/v1/legal/sub-processor-notifications/subscribe",
    # ADR-030 · OpenAPI schema público estándar · FastAPI auto-generated
    "/openapi.json",
    # ADR-030 · Swagger UI público estándar · FastAPI auto-generated
    "/docs",
    # ADR-030 · ReDoc UI público estándar · FastAPI auto-generated
    "/redoc",
})

WHITELIST_PREFIX: tuple[str, ...] = (
    "/api/v1/public/",            # m08 verification public portals (token-based)
    "/api/v1/_dev/",              # gated is_production=False (defensa redundante)
    "/api/v1/onboarding/me/",     # m16 cliente token-based (x-onboarding-session headers)
    # H52 fix (TODO-RBAC sub-bloque RBAC.D - 10.C): m12 magic-links/by-token/{token}
    # es GET publico pre-consume (sign-flows). Frontend abre /sign/{token} ->
    # useMagicLinkStatus llama /by-token -> debe retornar 200/404, NUNCA 401.
    # Bug pre-existente desde 4.D similar a H49 (consume) y H51 (onboarding consume).
    "/api/v1/magic-links/by-token/",
    # Sim MEDIO E2E fix: #43 firma de CONTRATO por magic-link público
    # (/contract-signing/{preview,confirm}). La credencial es el token +
    # OTP validados DENTRO del endpoint (ContractSigningFlow), NO una sesión.
    # Defecto latente: fase_43 siempre saltaba → nunca se ejerció el confirm →
    # un lead real firmando su contrato recibía 401 (auth global sin sesión).
    "/api/v1/contract-signing/",
    # H54 fix continuacion: catalogo LMS individual /lms/courses/{codigo}.
    "/api/v1/onboarding/lms/courses/",
    # audit-roundup 2026-06-16: consentimiento de cookies PUBLICO (visitantes
    # anonimos de fulkro.es · m_compliance/cookies_api · /consent GET+POST +
    # /revoke). Sin esto, el banner anonimo recibia 401 en la middleware ANTES
    # de llegar al handler (los tests pasaban porque el client de test lleva
    # sesion → enmascaraba el requisito publico). Exime tambien CSRF, necesario
    # para el POST cross-origin fulkro.es→app.fulkro.es. La credencial es el
    # anonymous_session_id generado por el cliente; no expone dato cross-tenant.
    "/api/v1/legal/cookies/",
    "/docs/",                     # Swagger assets (CSS, JS)
    "/redoc/",                    # ReDoc assets
)


def _is_whitelisted(path: str) -> bool:
    """Path bypassa auth check (login pre-auth, public, dev, docs)."""
    if path in WHITELIST_EXACT:
        return True
    return any(path.startswith(prefix) for prefix in WHITELIST_PREFIX)


# ────────────────────────────────────────────────────────────────────
# AuthSubject wrapper
# ────────────────────────────────────────────────────────────────────


class AuthSubject:
    """User authenticated wrapper (Marcos OR ClientUser).

    Disponible en ``request.state.auth_subject`` para endpoints
    downstream que necesiten distinguir pool sin re-resolver.

    Attributes:
        user: ``User`` (pool Marcos) o ``ClientUser`` (pool cliente).
        role_pool: ``"marcos"`` o ``"cliente"`` — origen del JWT.
        email: email del user (común a ambos pools).
    """

    __slots__ = ("user", "role_pool", "email")

    def __init__(self, user: User | ClientUser, role_pool: str) -> None:
        self.user = user
        self.role_pool = role_pool
        self.email = user.email


# ────────────────────────────────────────────────────────────────────
# Authentication dispatch
# ────────────────────────────────────────────────────────────────────


async def authenticate_request(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Optional[AuthSubject]:
    """Global dep: dispatcher dual + CSRF + set_config audit user.

    Lógica:
      1. Whitelist check → return None (endpoint público).
      2. Cookie ``fulkro_session`` requerida → 401 si ausente.
      3. JWT decode (Ed25519 común a ambos pools) → 401 si inválido.
      4. Peek ``payload.sub``:
           - prefijo ``"client:"`` → pool cliente (verify_session m21).
           - else → pool Marcos (session_is_active + get_user).
      5. CSRF triple binding (mutating methods): ``verify_csrf``.
      6. ``SET app.current_user = user.email`` para fn_audit_track triggers.
      7. ``request.state.auth_subject`` populated para downstream.
    """
    path = request.url.path

    if _is_whitelisted(path):
        return None

    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    try:
        payload = crypto.decode_token(token)
    except pyjwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session token",
        ) from exc

    if payload.get("typ") != "session":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Wrong token type",
        )

    sub = payload.get("sub")
    if not sub or not isinstance(sub, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token subject",
        )

    if sub.startswith("client:"):
        user, _session = await _authenticate_cliente(db, token)
        role_pool = "cliente"
    else:
        user = await _authenticate_marcos(db, payload, sub)
        role_pool = "marcos"

    # Acceso de soporte READ-ONLY (impersonation admin → portal cliente).
    # CHOKEPOINT app-level (esta dep corre en TODAS las rutas no-exentas, antes
    # que cualquier endpoint) → cubre TODA la superficie mutating del portal
    # cliente: ambas deps (get_current_client_user + require_client_user) y
    # cualquier endpoint cliente futuro, sin lista que se quede incompleta.
    # Una sesión de soporte lleva claim ``support=true`` (acuñado por
    # auth_service.mint_support_session); SOLO puede métodos seguros (GET/HEAD/
    # OPTIONS). Cualquier método mutating → 403, ANTES de tocar el endpoint.
    # ÚNICA excepción (allow): la propia sesión puede hacer logout para SALIR de
    # soporte (auto-terminación · NO es mutación de datos del cliente · emite
    # support.access.ended). El resto de la superficie mutating sigue bloqueada.
    if (
        role_pool == "cliente"
        and payload.get("support") is True
        and request.method.upper() not in SAFE_METHODS
        and request.url.path != _SUPPORT_SELF_LOGOUT_PATH
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="support_access_read_only",
        )

    # CSRF triple binding (no-op para SAFE_METHODS).
    verify_csrf(request, payload)

    # Audit user wiring para fn_audit_track triggers (TODO-AUDIT-USER-BACKFILL-001
    # PARTIAL RESOLVED → ahora completo via global dep).
    await db.execute(
        text("SELECT set_config('app.current_user', :usr, true)"),
        {"usr": user.email},
    )

    auth_subject = AuthSubject(user=user, role_pool=role_pool)
    request.state.auth_subject = auth_subject
    # Compatibilidad con call sites pre-4.D que leen ``request.state.auth_payload``
    # (e.g. auth/api.py::logout extrae jti para revocar sesión).
    request.state.auth_payload = payload
    return auth_subject


async def _authenticate_marcos(
    db: AsyncSession,
    payload: dict[str, Any],
    sub: str,
) -> User:
    """Pool Marcos: session_is_active(jti) + get_user(uuid)."""
    try:
        user_uuid = uuid.UUID(sub)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed Marcos subject",
        ) from exc

    jti = payload.get("jti")
    if not jti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing jti",
        )

    db_session: MarcosSession | None = await auth_service_marcos.session_is_active(
        db, jti,
    )
    if db_session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session revoked or expired",
        )

    user = await auth_service_marcos.get_user(db, user_uuid)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return user


async def _authenticate_cliente(
    db: AsyncSession,
    token: str,
) -> tuple[ClientUser, Any]:
    """Pool cliente: m21 ``verify_session(db, token)``.

    Pasa el ``token`` raw porque ``verify_session`` decodifica
    internamente (usa ``decode_token`` igual que el global dep).
    Doble decodificación es ~40μs total, aceptable; alternativa
    pasar payload requeriría refactor m21 fuera scope 4.D.
    """
    try:
        return await auth_service_cliente.verify_session(db, token)
    except auth_service_cliente.AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Client session: {exc}",
        ) from exc
