"""Tool: bandit_scan — Python-specific SAST."""
import json

from shared.mcp_protocol import MCPTool
from shared.output_normalizer import normalize_finding
from shared.utils import run_command


TOOL = MCPTool(
    name="bandit_scan",
    description="Bandit: Python static security analyzer.",
    input_schema={
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    },
    timeout_seconds=900,
    risk_level="low",
    ens_measures=["mp.sw.1"],
)


async def bandit_scan(path: str) -> dict:
    """Scope: local audit — no external target, scope check not applicable."""
    cmd = ["bandit", "-r", path, "-f", "json"]
    result = await run_command(cmd, timeout=TOOL.timeout_seconds)
    findings = []
    try:
        data = json.loads(result["stdout"] or "{}")
        for f in data.get("results", []):
            findings.append(normalize_finding(f, "bandit", path, result["command"]))
    except json.JSONDecodeError:
        pass
    return {"path": path, "command": result["command"], "findings": findings}
