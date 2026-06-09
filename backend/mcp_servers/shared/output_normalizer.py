"""Normalize any tool's output into the canonical FULKRO finding shape."""
import hashlib
import json
from datetime import datetime, timezone

from shared.utils import extract_cves, normalize_severity


def normalize_finding(
    raw: dict,
    tool_name: str,
    target: str,
    command_executed: str = "",
) -> dict:
    """Normalize a single raw finding from any scanner into the standard shape.

    The shape matches what Motor 8 v2 persists in ``pentest_findings`` and what
    Agent 10 consumes to build the E-702/E-703/E-704 reports.
    """
    title = (
        raw.get("title")
        or raw.get("name")
        or raw.get("info", {}).get("name")
        or raw.get("template-id")
        or raw.get("vulnerability", {}).get("title")
        or raw.get("plugin_name")
        or "Unknown finding"
    )

    raw_severity = (
        raw.get("severity")
        or raw.get("info", {}).get("severity")
        or raw.get("risk")
        or raw.get("vulnerability", {}).get("severity")
        or "info"
    )

    description = (
        raw.get("description")
        or raw.get("info", {}).get("description")
        or raw.get("vulnerability", {}).get("description")
        or raw.get("synopsis")
        or ""
    )

    cves = extract_cves(json.dumps(raw, default=str))

    cvss = (
        raw.get("cvss")
        or raw.get("info", {}).get("classification", {}).get("cvss-score")
        or raw.get("vulnerability", {}).get("cvss_score")
        or raw.get("cvss_base_score")
    )
    if cvss is not None:
        try:
            cvss = float(cvss)
        except (ValueError, TypeError):
            cvss = None

    host = raw.get("host") or raw.get("ip") or raw.get("target") or target

    matched_at = raw.get("matched-at", "")
    port_raw = raw.get("port")
    if port_raw is None and matched_at and ":" in matched_at:
        tail = matched_at.split(":")[-1]
        port_raw = tail.split("/")[0] if "/" in tail else tail

    evidence = (
        raw.get("evidence")
        or matched_at
        or raw.get("curl-command")
        or raw.get("extracted-results")
        or raw.get("proof")
        or ""
    )

    remediation = (
        raw.get("remediation")
        or raw.get("solution")
        or raw.get("info", {}).get("remediation")
        or raw.get("fix")
        or ""
    )

    raw_json = json.dumps(raw, sort_keys=True, default=str)
    port_int: int | None = None
    if port_raw is not None and str(port_raw).isdigit():
        port_int = int(port_raw)

    return {
        "tool": tool_name,
        "title": str(title)[:500],
        "severity": normalize_severity(raw_severity),
        "description": str(description)[:5000],
        "cve": cves,
        "cvss": cvss,
        "host": str(host),
        "port": port_int,
        "protocol": raw.get("protocol", "tcp"),
        "evidence": str(evidence)[:3000],
        "raw_output_hash": hashlib.sha256(raw_json.encode()).hexdigest(),
        "command_executed": command_executed,
        "remediation": str(remediation)[:2000],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "raw_data": raw,
    }
