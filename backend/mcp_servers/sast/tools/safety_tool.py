"""Tool: safety_audit — Python dependency audit."""
import json

from shared.mcp_protocol import MCPTool
from shared.utils import run_command


TOOL = MCPTool(
    name="safety_audit",
    description="PyUp Safety: audit Python dependencies for known vulnerabilities.",
    input_schema={
        "properties": {
            "requirements": {"type": "string", "description": "Path to requirements.txt"},
        },
        "required": ["requirements"],
    },
    timeout_seconds=300,
    risk_level="low",
    ens_measures=["mp.sw.2"],
)


async def safety_audit(requirements: str) -> dict:
    """Scope: local audit — no external target, scope check not applicable."""
    cmd = ["safety", "check", "-r", requirements, "--json"]
    result = await run_command(cmd, timeout=TOOL.timeout_seconds)
    findings = []
    try:
        data = json.loads(result["stdout"] or "[]")
        findings = data if isinstance(data, list) else data.get("vulnerabilities", [])
    except json.JSONDecodeError:
        pass
    return {"requirements": requirements, "command": result["command"], "findings": findings}
