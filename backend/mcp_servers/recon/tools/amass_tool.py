"""Tool: amass_enum — OWASP Amass subdomain enumeration."""
from shared.mcp_protocol import MCPTool
from shared.scope_check import check_scope
from shared.utils import parse_jsonl, run_command


TOOL = MCPTool(
    name="amass_enum",
    description="OWASP Amass subdomain enumeration (passive OSINT or active DNS brute).",
    input_schema={
        "properties": {
            "domain": {"type": "string"},
            "mode": {"type": "string", "enum": ["passive", "active"], "default": "passive"},
        },
        "required": ["domain"],
    },
    timeout_seconds=1800,
    risk_level="low",
    ens_measures=["op.exp.1"],
)


async def amass_enum(domain: str, mode: str = "passive") -> dict:
    scope = check_scope(domain, "enumerate")
    if not scope["allowed"]:
        return {"error": f"SCOPE DENIED: {scope['reason']}", "findings": []}

    cmd = ["amass", "enum", "-d", domain, "-json", "/dev/stdout"]
    if mode == "passive":
        cmd.append("-passive")
    result = await run_command(cmd, timeout=TOOL.timeout_seconds)
    findings = parse_jsonl(result["stdout"])
    return {
        "domain": domain,
        "command": result["command"],
        "findings": findings,
        "summary": {"total": len(findings)},
    }
