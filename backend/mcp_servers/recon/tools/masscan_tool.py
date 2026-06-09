"""Tool: masscan_sweep — Fast Internet-scale port scanner."""
import json

from shared.mcp_protocol import MCPTool
from shared.scope_check import check_scope
from shared.utils import run_command


TOOL = MCPTool(
    name="masscan_sweep",
    description="Masscan port sweep at configurable packet rate. Ideal for large ranges.",
    input_schema={
        "properties": {
            "target": {"type": "string"},
            "ports": {"type": "string", "default": "1-65535"},
            "rate": {"type": "integer", "default": 1000},
        },
        "required": ["target"],
    },
    timeout_seconds=1800,
    risk_level="low",
    ens_measures=["op.exp.1"],
)


async def masscan_sweep(target: str, ports: str = "1-65535", rate: int = 1000) -> dict:
    scope = check_scope(target, "scan")
    if not scope["allowed"]:
        return {"error": f"SCOPE DENIED: {scope['reason']}", "findings": []}

    cmd = ["masscan", target, "-p", ports, "--rate", str(rate), "-oJ", "-"]
    result = await run_command(cmd, timeout=TOOL.timeout_seconds)
    if result["returncode"] != 0 and not result["stdout"]:
        return {"error": result["stderr"][:2000], "command": result["command"], "findings": []}

    findings = []
    try:
        findings = json.loads(result["stdout"] or "[]")
    except json.JSONDecodeError:
        findings = []
    return {
        "target": target,
        "command": result["command"],
        "findings": findings,
        "summary": {"total": len(findings)},
    }
