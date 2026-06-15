"""ScopeEnforcer — validates a target/test_type pair against a signed authorization.

Fail-closed: any unexpected state denies the call.

La lógica de matching (host IPv6-aware + CIDR + dominio) es ÚNICA en
``shared.scope_check.evaluate_target_scope`` (DRY · §1.7) — antes estaba
duplicada aquí y divergía (sin CIDR en exclusiones, IPv6 roto por split).
"""
from datetime import datetime, timezone

try:  # MCP runtime (backend/mcp_servers en sys.path)
    from shared.scope_check import evaluate_target_scope
except ImportError:  # importado como paquete desde el backend/tests
    from backend.mcp_servers.shared.scope_check import evaluate_target_scope


class ScopeEnforcer:
    """Stateful scope validator used by the scope-enforcer MCP server."""

    def __init__(self, authorization: dict):
        self.authorization = authorization or {}

    def check(self, target: str, test_type: str = "scan") -> dict:
        """Return ``{"allowed": bool, "reason": str}`` for the given request."""
        try:
            auth = self.authorization
            if not auth:
                return {"allowed": False, "reason": "Empty authorization (fail-closed)"}

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
                target,
                auth.get("targets", []),
                auth.get("excluded_targets", []),
            )
        except Exception as exc:
            return {"allowed": False, "reason": f"Scope check error (fail-closed): {exc}"}
