"""Tool: nuclei_scan — ProjectDiscovery template-based vulnerability scanner."""
from shared.mcp_protocol import MCPTool
from shared.output_normalizer import normalize_finding
from shared.scope_check import check_scope
from shared.utils import parse_jsonl, run_command


TOOL = MCPTool(
    name="nuclei_scan",
    description="Template-driven vulnerability scanner with 8000+ CVE/misconfig checks.",
    input_schema={
        "properties": {
            "target": {"type": "string"},
            "severity": {"type": "string", "default": "critical,high,medium"},
            "tags": {"type": "string", "default": "cve,misconfig"},
            "rate_limit": {"type": "integer", "default": 150},
        },
        "required": ["target"],
    },
    timeout_seconds=1800,
    risk_level="medium",
    ens_measures=["op.exp.2", "op.exp.4"],
)


async def nuclei_scan(
    target: str,
    severity: str = "critical,high,medium",
    tags: str = "cve,misconfig",
    rate_limit: int = 150,
) -> dict:
    scope = check_scope(target, "scan")
    if not scope["allowed"]:
        return {"error": f"SCOPE DENIED: {scope['reason']}", "findings": []}

    cmd = [
        "nuclei", "-target", target, "-jsonl", "-silent",
        "-severity", severity, "-tags", tags,
        "-rate-limit", str(rate_limit),
    ]
    result = await run_command(cmd, timeout=TOOL.timeout_seconds)
    raw_findings = parse_jsonl(result["stdout"])
    findings = [normalize_finding(f, "nuclei", target, result["command"]) for f in raw_findings]
    return {
        "target": target,
        "command": result["command"],
        "findings": findings,
        "summary": {
            "total": len(findings),
            "critical": sum(1 for f in findings if f["severity"] == "critical"),
            "high": sum(1 for f in findings if f["severity"] == "high"),
        },
    }
