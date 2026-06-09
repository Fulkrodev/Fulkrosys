"""Tool: caldera_create_operation — Launch a MITRE CALDERA operation."""
import os

import urllib.request
import json

from shared.mcp_protocol import MCPTool
from shared.scope_check import check_scope


TOOL = MCPTool(
    name="caldera_create_operation",
    description="Create and launch a CALDERA adversary emulation operation.",
    input_schema={
        "properties": {
            "name": {"type": "string"},
            "adversary_id": {"type": "string"},
            "group": {"type": "string", "default": "red"},
        },
        "required": ["name", "adversary_id"],
    },
    timeout_seconds=600,
    risk_level="high",
    requires_approval=True,
    ens_measures=["op.exp.4"],
)


async def caldera_create_operation(
    name: str, adversary_id: str, group: str = "red"
) -> dict:
    scope = check_scope(group, "exploit")
    if not scope["allowed"]:
        return {"error": f"SCOPE DENIED: {scope['reason']}"}
    host = os.environ.get("CALDERA_HOST", "http://caldera:8888")
    api_key = os.environ.get("CALDERA_API_KEY", "")
    if not api_key:
        return {"error": "CALDERA_API_KEY not configured", "name": name}
    data = json.dumps({
        "name": name, "adversary_id": adversary_id, "group": group,
    }).encode()
    req = urllib.request.Request(
        f"{host}/api/v2/operations", data=data,
        headers={"KEY": api_key, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode()
        return {"status": "created", "name": name, "response": body[:2000]}
    except Exception as exc:
        return {"error": str(exc)[:500], "name": name}
