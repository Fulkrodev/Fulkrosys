"""Tool: dependency_check — OWASP Dependency-Check multi-language audit."""
import json

from shared.mcp_protocol import MCPTool
from shared.utils import run_command


TOOL = MCPTool(
    name="dependency_check",
    description="OWASP Dependency-Check: CVEs in Maven/Gradle/npm/pip/NuGet dependencies.",
    input_schema={
        "properties": {"project_path": {"type": "string"}},
        "required": ["project_path"],
    },
    timeout_seconds=3600,
    risk_level="low",
    ens_measures=["mp.sw.2"],
)


async def dependency_check(project_path: str) -> dict:
    """Scope: local audit — no external target, scope check not applicable."""
    cmd = [
        "dependency-check", "-s", project_path,
        "--format", "JSON", "--out", "/tmp/depcheck",
    ]
    result = await run_command(cmd, timeout=TOOL.timeout_seconds)
    findings = []
    report_path = "/tmp/depcheck/dependency-check-report.json"
    try:
        with open(report_path) as fh:
            data = json.load(fh)
        for dep in data.get("dependencies", []):
            for vuln in dep.get("vulnerabilities", []) or []:
                findings.append(vuln)
    except Exception:
        pass
    return {"project_path": project_path, "command": result["command"], "findings": findings}
