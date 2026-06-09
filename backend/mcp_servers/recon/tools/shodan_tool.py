"""Tool: shodan_lookup — Shodan Host API lookup."""
import os

from shared.mcp_protocol import MCPTool
from shared.scope_check import check_scope


TOOL = MCPTool(
    name="shodan_lookup",
    description="Shodan Host API query to retrieve banners, ports, CVEs for an IP.",
    input_schema={
        "properties": {"target": {"type": "string"}},
        "required": ["target"],
    },
    timeout_seconds=60,
    risk_level="low",
    ens_measures=["op.exp.1"],
)


async def shodan_lookup(target: str) -> dict:
    scope = check_scope(target, "scan")
    if not scope["allowed"]:
        return {"error": f"SCOPE DENIED: {scope['reason']}"}

    api_key = os.environ.get("SHODAN_API_KEY", "")
    if not api_key:
        return {"error": "SHODAN_API_KEY not configured", "target": target}
    try:
        import shodan  # type: ignore
        api = shodan.Shodan(api_key)
        host = api.host(target)
    except Exception as exc:
        return {"error": str(exc)[:500], "target": target}
    return {"target": target, "host": host}
