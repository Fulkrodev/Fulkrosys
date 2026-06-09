"""Scope enforcer client. Every tool calls check_scope() BEFORE executing.

FAIL-CLOSED: any error returns allowed=False.
"""
import ipaddress
import json
import os
from datetime import datetime, timezone


_AUTHORIZATION: dict | None = None


def load_authorization() -> dict:
    """Load authorization from env var or file."""
    global _AUTHORIZATION
    if _AUTHORIZATION:
        return _AUTHORIZATION

    auth_json = os.environ.get("PENTEST_AUTHORIZATION", "")
    if auth_json:
        _AUTHORIZATION = json.loads(auth_json)
        return _AUTHORIZATION

    auth_file = os.environ.get("PENTEST_AUTHORIZATION_FILE", "/app/authorization.json")
    if os.path.exists(auth_file):
        with open(auth_file) as f:
            _AUTHORIZATION = json.load(f)
        return _AUTHORIZATION

    return {}


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

        targets = auth.get("targets", [])
        excluded = auth.get("excluded_targets", [])

        target_clean = target.split(":")[0]

        for excl in excluded:
            try:
                if ipaddress.ip_address(target_clean) == ipaddress.ip_address(excl):
                    return {"allowed": False, "reason": f"Target {target} is excluded"}
            except ValueError:
                if target_clean.lower() == excl.lower():
                    return {"allowed": False, "reason": f"Target {target} is excluded"}

        for allowed_target in targets:
            try:
                net = ipaddress.ip_network(allowed_target, strict=False)
                ip = ipaddress.ip_address(target_clean)
                if ip in net:
                    return {"allowed": True, "reason": "IP in authorized network"}
            except ValueError:
                pass

            allowed_lower = allowed_target.lower()
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
    except Exception as exc:
        return {"allowed": False, "reason": f"Scope check error (fail-closed): {exc}"}
