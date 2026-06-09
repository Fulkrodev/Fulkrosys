"""FastAPI dependencies for role-based authorization.

Sub-fase 4.D ADR-021: la autenticación (cookie lookup + JWT decode +
session validation + CSRF triple binding + ``set_config('app.current_user')``)
está centralizada en ``backend/app/auth/global_dep.py::authenticate_request``,
wired como global dependency en ``main.py``. Las dependencies de este
módulo asumen que el global dep ya corrió y populó
``request.state.auth_subject``.

Estas dependencies sólo hacen **role check** sobre el ``AuthSubject``
ya inyectado, sin re-resolver cookies ni queries DB.

ADR-013 (separación 3 portales) + ADR-015 (role vs capability) +
ADR-019 (CSRF triple binding) + ADR-021 (motors auth strategy).
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from backend.app.auth.csrf import (
    CSRF_COOKIE,
    CSRF_HEADER,
    SAFE_METHODS,
    SESSION_COOKIE,
)
from backend.app.auth.global_dep import AuthSubject
from backend.app.models.auth import User

# Re-export constants para compatibilidad con call sites pre-4.D
# (e.g. auth/api.py importa CSRF_COOKIE/SESSION_COOKIE para set_cookie).
__all__ = [
    "CSRF_COOKIE",
    "CSRF_HEADER",
    "SAFE_METHODS",
    "SESSION_COOKIE",
    "CurrentUser",
    "get_current_user",
    "require_client_user",
    "require_marcos_or_client",
    "require_owner",
]


def _get_auth_subject(request: Request) -> AuthSubject:
    """Lookup ``request.state.auth_subject`` o 401.

    Si el global dep no se ejecutó (e.g. path en whitelist o test sin
    override fixture), no hay subject → 401. Esto NO debería ocurrir en
    runtime salvo bug en wiring.
    """
    auth_subject = getattr(request.state, "auth_subject", None)
    if auth_subject is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return auth_subject


async def get_current_user(request: Request) -> User:
    """Retorna el ``User`` Marcos autenticado.

    Falla con 401 si el subject pertenece al pool cliente (los endpoints
    que usan ``CurrentUser`` están diseñados para Marcos / owner).
    Para endpoints multi-pool, leer ``request.state.auth_subject`` directamente
    e inspeccionar ``role_pool``.
    """
    subject = _get_auth_subject(request)
    if subject.role_pool != "marcos":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Marcos session required",
        )
    return subject.user  # type: ignore[return-value]


CurrentUser = Annotated[User, Depends(get_current_user)]


# ──────────────────────────────────────────────────────────────────────
# Role-based dependencies (ADR-013 + ADR-015)
#
# Estas dependencies validan contra ``user.role`` (BD), NO contra los
# claims del JWT. Razón: defensa en profundidad. El JWT vive según
# ``SESSION_TTL`` (15-60 min); si Marcos degrada un usuario de owner a
# client_user en BD, el cambio surte efecto inmediato sin esperar la
# expiración del token viejo. Los claims JWT son útiles para el
# frontend (que no consulta BD), pero el backend siempre vuelve a la
# fuente de verdad.
# ──────────────────────────────────────────────────────────────────────


async def require_owner(user: CurrentUser) -> User:
    """403 si el usuario autenticado no tiene ``role == 'owner'``."""
    if user.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso restringido a owners",
        )
    return user


async def require_client_user(request: Request) -> User:
    """403 si el subject NO pertenece al pool cliente.

    Distinto a ``require_owner``: aquí esperamos un ``ClientUser`` (pool
    cliente), no un ``User`` (Marcos). Lookup desde ``auth_subject``
    directamente para evitar que ``get_current_user`` rechace al cliente.
    """
    subject = _get_auth_subject(request)
    if subject.role_pool != "cliente":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso restringido a usuarios cliente",
        )
    return subject.user  # type: ignore[return-value]


async def require_marcos_or_client(request: Request):
    """Auth chain: cualquier usuario válido (Marcos OR cliente).

    Para endpoints Cat C (TODO-RBAC-PER-ENDPOINT-001) compartidos por
    ambos pools. Ejemplos:
    - m07_evidence: cliente sube pruebas, Marcos lista/modera
    - m16_onboarding: Marcos prepara wizard, cliente interactúa via magic link
    - m20_workspace: cliente accede a su workspace, Marcos también
    - m24_idms: cliente firma documentos, Marcos crea/gestiona

    Auth ya hecha por ``authenticate_request`` global dep. Esta dep solo
    valida que el subject pertenezca a uno de los 2 pools (no a un pool
    futuro como ``auditor`` que podría introducirse).

    Returns:
        ``User`` (Marcos) o ``ClientUser`` (cliente). Type union sin enforce.
    """
    subject = _get_auth_subject(request)
    if subject.role_pool not in ("marcos", "cliente"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User pool not allowed",
        )
    return subject.user
