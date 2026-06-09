"""Tool: subfinder_enum — ProjectDiscovery subdomain enumerator."""
from shared.mcp_protocol import MCPTool
from shared.scope_check import check_scope
from shared.utils import parse_jsonl, run_command


TOOL = MCPTool(
    name="subfinder_enum",
    description="Fast passive subdomain enumeration via subfinder.",
    input_schema={
        "properties": {"domain": {"type": "string"}},
        "required": ["domain"],
    },
    timeout_seconds=600,
    risk_level="low",
    ens_measures=["op.exp.1"],
)


async def subfinder_enum(domain: str) -> dict:
    scope = check_scope(domain, "enumerate")
    if not scope["allowed"]:
        return {"error": f"SCOPE DENIED: {scope['reason']}", "findings": []}
    cmd = ["subfinder", "-d", domain, "-json", "-silent"]
    result = await run_command(cmd, timeout=TOOL.timeout_seconds)
    findings = parse_jsonl(result["stdout"])
    return {"domain": domain, "command": result["command"], "findings": findings}
