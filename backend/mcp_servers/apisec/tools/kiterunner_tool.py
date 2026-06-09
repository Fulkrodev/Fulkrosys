"""Tool: kiterunner_api_fuzz — assetnote Kiterunner API fuzzing."""
from shared.mcp_protocol import MCPTool
from shared.scope_check import check_scope
from shared.utils import run_command


TOOL = MCPTool(
    name="kiterunner_api_fuzz",
    description="Kiterunner: fuzz REST APIs using known route kites (Swagger/OpenAPI).",
    input_schema={
        "properties": {
            "target": {"type": "string"},
            "kite": {"type": "string", "default": "/opt/kites/routes-large.kite"},
        },
        "required": ["target"],
    },
    timeout_seconds=1800,
    risk_level="low",
    ens_measures=["mp.sw.2"],
)


async def kiterunner_api_fuzz(
    target: str, kite: str = "/opt/kites/routes-large.kite"
) -> dict:
    scope = check_scope(target, "scan")
    if not scope["allowed"]:
        return {"error": f"SCOPE DENIED: {scope['reason']}"}
    cmd = ["kr", "scan", target, "-w", kite, "--json"]
    result = await run_command(cmd, timeout=TOOL.timeout_seconds)
    return {
        "target": target, "kite": kite,
        "command": result["command"],
        "stdout": result["stdout"][:10000],
        "returncode": result["returncode"],
    }
