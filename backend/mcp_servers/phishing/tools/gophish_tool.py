"""Tool: gophish_campaign — Gophish campaign management via API."""
import json
import os
import urllib.request

from shared.mcp_protocol import MCPTool
from shared.scope_check import check_scope


TOOL = MCPTool(
    name="gophish_campaign",
    description=(
        "Manage Gophish phishing campaigns (create, launch, results, report). "
        "Targets must be inside the signed engagement scope."
    ),
    input_schema={
        "properties": {
            "action": {"type": "string", "enum": ["create", "launch", "results", "report"]},
            "campaign_id": {"type": "integer"},
            "payload": {"type": "object"},
        },
        "required": ["action"],
    },
    timeout_seconds=300,
    risk_level="high",
    requires_approval=True,
    ens_measures=["mp.per.3", "mp.per.4"],
)


async def gophish_campaign(
    action: str,
    campaign_id: int | None = None,
    payload: dict | None = None,
) -> dict:
    host = os.environ.get("GOPHISH_HOST", "http://gophish:3333")
    api_key = os.environ.get("GOPHISH_API_KEY", "")
    if not api_key:
        return {"error": "GOPHISH_API_KEY not configured", "action": action}

    if action in ("create", "launch") and payload:
        for target in payload.get("targets", []):
            scope = check_scope(target.get("email", ""), "phishing")
            if not scope["allowed"]:
                return {"error": f"SCOPE DENIED: {scope['reason']}"}

    url_map = {
        "create": f"{host}/api/campaigns/",
        "launch": f"{host}/api/campaigns/{campaign_id}/launch",
        "results": f"{host}/api/campaigns/{campaign_id}/results",
        "report": f"{host}/api/campaigns/{campaign_id}",
    }
    url = url_map[action]
    data = json.dumps(payload or {}).encode() if action == "create" else None
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode()
        return {"action": action, "response": body[:5000]}
    except Exception as exc:
        return {"error": str(exc)[:500], "action": action}
