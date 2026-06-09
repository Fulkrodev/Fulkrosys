"""Tool: semgrep_scan — Semgrep static analysis with built-in rulesets."""
import json

from shared.mcp_protocol import MCPTool
from shared.output_normalizer import normalize_finding
from shared.utils import run_command


TOOL = MCPTool(
    name="semgrep_scan",
    description="Run Semgrep SAST with OWASP/CWE rulesets on a source-code path.",
    input_schema={
        "properties": {
            "path": {"type": "string"},
            "config": {"type": "string", "default": "p/owasp-top-ten"},
        },
        "required": ["path"],
    },
    timeout_seconds=1800,
    risk_level="low",
    ens_measures=["mp.sw.1"],
)


async def semgrep_scan(path: str, config: str = "p/owasp-top-ten") -> dict:
    """Scope: local audit — no external target, scope check not applicable."""
    cmd = ["semgrep", "--config", config, "--json", path]
    result = await run_command(cmd, timeout=TOOL.timeout_seconds)
    findings = []
    try:
        data = json.loads(result["stdout"] or "{}")
        for f in data.get("results", []):
            findings.append(normalize_finding(f, "semgrep", path, result["command"]))
    except json.JSONDecodeError:
        pass
    return {"path": path, "config": config, "command": result["command"], "findings": findings}
