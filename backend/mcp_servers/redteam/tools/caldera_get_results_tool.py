"""Tool: caldera_get_results — Retrieve CALDERA operation results."""
import json
import os
import urllib.request

from shared.mcp_protocol import MCPTool
from shared.scope_check import check_scope


TOOL = MCPTool(
    name="caldera_get_results",
    description="Fetch results (abilities executed, artifacts) for a CALDERA operation.",
    input_schema={
        "properties": {"operation_id": {"type": "string"}},
        "required": ["operation_id"],
    },
    timeout_seconds=60,
    risk_level="low",
    ens_measures=["op.exp.4"],
)


async def caldera_get_results(operation_id: str) -> dict:
    # Validates active engagement window, not target IP
    scope = check_scope("__local__", "config_audit")
    if not scope["allowed"]:
        return {"error": f"SCOPE DENIED: {scope['reason']}"}
    host = os.environ.get("CALDERA_HOST", "http://caldera:8888")
    api_key = os.environ.get("CALDERA_API_KEY", "")
    if not api_key:
        return {"error": "CALDERA_API_KEY not configured", "operation_id": operation_id}
    req = urllib.request.Request(
        f"{host}/api/v2/operations/{operation_id}",
        headers={"KEY": api_key},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode()
        return {"operation_id": operation_id, "data": json.loads(body)}
    except Exception as exc:
        return {"error": str(exc)[:500], "operation_id": operation_id}
