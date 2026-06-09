"""Tool: kube_security_scan — kube-bench + kube-hunter Kubernetes security scan."""
import json

from shared.mcp_protocol import MCPTool
from shared.utils import run_command
from shared.scope_check import check_scope


TOOL = MCPTool(
    name="kube_security_scan",
    description="Run kube-bench (CIS benchmark) + kube-hunter against a Kubernetes cluster.",
    input_schema={
        "properties": {
            "mode": {"type": "string", "enum": ["bench", "hunter"], "default": "bench"},
            "target": {"type": "string", "default": "localhost"},
        }
    },
    timeout_seconds=1800,
    risk_level="low",
    ens_measures=["op.exp.2", "op.nub.1"],
)


async def kube_security_scan(mode: str = "bench", target: str = "localhost") -> dict:
    # Validates active engagement window, not target IP
    scope = check_scope("__local__", "config_audit")
    if not scope["allowed"]:
        return {"error": f"SCOPE DENIED: {scope['reason']}"}
    if mode == "bench":
        cmd = ["kube-bench", "--json"]
    else:
        cmd = ["kube-hunter", "--remote", target, "--report", "json"]
    result = await run_command(cmd, timeout=TOOL.timeout_seconds)
    try:
        data = json.loads(result["stdout"] or "{}")
    except json.JSONDecodeError:
        data = {"raw": result["stdout"][:5000]}
    return {"mode": mode, "target": target, "command": result["command"], "data": data}
