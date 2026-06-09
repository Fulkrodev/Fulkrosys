"""Tool: lynis_audit — Lynis Linux hardening audit (host-local).

Pattern replica nuclei_tool.py · subprocess + check_scope + normalize.
SAN-B.MB-7.1 · cierre wire-up MCP path para LynisRunner existing.
"""
from shared.mcp_protocol import MCPTool
from shared.output_normalizer import normalize_finding
from shared.scope_check import check_scope
from shared.utils import run_command


TOOL = MCPTool(
    name="lynis_audit",
    description="Lynis Linux hardening audit · warnings + suggestions normalizadas a findings.",
    input_schema={
        "properties": {
            "target": {
                "type": "string",
                "description": "host_label · ej. 'localhost' o 'cliente-prod-host'.",
            },
            "quick_mode": {"type": "boolean", "default": True},
        },
        "required": ["target"],
    },
    timeout_seconds=20 * 60,  # 20 min default
    risk_level="low",
    ens_measures=["op.exp.2", "op.exp.4", "mp.if.6"],
)


async def lynis_audit(target: str, quick_mode: bool = True) -> dict:
    scope = check_scope(target, "audit")
    if not scope["allowed"]:
        return {"error": f"SCOPE DENIED: {scope['reason']}", "findings": []}

    cmd = ["lynis", "audit", "system", "--no-colors",
           "--logfile", "/dev/null", "--report-file", "/dev/stdout"]
    if quick_mode:
        cmd.append("--quick")
    result = await run_command(cmd, timeout=TOOL.timeout_seconds)

    raw_findings = _parse_lynis_report(result["stdout"])
    findings = [normalize_finding(f, "lynis", target, result["command"]) for f in raw_findings]
    return {
        "target": target,
        "command": result["command"],
        "findings": findings,
        "summary": {
            "total": len(findings),
            "warnings": sum(1 for f in raw_findings if f.get("kind") == "warning"),
            "suggestions": sum(1 for f in raw_findings if f.get("kind") == "suggestion"),
        },
    }


def _parse_lynis_report(text: str) -> list[dict]:
    """Parse Lynis report.dat: warning[]=ID|message|severity|solution lines."""
    if not text:
        return []
    findings: list[dict] = []
    for line in text.splitlines():
        line = line.strip()
        if "=" not in line or not (line.startswith("warning[]") or line.startswith("suggestion[]")):
            continue
        kind = "warning" if line.startswith("warning[]") else "suggestion"
        value = line.split("=", 1)[1]
        parts = value.split("|", 3)
        test_id = parts[0] if parts else "UNKNOWN"
        message = parts[1] if len(parts) > 1 else ""
        findings.append({
            "title": f"Lynis {kind.upper()} {test_id}",
            "name": test_id,
            "description": message or f"Lynis {kind}",
            "severity": "high" if kind == "warning" else "medium",
            "kind": kind,
        })
    return findings
