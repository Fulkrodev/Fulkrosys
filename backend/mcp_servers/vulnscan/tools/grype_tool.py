"""Tool: grype_sbom_scan — Anchore Grype SBOM/image vulnerability scan."""
import json

from shared.mcp_protocol import MCPTool
from shared.output_normalizer import normalize_finding
from shared.scope_check import check_scope
from shared.utils import run_command


TOOL = MCPTool(
    name="grype_sbom_scan",
    description="Grype vulnerability scanner for container images or SBOM files.",
    input_schema={
        "properties": {"target": {"type": "string"}},
        "required": ["target"],
    },
    timeout_seconds=900,
    risk_level="low",
    ens_measures=["op.exp.2", "mp.sw.2"],
)


async def grype_sbom_scan(target: str) -> dict:
    scope = check_scope(target, "scan")
    if not scope["allowed"]:
        return {"error": f"SCOPE DENIED: {scope['reason']}", "findings": []}
    cmd = ["grype", target, "-o", "json", "--quiet"]
    result = await run_command(cmd, timeout=TOOL.timeout_seconds)
    findings = []
    try:
        data = json.loads(result["stdout"] or "{}")
        for match in data.get("matches", []):
            vuln = match.get("vulnerability", {})
            findings.append(normalize_finding(vuln, "grype", target, result["command"]))
    except json.JSONDecodeError:
        pass
    return {"target": target, "command": result["command"], "findings": findings}
