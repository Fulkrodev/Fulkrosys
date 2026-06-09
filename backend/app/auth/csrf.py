"""CSRF triple binding helper centralizado.

Antes de sub-fase 4.D, este pattern estaba inline en:
- ``auth/dependencies.py::get_current_user`` (Marcos pool)
- ``motors/m21_portal_cliente/api.py::get_current_client_user`` (Cliente pool)

Centralización extraída en sub-fase 4.D.1 (TODO-MOTORS-AUTH-LANDING-001
RESOLVE) para que el global dep ``authenticate_request`` lo use
uniformemente sobre ambos pools — y para que motors nuevos hereden
CSRF protection automáticamente al pasar por el global dep.

ADR-019 (CSRF triple binding) + ADR-021 (motors auth strategy).
"""
from __future__ import annotations

from fastapi import HTTPException, Request, status

from backend.app.auth import crypto


# Constants alineadas con auth/dependencies.py + m21/api.py existing.
SESSION_COOKIE = "fulkro_session"
CSRF_COOKIE = "fulkro_csrf"
CSRF_HEADER = "x-csrf-token"
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def verify_csrf(request: Request, payload: dict) -> None:
    """Triple binding CSRF check.

    Mutating methods (POST/PATCH/PUT/DELETE) deben presentar:
    1. Header ``x-csrf-token``
    2. Cookie ``fulkro_csrf``
    3. JWT claim ``csrf``

    Los tres deben coincidir (header == JWT claim == cookie, transitividad
    via JWT como pivote para mantener pattern existing).

    Idempotente para SAFE_METHODS (GET/HEAD/OPTIONS): no-op.

    Raises:
        HTTPException 403 si cualquier token ausente o mismatch.
    """
    if request.method.upper() in SAFE_METHODS:
        return

    header_token = request.headers.get(CSRF_HEADER)
    cookie_token = request.cookies.get(CSRF_COOKIE)
    payload_csrf = payload.get("csrf")

    if (
        not header_token
        or not cookie_token
        or not payload_csrf
        or not crypto.constant_time_eq(header_token, payload_csrf)
        or not crypto.constant_time_eq(cookie_token, payload_csrf)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="csrf token mismatch",
        )
