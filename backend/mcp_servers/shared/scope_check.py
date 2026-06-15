"""Scope enforcer client. Every tool calls check_scope() BEFORE executing.

FAIL-CLOSED: any error returns allowed=False.

§1.7 hardening (2026-06-15):
- Extracción de host IPv6-aware (antes ``split(":")[0]`` rompía ``[2001:db8::1]:443``).
- Exclusiones con soporte CIDR (antes sólo igualdad de IP exacta → un excluido
  ``10.0.0.0/8`` se ignoraba en silencio y el target dentro del rango pasaba).
- Verificación de la firma HMAC del authorization (``PENTEST_AUTHORIZATION_SIG``):
  antes se generaba pero NUNCA se verificaba (firma decorativa). Ahora, si hay
  firma, se valida fail-closed contra la app_secret_key.
"""
import ipaddress
import json
import os
from datetime import datetime, timezone


_AUTHORIZATION: dict | None = None


def _verify_signature(auth: dict, signature: str) -> bool:
    """Verifica la firma HMAC del authorization. Fail-closed si no se puede.

    Import perezoso de ``verify_authorization`` (vive en backend.app · el flujo
    real corre in-process). Si no es importable (contenedor MCP aislado sin
    backend) devolvemos False → fail-closed (no se confía en una firma que no se
    puede comprobar).
    """
    try:
        from backend.app.motors.m08_verification.autopilot.ephemeral_connector import (
            verify_authorization,
        )
        return verify_authorization(auth, signature)
    except Exception:
        return False


def load_authorization() -> dict:
    """Load authorization from env var or file (verificando firma si la hay)."""
    global _AUTHORIZATION
    if _AUTHORIZATION:
        return _AUTHORIZATION

    auth_json = os.environ.get("PENTEST_AUTHORIZATION", "")
    if auth_json:
        auth = json.loads(auth_json)
        sig = os.environ.get("PENTEST_AUTHORIZATION_SIG", "")
        if sig and not _verify_signature(auth, sig):
            # Firma presente pero inválida/no verificable → fail-closed.
            return {}
        _AUTHORIZATION = auth
        return _AUTHORIZATION

    auth_file = os.environ.get("PENTEST_AUTHORIZATION_FILE", "/app/authorization.json")
    if os.path.exists(auth_file):
        with open(auth_file) as f:
            _AUTHORIZATION = json.load(f)
        return _AUTHORIZATION

    return {}


def extract_host(target: str) -> str:
    """Extrae el host de ``target``, soportando ``[IPv6]:port`` e ``IPv4:port``.

    - ``[2001:db8::1]:8080`` -> ``2001:db8::1``
    - ``10.0.0.1:443``       -> ``10.0.0.1``
    - ``example.com:8443``   -> ``example.com``
    - ``2001:db8::1``        -> ``2001:db8::1`` (IPv6 sin corchetes ni puerto)
    """
    t = (target or "").strip()
    if t.startswith("["):
        end = t.rfind("]")
        if end != -1:
            return t[1:end]
    # IPv6 sin corchetes (varios ":") → no es host:port, devolver tal cual.
    if t.count(":") > 1:
        return t
    # IPv4/hostname con puerto opcional.
    if ":" in t:
        host, _, port = t.rpartition(":")
        if port.isdigit():
            return host
    return t


def evaluate_target_scope(target: str, targets: list, excluded: list) -> dict:
    """Decide allowed/denied de ``target`` contra targets+excluded (default deny).

    Soporta CIDR (IPv4/IPv6), IP exacta y dominios (wildcard ``*.dominio``).
    Compartido por ``check_scope`` y ``ScopeEnforcer`` (DRY).
    """
    target_clean = extract_host(target)

    # --- Exclusiones (tienen prioridad) · CIDR + IP exacta + dominio ---
    for excl in excluded:
        try:
            net = ipaddress.ip_network(excl, strict=False)
            if ipaddress.ip_address(target_clean) in net:
                return {"allowed": False, "reason": f"Target {target} is excluded"}
            continue
        except ValueError:
            pass
        if target_clean.lower() == str(excl).lower():
            return {"allowed": False, "reason": f"Target {target} is excluded"}

    # --- Targets autorizados · CIDR + dominio exacto/wildcard ---
    for allowed_target in targets:
        try:
            net = ipaddress.ip_network(allowed_target, strict=False)
            if ipaddress.ip_address(target_clean) in net:
                return {"allowed": True, "reason": "IP in authorized network"}
        except ValueError:
            pass

        allowed_lower = str(allowed_target).lower()
        target_lower = target_clean.lower()
        if allowed_lower.startswith("*."):
            base = allowed_lower[2:]
            if target_lower == base or target_lower.endswith("." + base):
                return {"allowed": True, "reason": "Domain matches wildcard"}
        elif target_lower == allowed_lower:
            return {"allowed": True, "reason": "Domain exact match"}

    return {
        "allowed": False,
        "reason": f"Target {target} not in authorized scope: {targets}",
    }


def check_scope(target: str, test_type: str = "scan") -> dict:
    """Verify whether target is authorized for the given test type.

    Returns: {"allowed": bool, "reason": str}. FAIL-CLOSED on any exception.
    """
    try:
        auth = load_authorization()
        if not auth:
            return {"allowed": False, "reason": "No authorization loaded (fail-closed)"}

        now = datetime.now(timezone.utc)
        window_start = datetime.fromisoformat(
            auth.get("window_start", "2000-01-01T00:00:00+00:00")
        )
        window_end = datetime.fromisoformat(
            auth.get("window_end", "2099-12-31T23:59:59+00:00")
        )
        if not (window_start <= now <= window_end):
            return {
                "allowed": False,
                "reason": f"Outside time window: {window_start} - {window_end}",
            }

        allowed_types = auth.get("allowed_test_types", [])
        if allowed_types and test_type not in allowed_types:
            return {
                "allowed": False,
                "reason": f"Test type '{test_type}' not allowed. Allowed: {allowed_types}",
            }

        return evaluate_target_scope(
            target, auth.get("targets", []), auth.get("excluded_targets", []),
        )
    except Exception as exc:
        return {"allowed": False, "reason": f"Scope check error (fail-closed): {exc}"}
