"""M8 Autopilot · normalización a esquema común (doc §3 Capa 3).

SARIF 2.1.0 como esquema común cross-motor + adaptadores MCP→Finding.
"""
from backend.app.motors.m08_verification.normalization.sarif import (
    findings_to_sarif,
    sarif_to_findings,
)
from backend.app.motors.m08_verification.normalization.adapters import (
    mcp_finding_to_candidate,
    mcp_result_to_candidates,
)

__all__ = [
    "findings_to_sarif",
    "sarif_to_findings",
    "mcp_finding_to_candidate",
    "mcp_result_to_candidates",
]
