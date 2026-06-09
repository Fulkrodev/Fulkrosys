"""Tool: arjun_param_discovery — Arjun hidden parameter discovery."""
import json

from shared.mcp_protocol import MCPTool
from shared.scope_check import check_scope
from shared.utils import run_command


TOOL = MCPTool(
    name="arjun_param_discovery",
    description="Arjun: find hidden HTTP parameters accepted by a web endpoint.",
    input_schema={
        "properties": {"url": {"type": "string"}},
        "required": ["url"],
    },
    timeout_seconds=900,
    risk_level="low",
    ens_measures=["mp.sw.2"],
)


async def arjun_param_discovery(url: str) -> dict:
    scope = check_scope(url, "scan")
    if not scope["allowed"]:
        return {"error": f"SCOPE DENIED: {scope['reason']}"}
    cmd = ["arjun", "-u", url, "-oJ", "/tmp/arjun.json"]
    result = await run_command(cmd, timeout=TOOL.timeout_seconds)
    findings: dict = {}
    try:
        with open("/tmp/arjun.json") as fh:
            findings = json.load(fh)
    except Exception:
        findings = {}
    return {"url": url, "command": result["command"], "findings": findings}
