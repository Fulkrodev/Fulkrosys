"""Conector efímero · zero standing access time-boxed (doc §2 + §15).

Fulkro NO guarda acceso permanente god-mode a la infra del cliente. Cada
engagement abre una sesión efímera: scoped, least-privilege, time-boxed a la
ventana, con authorization.json firmado (HMAC) que los MCP servers validan
(scope_enforcer fail-closed), y que se REVOCA sola al cerrar o al caducar.

Reutiliza las columnas `ephemeral_*` de verification_runs (Fase 1) + el
scope ya derivado (scope_deriver). La firma HMAC con app_secret_key evita
tampering del authorization.json en tránsito hacia el conector.

Determinista salvo la generación del session_id (uuid4) y el reloj (now
inyectable para tests).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.app.config import get_settings

DEFAULT_TTL_MINUTES = 8 * 60  # ventana típica de engagement nocturno


def _secret() -> bytes:
    try:
        return get_settings().app_secret_key.get_secret_value().encode("utf-8")
    except Exception:  # pragma: no cover
        return b"fulkro-dev"


def build_authorization_json(
    run: Any,
    scope: dict[str, Any] | None = None,
    *,
    session_id: str,
    expires_at: datetime,
) -> dict[str, Any]:
    """Construye el authorization.json que consumen los MCP servers.

    Shape alineado con `scope_check`/`ScopeEnforcer`: window_start/window_end
    (ISO), allowed_test_types, targets, excluded_targets.
    """
    scope = scope or (run.scope_jsonb or {})
    targets = list(scope.get("targets") or [])
    web = scope.get("web_apps") or []
    # web_apps son URLs → añadimos sus hosts a targets de scope
    targets_all = sorted(set(targets) | {str(u) for u in web})
    return {
        "session_id": session_id,
        "window_start": (run.scheduled_start or datetime.now(timezone.utc)).isoformat()
        if getattr(run, "scheduled_start", None)
        else datetime.now(timezone.utc).isoformat(),
        "window_end": expires_at.isoformat(),
        "allowed_test_types": scope.get("allowed_test_types")
        or ["scan", "config_audit", "active_safe"],
        "targets": targets_all,
        "excluded_targets": list(scope.get("exclusions") or []),
        "category": scope.get("category") or getattr(run, "category", None),
    }


def sign_authorization(authorization: dict[str, Any]) -> str:
    """HMAC-SHA256 del authorization.json canónico (anti-tampering)."""
    canonical = json.dumps(authorization, sort_keys=True, separators=(",", ":"))
    return hmac.new(_secret(), canonical.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_authorization(authorization: dict[str, Any], signature: str) -> bool:
    return hmac.compare_digest(sign_authorization(authorization), signature)


def create_ephemeral_session(
    run: Any,
    scope: dict[str, Any] | None = None,
    *,
    ttl_minutes: int = DEFAULT_TTL_MINUTES,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Abre una sesión efímera sobre el run (muta run.ephemeral_*).

    Devuelve {session_id, authorization, signature, expires_at}. El caller
    persiste el run y entrega authorization+signature al conector/MCP.
    """
    now = now or datetime.now(timezone.utc)
    session_id = str(uuid.uuid4())
    expires_at = now + timedelta(minutes=ttl_minutes)
    run.ephemeral_session_id = uuid.UUID(session_id)
    run.ephemeral_expires_at = expires_at
    run.ephemeral_revoked_at = None
    authorization = build_authorization_json(
        run, scope, session_id=session_id, expires_at=expires_at,
    )
    signature = sign_authorization(authorization)
    return {
        "session_id": session_id,
        "authorization": authorization,
        "signature": signature,
        "expires_at": expires_at,
    }


def revoke_ephemeral_session(run: Any, *, now: datetime | None = None) -> None:
    """Revoca la sesión efímera (zero standing access · doc §2)."""
    run.ephemeral_revoked_at = now or datetime.now(timezone.utc)


def is_session_active(run: Any, *, now: datetime | None = None) -> bool:
    """True si hay sesión efímera vigente (no revocada, no caducada)."""
    if not getattr(run, "ephemeral_session_id", None):
        return False
    if getattr(run, "ephemeral_revoked_at", None) is not None:
        return False
    expires = getattr(run, "ephemeral_expires_at", None)
    if expires is None:
        return False
    now = now or datetime.now(timezone.utc)
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    return now < expires
