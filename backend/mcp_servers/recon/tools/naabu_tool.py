"""Tool: naabu_portscan — Fast port scanner by ProjectDiscovery."""
from shared.mcp_protocol import MCPTool
from shared.scope_check import check_scope
from shared.utils import parse_jsonl, run_command


TOOL = MCPTool(
    name="naabu_portscan",
    description="Naabu: fast TCP port scanner with JSONL output.",
    input_schema={
        "properties": {"target": {"type": "string"}},
        "required": ["target"],
    },
    timeout_seconds=900,
    risk_level="low",
    ens_measures=["op.exp.1"],
)


async def naabu_portscan(target: str) -> dict:
    scope = check_scope(target, "scan")
    if not scope["allowed"]:
        return {"error": f"SCOPE DENIED: {scope['reason']}", "findings": []}
    cmd = ["naabu", "-host", target, "-json", "-silent"]
    result = await run_command(cmd, timeout=TOOL.timeout_seconds)
    findings = parse_jsonl(result["stdout"])
    return {"target": target, "command": result["command"], "findings": findings}
