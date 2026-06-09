"""ScopeEnforcer — validates a target/test_type pair against a signed authorization.

Fail-closed: any unexpected state denies the call.
"""
import ipaddress
from datetime import datetime, timezone


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
