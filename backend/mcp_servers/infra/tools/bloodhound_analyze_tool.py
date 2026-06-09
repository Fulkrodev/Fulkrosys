"""Tool: bloodhound_analyze — Parse BloodHound JSON to extract attack paths."""
import json
import os

from shared.mcp_protocol import MCPTool


TOOL = MCPTool(
    name="bloodhound_analyze",
    description="Parse BloodHound collection JSON to surface paths to Domain Admin / Tier 0.",
    input_schema={
        "properties": {
            "json_path": {"type": "string", "description": "Path to BloodHound JSON file"},
        },
        "required": ["json_path"],
    },
    timeout_seconds=300,
    risk_level="low",
    ens_measures=["op.acc.5"],
)


async def bloodhound_analyze(json_path: str) -> dict:
    """Scope: local audit — no external target, scope check not applicable."""
    if not os.path.exists(json_path):
        return {"error": f"File not found: {json_path}"}
    try:
        with open(json_path) as fh:
            data = json.load(fh)
    except Exception as exc:
        return {"error": str(exc)[:500]}
    return {
        "path": json_path,
        "kind": data.get("meta", {}).get("type", "unknown"),
        "count": data.get("meta", {}).get("count", 0),
    }
