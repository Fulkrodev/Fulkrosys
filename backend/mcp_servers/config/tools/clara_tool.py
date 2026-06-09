"""Tool: clara_ccn_audit — Parse CLARA (CCN) Windows XML reports."""
import os
import xml.etree.ElementTree as ET

from shared.mcp_protocol import MCPTool


TOOL = MCPTool(
    name="clara_ccn_audit",
    description=(
        "Parse the XML report produced by CLARA (CCN's Windows hardening auditor) "
        "into a structured finding list."
    ),
    input_schema={
        "properties": {
            "report_path": {"type": "string", "description": "Path to CLARA XML report"},
        },
        "required": ["report_path"],
    },
    timeout_seconds=60,
    risk_level="low",
    ens_measures=["op.exp.2", "mp.si.2"],
)


async def clara_ccn_audit(report_path: str) -> dict:
    """Scope: local audit — no external target, scope check not applicable."""
    if not os.path.exists(report_path):
        return {"error": f"Report not found: {report_path}"}
    try:
        tree = ET.parse(report_path)
    except ET.ParseError as exc:
        return {"error": f"Parse error: {exc}"}
    root = tree.getroot()
    findings = []
    for item in root.findall(".//Result"):
        findings.append({
            "id": item.get("id", ""),
            "status": item.get("status", ""),
            "description": (item.findtext("Description") or "").strip(),
        })
    return {
        "report_path": report_path,
        "findings": findings,
        "summary": {"total": len(findings)},
    }
