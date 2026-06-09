"""Tool: spiderfoot_osint — SpiderFoot automated OSINT scan."""
from shared.mcp_protocol import MCPTool
from shared.scope_check import check_scope
from shared.utils import parse_csv_output, run_command


TOOL = MCPTool(
    name="spiderfoot_osint",
    description="SpiderFoot OSINT scan: domains, emails, IPs, leaks across 200+ modules.",
    input_schema={
        "properties": {
            "target": {"type": "string"},
            "scan_type": {"type": "string", "default": "all"},
        },
        "required": ["target"],
    },
    timeout_seconds=1800,
    risk_level="low",
    ens_measures=["op.exp.1"],
)


async def spiderfoot_osint(target: str, scan_type: str = "all") -> dict:
    scope = check_scope(target, "enumerate")
    if not scope["allowed"]:
        return {"error": f"SCOPE DENIED: {scope['reason']}"}
    cmd = ["spiderfoot", "-s", target, "-t", scan_type, "-q"]
    result = await run_command(cmd, timeout=TOOL.timeout_seconds)
    findings: list = []
    try:
        findings = parse_csv_output(result["stdout"])
    except Exception:
        findings = []
    return {"target": target, "command": result["command"], "findings": findings}
