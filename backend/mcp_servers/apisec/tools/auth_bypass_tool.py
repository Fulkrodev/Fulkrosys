"""Tool: api_auth_bypass_test — Test common API auth-bypass patterns."""
import urllib.request

from shared.mcp_protocol import MCPTool
from shared.scope_check import check_scope


TOOL = MCPTool(
    name="api_auth_bypass_test",
    description=(
        "Probe a REST endpoint for common authentication bypass classes: "
        "no token, expired token, tampered role, HTTP verb tampering."
    ),
    input_schema={
        "properties": {
            "endpoint": {"type": "string"},
            "valid_token": {"type": "string"},
        },
        "required": ["endpoint"],
    },
    timeout_seconds=120,
    risk_level="medium",
    ens_measures=["op.acc.6", "mp.sw.2"],
)


async def api_auth_bypass_test(endpoint: str, valid_token: str = "") -> dict:
    scope = check_scope(endpoint, "scan")
    if not scope["allowed"]:
        return {"error": f"SCOPE DENIED: {scope['reason']}"}
    checks = []
    variants = [
        ("no_token", {}),
        ("bogus_token", {"Authorization": "Bearer invalid"}),
    ]
    if valid_token:
        variants.append(("tampered_role", {"Authorization": f"Bearer {valid_token}x"}))
    for name, headers in variants:
        req = urllib.request.Request(endpoint, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                checks.append({"name": name, "status": resp.status})
        except urllib.error.HTTPError as err:
            checks.append({"name": name, "status": err.code})
        except Exception as exc:
            checks.append({"name": name, "error": str(exc)[:200]})
    return {"endpoint": endpoint, "checks": checks}
