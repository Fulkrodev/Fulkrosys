"""Tool: searchsploit_query — Offline ExploitDB search."""
import json

from shared.mcp_protocol import MCPTool
from shared.utils import run_command


TOOL = MCPTool(
    name="searchsploit_query",
    description="Offline ExploitDB search for known exploits matching product/version.",
    input_schema={
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    },
    timeout_seconds=60,
    risk_level="low",
    ens_measures=["op.exp.4"],
)


async def searchsploit_query(query: str) -> dict:
    """Scope: local audit — no external target, scope check not applicable."""
    cmd = ["searchsploit", "--json", query]
    result = await run_command(cmd, timeout=TOOL.timeout_seconds)
    data: dict = {}
    try:
        data = json.loads(result["stdout"] or "{}")
    except json.JSONDecodeError:
        data = {}
    exploits = data.get("RESULTS_EXPLOIT", []) if isinstance(data, dict) else []
    return {
        "query": query,
        "command": result["command"],
        "exploits": exploits,
        "summary": {"total": len(exploits)},
    }
