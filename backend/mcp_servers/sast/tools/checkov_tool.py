"""Tool: checkov_scan — Bridgecrew/Prisma Checkov IaC scan."""
import json

from shared.mcp_protocol import MCPTool
from shared.utils import run_command


TOOL = MCPTool(
    name="checkov_scan",
    description="Checkov IaC scanner (Terraform, CloudFormation, Kubernetes, Dockerfile).",
    input_schema={
        "properties": {
            "directory": {"type": "string"},
            "framework": {"type": "string"},
        },
        "required": ["directory"],
    },
    timeout_seconds=1800,
    risk_level="low",
    ens_measures=["mp.sw.1", "op.nub.1"],
)


async def checkov_scan(directory: str, framework: str | None = None) -> dict:
    """Scope: local audit — no external target, scope check not applicable."""
    cmd = ["checkov", "-d", directory, "-o", "json"]
    if framework:
        cmd += ["--framework", framework]
    result = await run_command(cmd, timeout=TOOL.timeout_seconds)
    data: dict | list = {}
    try:
        data = json.loads(result["stdout"] or "{}")
    except json.JSONDecodeError:
        data = {}
    return {"directory": directory, "command": result["command"], "data": data}
