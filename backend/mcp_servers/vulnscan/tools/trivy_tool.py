"""Tool: trivy_scan — Aquasecurity Trivy (image/fs/repo/config)."""
import json

from shared.mcp_protocol import MCPTool
from shared.output_normalizer import normalize_finding
from shared.scope_check import check_scope
from shared.utils import run_command


TOOL = MCPTool(
    name="trivy_scan",
    description="Trivy vulnerability scanner (container image, filesystem, repo or IaC config).",
    input_schema={
        "properties": {
            "target": {"type": "string"},
            "scan_type": {"type": "string", "enum": ["image", "fs", "repo", "config"], "default": "image"},
        },
        "required": ["target"],
    },
    timeout_seconds=1200,
    risk_level="low",
    ens_measures=["op.exp.2", "mp.sw.2"],
)


async def trivy_scan(target: str, scan_type: str = "image") -> dict:
    scope = check_scope(target, "scan")
    if not scope["allowed"]:
        return {"error": f"SCOPE DENIED: {scope['reason']}", "findings": []}
    cmd = ["trivy", scan_type, target, "--format", "json", "--quiet"]
    result = await run_command(cmd, timeout=TOOL.timeout_seconds)
    findings = []
    try:
        data = json.loads(result["stdout"] or "{}")
        for r in data.get("Results", []):
            for vuln in r.get("Vulnerabilities", []) or []:
                findings.append(normalize_finding(vuln, "trivy", target, result["command"]))
    except json.JSONDecodeError:
        pass
    return {"target": target, "command": result["command"], "findings": findings}
